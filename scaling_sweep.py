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
import multivariate_data as mvd
from vol_fair_benchmark import (
    LAGS, SEEDS, rmse, qlike, mz_r2, dm_test, model_confidence_set,
    ridge_readout, esn_features,
)
from qrc_engine import (
    build_ising_hamiltonian, generate_coupling_matrix,
    apply_single_qubit_gate, Ry, measure_full_features,
)
import h0_thresholds as H0

# Phase-2 configurations (fixed; only n is swept)
TAU_1SCALE = (2.0,)             # g(n) anchor architecture (kernel geometry)
TAU_3SCALE = (1.0, 2.0, 4.0)    # mz_gap(n) headline architecture (regime transition)
CRISIS_TRAIN_END = pd.Timestamp("2007-01-01")
CRISIS_TEST_END = pd.Timestamp("2013-01-01")
KERNEL_N = 800                  # train subsample for stable/fast kernel ops (as in Phase 2)


# --------------------------- model & kernel helpers ---------------------------
# Eigendecomposition cache keyed by (n, coupling-seed): U(tau)=V e^{-i lambda tau} V^dag is
# EXACT (matches expm to ~1e-13) and one eigh serves every tau / seed sharing a coupling.
_EIG_CACHE: dict = {}

def _eig(n_qubits, jseed):
    key = (n_qubits, jseed)
    if key not in _EIG_CACHE:
        J = generate_coupling_matrix(n_qubits, 0.5, seed=jseed)   # matches Phase-2 (conn=0.5)
        H = build_ising_hamiltonian(n_qubits, J, hx=1.0)
        _EIG_CACHE[key] = np.linalg.eigh(H)
    return _EIG_CACHE[key]

def _reservoir_features(Q, n_qubits, jseed, tau, reupload=1):
    """One delay-embedding QRC reservoir's features (no feedback), with a cached eigh-based U.
    Data re-uploading (Perez-Salinas 2020): with reupload=R, encode successive n-feature
    blocks of each row interleaved with evolution - [encode emb[0:n] -> U -> encode emb[n:2n]
    -> U -> ...] x R - so n qubits absorb up to R*n input features through depth. reupload=1
    reduces exactly to the Phase-2 single-encode reservoir (anchor preserved)."""
    w, V = _eig(n_qubits, jseed)
    U = (V * np.exp(-1j * w * tau)) @ V.conj().T
    fdim = n_qubits + n_qubits * (n_qubits - 1) // 2
    F = np.empty((len(Q), fdim))
    for i, emb in enumerate(Q):
        psi = np.zeros(2 ** n_qubits, dtype=complex); psi[0] = 1.0
        for layer in range(reupload):
            blk = emb[layer * n_qubits:(layer + 1) * n_qubits]
            for q in range(min(len(blk), n_qubits)):
                psi = apply_single_qubit_gate(psi, Ry(np.pi * np.clip(blk[q], 0, 1)), q, n_qubits)
            psi = U @ psi
        F[i] = measure_full_features(psi, n_qubits)
    return F

def chimera_features_n(Q, taus, seed, n_qubits, reupload=1):
    """Same model as vol_fair_benchmark.chimera_features / MultiScaleCHIMERA (n_qubits
    parametrized): a tau-bank where reservoir i uses coupling seed+i and tau=taus[i],
    features concatenated. Eigh-cached -> the n=8 row still reproduces the Phase-2 anchors."""
    return np.hstack([_reservoir_features(Q, n_qubits, seed + i, taus[i], reupload)
                      for i in range(len(taus))])


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
def compute_g(n, Q, tr, y, reupload=1):
    """g(n): geometric difference of the matched ESN kernel from the CHIMERA-1scale
    kernel, on an evenly-spaced N=KERNEL_N train subsample (mirrors kernel_analysis.py).
    Both maps receive the SAME reupload*n input features (quantum re-uploads them across n
    qubits; the ESN sees them flat)."""
    idx = np.linspace(0, len(tr) - 1, min(KERNEL_N, len(tr))).astype(int)
    trk = np.array(tr)[idx]
    Qn = Q[trk][:, :reupload * n]                         # identical inputs (reupload*n feats)
    FQ = chimera_features_n(Qn, TAU_1SCALE, 0, n, reupload)  # quantum, n-dependent feat dim
    F108 = esn_features(Qn, 108, 0)                       # matched classical
    F108b = esn_features(Qn, 108, 1)                      # classical-classical control
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


