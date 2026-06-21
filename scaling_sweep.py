"""
scaling_sweep.py - Phase-3 Axis-A scaling sweep for CHIMERA-QRC.

Emits the two decisive H0 curves vs qubit count n:
  (1) g(n)      - geometric difference g(ESN-108 -> CHIMERA-1scale) on the train-window
                  kernel (with the classical-classical control and kernel effective rank).
  (2) mz_gap(n) - MZ-R2(CHIMERA-3scale) - MZ-R2(HAR) on the regime-transition (GFC-in-test)
                  split, with the Diebold-Mariano test and Model-Confidence-Set membership.

The verdict is computed MECHANICALLY from the PRE-REGISTERED thresholds in
h0_thresholds.py (locked in a prior commit; see preregistration.md). This first sweep
uses the *univariate* 8-lag encoder, so per the pre-registration it is scoped as a
HARNESS VALIDATION + INPUT-BOUND DIAGNOSTIC, not a test of H0 itself: with a fixed 8-lag
input, qubits beyond 8 carry no new information, so g(n)/effective-rank are predicted to
saturate (an input-bound signature that gates the Axis-B encoder, NOT an H0 refutation).

Reuses the exact Phase-2 model and metrics (multiscale_chimera, vol_fair_benchmark) so
the n=8 row reproduces the published anchors (g~62; mz_gap~+0.032) before any new n is
trusted.

Usage:
    python scaling_sweep.py                 # n in {8, 10, 12}
    python scaling_sweep.py --ns 8          # anchor-only quick validation
    python scaling_sweep.py --ns 8 10 12 14 # extend (n=14 needs ~4 GB per reservoir)

Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
from __future__ import annotations
import argparse, json, time, sys
import numpy as np
import pandas as pd
from numpy.linalg import eigh, inv, norm

import volatility_data as vd
from vol_fair_benchmark import (
    LAGS, SEEDS, rmse, qlike, mz_r2, dm_test, model_confidence_set,
    ridge_readout, esn_features,
)
from multiscale_chimera import MultiScaleCHIMERA
import h0_thresholds as H0

# Phase-2 configurations (fixed; only n is swept)
TAU_1SCALE = (2.0,)             # g(n) anchor architecture (kernel geometry)
TAU_3SCALE = (1.0, 2.0, 4.0)    # mz_gap(n) headline architecture (regime transition)
CRISIS_TRAIN_END = pd.Timestamp("2007-01-01")
CRISIS_TEST_END = pd.Timestamp("2013-01-01")
KERNEL_N = 800                  # train subsample for stable/fast kernel ops (as in Phase 2)


# --------------------------- model & kernel helpers ---------------------------
def chimera_features_n(Q, taus, seed, n_qubits):
    """Identical to vol_fair_benchmark.chimera_features, but with n_qubits parametrized.
    Same MultiScaleCHIMERA model -> the n=8 row reproduces the Phase-2 features exactly."""
    ch = MultiScaleCHIMERA(n_qubits=n_qubits, taus=taus, hamiltonian='ising',
                           hx=1.0, connectivity=0.5, seed=seed)
    ch._reset_feedback()
    return np.array([ch._all_features(w) for w in Q])


def _standardize(F):
    mu, sd = F.mean(0), F.std(0); sd = np.where(sd < 1e-8, 1.0, sd); return (F - mu) / sd

def lin_kernel(F):
    F = _standardize(F); K = F @ F.T
    return K * (K.shape[0] / np.trace(K))      # trace-normalize to N

def eff_dim(K):
    w = np.clip(eigh(K)[0], 0, None); return float((w.sum() ** 2) / ((w ** 2).sum() + 1e-12))

def geom_diff(KA, KB, reg=1e-3):
    n = KA.shape[0]
    wB, VB = eigh(KB); wB = np.clip(wB, 0, None); KBh = (VB * np.sqrt(wB)) @ VB.T
    M = KBh @ inv(KA + reg * np.eye(n)) @ KBh
    return float(np.sqrt(np.clip(eigh(M)[0], 0, None).max()))


# --------------------------- the two H0 curves ---------------------------
def compute_g(n, Q, tr, y):
    """g(n): geometric difference of the matched ESN kernel from the CHIMERA-1scale
    kernel, on an evenly-spaced N=KERNEL_N train subsample (mirrors kernel_analysis.py)."""
    idx = np.linspace(0, len(tr) - 1, min(KERNEL_N, len(tr))).astype(int)
    trk = np.array(tr)[idx]
    FQ = chimera_features_n(Q[trk], TAU_1SCALE, 0, n)     # quantum, n-dependent feat dim
    F108 = esn_features(Q[trk], 108, 0)                   # matched classical
    F108b = esn_features(Q[trk], 108, 1)                  # classical-classical control
    KQ, K108, K108b = lin_kernel(FQ), lin_kernel(F108), lin_kernel(F108b)
    return {
        "g": geom_diff(K108, KQ),                # g(ESN-108 -> CHIMERA)  [anchor ~62 @ n=8]
        "g_control": geom_diff(K108, K108b),     # classical-classical control [~4.3]
        "deff_chimera": eff_dim(KQ),
        "deff_esn108": eff_dim(K108),
        "n_feat_chimera": int(FQ.shape[1]),
    }


def _mz_gap_bootstrap(yT_rv, var_chim, var_har, B=2000, block=20, seed=0):
    """Stationary-block-bootstrap one-sided significance of the MZ-R2 gap (CHIMERA-HAR).
    This is the correct significance test for the H0 as *stated* (regime-transition MZ-R2
    gap), distinct from the Diebold-Mariano test on point-forecast loss.
    Returns (p_gap_not_positive, boot_mean, boot_std)."""
    rng = np.random.RandomState(seed); T = len(yT_rv); gaps = np.empty(B)
    for b in range(B):
        idx = np.empty(T, int); i = 0
        while i < T:
            s = rng.randint(T); ln = max(1, rng.geometric(1.0 / block))
            for j in range(ln):
                if i >= T: break
                idx[i] = (s + j) % T; i += 1
        gaps[b] = mz_r2(yT_rv[idx], var_chim[idx]) - mz_r2(yT_rv[idx], var_har[idx])
    return float((gaps <= 0).mean()), float(gaps.mean()), float(gaps.std())


def compute_mz_gap(n, Qc, tr, te, y_logrv, y_rv, Xlag, Xhar):
    """mz_gap(n): MZ-R2(CHIMERA-3scale ensemble) - MZ-R2(HAR) on the crisis split, with
    DM(CHIMERA vs HAR) on point loss, a block-bootstrap MZ-gap test, and MCS membership."""
    LIN = np.hstack([Xlag, Xhar])
    yT_log, yT_rv = y_logrv[te], y_rv[te]

    har_pred, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])

    def reservoir_pred(kind):
        sp = []
        for sd in SEEDS:
            F = (esn_features(Qc, 108, sd) if kind == "esn"
                 else chimera_features_n(Qc, TAU_3SCALE, sd, n))
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
            sp.append(pr)
        return np.mean(sp, axis=0)

    chim_pred = reservoir_pred("chim")
    esn_pred = reservoir_pred("esn")

    mz_chim = mz_r2(yT_rv, np.exp(chim_pred))
    mz_har = mz_r2(yT_rv, np.exp(har_pred))
    har_loss = (har_pred - yT_log) ** 2
    chim_loss = (chim_pred - yT_log) ** 2
    esn_loss = (esn_pred - yT_log) ** 2
    dm_stat, dm_p = dm_test(chim_loss, har_loss)     # <0 & p<.05 => CHIMERA beats HAR (point loss)
    surv, mp = model_confidence_set(
        {"HAR-RV": har_loss, "ESN-108": esn_loss, "CHIMERA-3scale": chim_loss})
    boot_p, boot_mean, boot_std = _mz_gap_bootstrap(yT_rv, np.exp(chim_pred), np.exp(har_pred))
    return {
        "mz_chimera": mz_chim, "mz_har": mz_har, "mz_gap": mz_chim - mz_har,
        "mz_gap_boot_p": boot_p, "mz_gap_boot_mean": boot_mean, "mz_gap_boot_std": boot_std,
        "dm_stat": dm_stat, "dm_p": dm_p,
        "chimera_in_mcs": "CHIMERA-3scale" in surv, "mcs": surv,
        "rmse_chimera": rmse(yT_log, chim_pred), "rmse_har": rmse(yT_log, har_pred),
    }


# --------------------------- driver ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[8, 10, 12])
    ap.add_argument("--out", default="scaling_sweep_results.json")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()

    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    dts = pd.to_datetime(data["dates"])

    # headline split (for g): 70/30 chronological
    tr_h, te_h = vd.make_splits(len(y_logrv), train_frac=0.70)
    lo, hi = Xlag[tr_h].min(0), Xlag[tr_h].max(0); rng = np.where(hi - lo == 0, 1, hi - lo)
    Q_h = np.clip((Xlag - lo) / rng, 0.0, 1.0)

    # crisis split (for mz_gap): GFC 2008 in the test set
    tr_c = np.where(dts < CRISIS_TRAIN_END)[0]
    te_c = np.where((dts >= CRISIS_TRAIN_END) & (dts < CRISIS_TEST_END))[0]
    loc, hic = Xlag[tr_c].min(0), Xlag[tr_c].max(0); rngc = np.where(hic - loc == 0, 1, hic - loc)
    Q_c = np.clip((Xlag - loc) / rngc, 0.0, 1.0)

    print("=" * 92)
    print("CHIMERA-QRC Phase-3  Axis-A SCALING SWEEP  (univariate 8-lag encoder)")
    print(f"  g(n): headline split, kernel N={KERNEL_N}, 1-scale tau={TAU_1SCALE}")
    print(f"  mz_gap(n): crisis split {dts[tr_c[0]].date()}..{dts[te_c[-1]].date()} "
          f"(train n={len(tr_c)}, test n={len(te_c)}), 3-scale tau={TAU_3SCALE}, seeds={SEEDS}")
    print("  verdict via PRE-REGISTERED h0_thresholds.py (encoding='univariate')")
    print("=" * 92)

    rows = []
    t_start = time.time()
    for n in args.ns:
        t0 = time.time()
        g = compute_g(n, Q_h, tr_h, y_logrv)
        mz = compute_mz_gap(n, Q_c, tr_c, te_c, y_logrv, y_rv, Xlag, Xhar)
        row = {"n": n, **g, **mz, "secs": round(time.time() - t0, 1)}
        rows.append(row)
        print(f"\n[n={n:2d}]  g={g['g']:6.2f} (control {g['g_control']:4.2f})  "
              f"D_eff(Q)={g['deff_chimera']:5.2f}  feat={g['n_feat_chimera']:3d}   ||   "
              f"MZ: CHIMERA={mz['mz_chimera']:.3f} HAR={mz['mz_har']:.3f} "
              f"gap={mz['mz_gap']:+.3f} (boot p={mz['mz_gap_boot_p']:.3f})  "
              f"DM(loss)={mz['dm_stat']:+.2f} (p={mz['dm_p']:.3f})  "
              f"in_MCS={mz['chimera_in_mcs']}  [{row['secs']}s]")
        # incremental save (robust to interruption)
        json.dump({"rows": rows}, open(args.out, "w"), indent=2)

    # ---- mechanical verdict from the locked thresholds ----
    ns = [r["n"] for r in rows]
    gs = [r["g"] for r in rows]
    deffs = [r["deff_chimera"] for r in rows]
    g_control = float(np.mean([r["g_control"] for r in rows]))
    last = rows[-1]

    anchor_passed = anchor_msg = None
    if 8 in ns:
        a = next(r for r in rows if r["n"] == 8)
        anchor_passed, anchor_msg = H0.anchor_ok(a["g"], a["mz_gap"])

    g_stat = H0.g_curve_status(ns, gs, g_control)
    d_stat = H0.deff_status(ns, deffs)
    acc_stat = H0.accuracy_status(last["mz_gap"], last["dm_stat"], last["dm_p"],
                                  last["chimera_in_mcs"], last["mz_gap_boot_p"])
    verdict = H0.h0_verdict("univariate", max(ns),
                            anchor_passed if anchor_passed is not None else False,
                            g_stat, d_stat, acc_stat)

    print("\n" + "=" * 92)
    print("PRE-REGISTERED VERDICT (univariate Axis-A sweep)")
    print("-" * 92)
    if anchor_msg:
        print(f"  anchor gate : {'PASS' if anchor_passed else 'FAIL'}  |  {anchor_msg}")
    print(f"  g-curve     : {g_stat}   (top-step Dg vs control {g_control:.2f}; "
          f"growing>= {H0.G_GROWTH_CONTROL_MULT}x control, saturating<= 1x)")
    print(f"  D_eff-curve : {d_stat}")
    print(f"  accuracy    : {acc_stat}   (mz_gap@max_n={last['mz_gap']:+.3f}, "
          f"DM p={last['dm_p']:.3f}, in_MCS={last['chimera_in_mcs']})")
    print(f"\n  >>> {verdict}")
    print("=" * 92)
    print(f"[total {time.time() - t_start:.0f}s]")

    summary = {
        "encoding": "univariate", "ns": ns, "g_control": g_control,
        "anchor_passed": anchor_passed, "g_status": g_stat, "deff_status": d_stat,
        "accuracy_status": acc_stat, "verdict": verdict.label,
        "verdict_rationale": verdict.rationale, "rows": rows,
    }
    json.dump(summary, open(args.out, "w"), indent=2)
    pd.DataFrame(rows).to_csv(args.out.replace(".json", ".csv"), index=False)
    print(f"saved {args.out} and {args.out.replace('.json', '.csv')}")

    if not args.no_plot and len(rows) >= 1:
        try:
            _plot(rows, g_control, verdict)
        except Exception as e:
            print(f"(plot skipped: {e})")


def _plot(rows, g_control, verdict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ns = [r["n"] for r in rows]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(ns, [r["g"] for r in rows], "o-", lw=2, label="g(ESN→CHIMERA)")
    ax[0].axhline(g_control, ls="--", c="gray", label=f"classical control ≈{g_control:.1f}")
    ax[0].set_xlabel("qubit count n"); ax[0].set_ylabel("geometric difference g(n)")
    ax[0].set_title("H0 curve 1: kernel distinctness"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax2 = ax[0].twinx()
    ax2.plot(ns, [r["deff_chimera"] for r in rows], "s:", c="C1", alpha=.7, label="D_eff")
    ax2.set_ylabel("kernel effective rank D_eff", color="C1")
    ax[1].axhline(0, c="k", lw=.8)
    ax[1].plot(ns, [r["mz_gap"] for r in rows], "o-", lw=2, c="C2")
    ax[1].set_xlabel("qubit count n"); ax[1].set_ylabel("MZ-R²(CHIMERA) − MZ-R²(HAR)")
    ax[1].set_title("H0 curve 2: regime-transition accuracy gap"); ax[1].grid(alpha=.3)
    fig.suptitle(f"CHIMERA-QRC Axis-A sweep (univariate)  —  verdict: {verdict.label}",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig("figures/fig_scaling_sweep.png", dpi=130)
    print("saved figures/fig_scaling_sweep.png")


if __name__ == "__main__":
    main()