def compute_mz_gap(n, Qc, tr, te, y_logrv, y_rv, Xraw, Xhar, reupload=1):
    """mz_gap(n): MZ-R2(CHIMERA-3scale ensemble) - MZ-R2(HAR) on the crisis split, with
    DM(CHIMERA vs HAR) on point loss, a block-bootstrap MZ-gap test, and MCS membership.
    Fair-comparison: the linear readout LIN gets the raw (unscaled-log) version of EXACTLY
    the reupload*n inputs the reservoir encodes, plus HAR - so any reservoir gain is genuine
    nonlinearity beyond linear use of the same inputs."""
    width = reupload * n
    Xn = Xraw[:, :width]
    Qcn = Qc[:, :width]
    LIN = np.hstack([Xn, Xhar])
    yT_log, yT_rv = y_logrv[te], y_rv[te]

    har_pred, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])

    def reservoir_pred(kind):
        sp = []
        for sd in SEEDS:
            F = (esn_features(Qcn, 108, sd) if kind == "esn"
                 else chimera_features_n(Qcn, TAU_3SCALE, sd, n, reupload))
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
    ap.add_argument("--encoding", choices=["univariate", "multivariate"], default="univariate")
    ap.add_argument("--reupload", type=int, default=1,
                    help="data re-uploading depth R: n qubits absorb R*n panel features")
    ap.add_argument("--out", default="scaling_sweep_results.json")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()
    # effective encoding label (drives the pre-registered verdict + output names)
    enc_label = ("multivariate_reupload" if (args.encoding == "multivariate" and args.reupload > 1)
                 else args.encoding)
    if args.out == "scaling_sweep_results.json" and enc_label != "univariate":
        args.out = f"scaling_sweep_results_{enc_label}.json"

    if args.encoding == "multivariate":
        data = mvd.build_panel_supervised(horizon=1)
        Xraw = data["X_panel"]                                  # ordered multivariate panel
        Xhar = data["X_har"]
        enc_desc = f"multivariate realized-measure panel ({data['n_features']} feats; " \
                   f"first 8 == univariate rv5 lags, then new measures)"
    else:
        df = vd.load_spx_rv()
        data = vd.build_supervised(df, horizon=1, lags=LAGS)
        Xraw = data["X_lags"]                                   # 8 univariate log-RV lags
        Xhar = data["X_har"]
        enc_desc = "univariate 8-lag log-RV encoder"
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    dts = pd.to_datetime(data["dates"])

    # headline split (for g): 70/30 chronological
    tr_h, te_h = vd.make_splits(len(y_logrv), train_frac=0.70)
    lo, hi = Xraw[tr_h].min(0), Xraw[tr_h].max(0); rng = np.where(hi - lo == 0, 1, hi - lo)
    Q_h = np.clip((Xraw - lo) / rng, 0.0, 1.0)

    # crisis split (for mz_gap): GFC 2008 in the test set
    tr_c = np.where(dts < CRISIS_TRAIN_END)[0]
    te_c = np.where((dts >= CRISIS_TRAIN_END) & (dts < CRISIS_TEST_END))[0]
    loc, hic = Xraw[tr_c].min(0), Xraw[tr_c].max(0); rngc = np.where(hic - loc == 0, 1, hic - loc)
    Q_c = np.clip((Xraw - loc) / rngc, 0.0, 1.0)

    print("=" * 92)
    print(f"CHIMERA-QRC Phase-3  SCALING SWEEP  encoding={enc_label}  (reupload={args.reupload})")
    print(f"  input: {enc_desc}" + (f"; data re-uploading R={args.reupload} "
          f"(n qubits absorb {args.reupload}*n features)" if args.reupload > 1 else ""))
    print(f"  g(n): headline split, kernel N={KERNEL_N}, 1-scale tau={TAU_1SCALE}")
    print(f"  mz_gap(n): crisis split {dts[tr_c[0]].date()}..{dts[te_c[-1]].date()} "
          f"(train n={len(tr_c)}, test n={len(te_c)}), 3-scale tau={TAU_3SCALE}, seeds={SEEDS}")
    print(f"  verdict via PRE-REGISTERED h0_thresholds.py (encoding='{enc_label}')")
    print("=" * 92)

    rows = []
    t_start = time.time()
    for n in args.ns:
        t0 = time.time()
        g = compute_g(n, Q_h, tr_h, y_logrv, args.reupload)
        mz = compute_mz_gap(n, Q_c, tr_c, te_c, y_logrv, y_rv, Xraw, Xhar, args.reupload)
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
    if 8 in ns and args.reupload == 1:
        a = next(r for r in rows if r["n"] == 8)
        anchor_passed, anchor_msg = H0.anchor_ok(a["g"], a["mz_gap"])
    elif args.reupload > 1:
        # reupload>1 is a deeper model not expected to match the Phase-2 anchor;
        # the harness itself was validated at reupload=1.
        anchor_passed = True
        anchor_msg = f"anchor gate N/A for reupload={args.reupload} (harness validated at reupload=1)"

    g_stat = H0.g_curve_status(ns, gs, g_control)
    d_stat = H0.deff_status(ns, deffs)
    acc_stat = H0.accuracy_status(last["mz_gap"], last["dm_stat"], last["dm_p"],
                                  last["chimera_in_mcs"], last["mz_gap_boot_p"])
    verdict = H0.h0_verdict(enc_label, max(ns),
                            anchor_passed if anchor_passed is not None else False,
                            g_stat, d_stat, acc_stat)

    print("\n" + "=" * 92)
    print(f"PRE-REGISTERED VERDICT (encoding={enc_label})")
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
        "encoding": enc_label, "reupload": args.reupload, "ns": ns, "g_control": g_control,
        "anchor_passed": anchor_passed, "g_status": g_stat, "deff_status": d_stat,
        "accuracy_status": acc_stat, "verdict": verdict.label,
        "verdict_rationale": verdict.rationale, "rows": rows,
    }
    json.dump(summary, open(args.out, "w"), indent=2)
    pd.DataFrame(rows).to_csv(args.out.replace(".json", ".csv"), index=False)
    print(f"saved {args.out} and {args.out.replace('.json', '.csv')}")

    if not args.no_plot and len(rows) >= 1:
        try:
            _plot(rows, g_control, verdict, enc_label)
        except Exception as e:
            print(f"(plot skipped: {e})")


def _plot(rows, g_control, verdict, encoding="univariate"):
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
    fig.suptitle(f"CHIMERA-QRC scaling sweep ({encoding})  —  verdict: {verdict.label}",
                 fontsize=11)
    fig.tight_layout()
    out = f"figures/fig_scaling_sweep_{encoding}.png"
    fig.savefig(out, dpi=130)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
