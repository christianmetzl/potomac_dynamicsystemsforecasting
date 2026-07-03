"""
axisB_rigorous.py - the credibility-hardened Axis-B experiment.

Addresses the referee critique of the first Axis-B result (which compared CHIMERA to
PLAIN HAR and to a memoryless ESN on a single window with an ensemble-only,
unadjusted DM test). Here we run the GOLD-STANDARD nested comparison so the quantum
claim is separable from "richer inputs help any model":

MODELS (all share the SAME information set; the only difference is how the rich
realized-measure inputs are processed):
  HAR     : ridge on [HAR components]                               (weak linear bar)
  HAR-X   : ridge on [rich inputs (first n pool cols) + HAR]        (STRONG linear bar,
            = the same leverage/semivariance/jump features used LINEARLY, no reservoir)
  ESN     : ridge on [recurrent-ESN features(rich) + rich + HAR]    (classical nonlinear,
            a TRUE sequential echo-state reservoir, not reset-per-row)
  RFF     : ridge on [random-Fourier-features(rich) + rich + HAR]   (classical RBF kernel)
  CHIMERA : ridge on [quantum features(rich) + rich + HAR]          (quantum nonlinear)

Because CHIMERA, ESN and RFF all include the rich inputs LINEARLY (the HAR-X block),
each NESTS HAR-X: it can only beat HAR-X if its nonlinear feature map adds predictive
value beyond the linear span of identical information. CHIMERA vs HAR-X is therefore
the decisive, fair test of quantum *nonlinearity*; CHIMERA vs ESN/RFF tests quantum
vs classical nonlinearity at matched inputs and feature count.

RIGOUR:
  * windows: crisis (2007-2012, GFC in test) AND calm (2014-2020) for robustness.
  * seeds: 8 per stochastic model; per-seed RMSE spread reported (not hidden in a mean).
  * DM test: Newey-West HAC variance (crisis loss is serially correlated) + HLN.
  * multiple comparisons: Holm-adjusted across the full family of tests; n=10 is
    pre-declared the focal point but ALL n are reported.

Usage:
  python3 axisB_rigorous.py            # crisis n=8,10,12 + calm n=10, 8 seeds
  python3 axisB_rigorous.py --quick    # n=10 only, 3 seeds, crisis only

Team EIGENNEXUS | GIC 2026 - Phase 3 (Axis B, hardened)
"""
import argparse
import time
import numpy as np
import pandas as pd

import volatility_data as vd
import feature_pool as fp
import scaling_sweep as ss
from classical_baselines import EchoStateNetwork
from vol_fair_benchmark import rmse, qlike, mz_r2, ridge_readout, model_confidence_set

RIG_SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)
CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")


# --------------------------------------------------------------------------
# Diebold-Mariano with Newey-West HAC variance (+ HLN small-sample correction)
# --------------------------------------------------------------------------
def dm_hac(loss1, loss2, lag=None):
    """DM test on d = loss1 - loss2 with a Newey-West HAC long-run variance.
    Returns (stat, two-sided p). stat<0 => model1 better. lag auto if None."""
    from scipy import stats
    d = np.asarray(loss1, float) - np.asarray(loss2, float)
    T = len(d); db = d.mean()
    if lag is None:
        lag = int(np.floor(4 * (T / 100.0) ** (2.0 / 9.0)))
    g0 = np.mean((d - db) ** 2)
    lrv = g0
    for k in range(1, lag + 1):
        cov = np.mean((d[k:] - db) * (d[:-k] - db))
        lrv += 2.0 * (1.0 - k / (lag + 1.0)) * cov
    if lrv <= 0:
        return np.nan, np.nan
    stat = db / np.sqrt(lrv / T)
    # HLN small-sample correction (h=1)
    stat *= np.sqrt((T - 1) / T) if T > 1 else 1.0
    p = 2.0 * (1.0 - stats.t.cdf(abs(stat), df=T - 1))
    return float(stat), float(p)


def holm(pvals: dict):
    """Holm-Bonferroni adjustment. pvals: name->p. Returns name->adjusted p."""
    items = sorted(((k, v) for k, v in pvals.items() if not np.isnan(v)), key=lambda x: x[1])
    m = len(items); out = {}
    prev = 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        out[k] = adj; prev = adj
    for k, v in pvals.items():
        out.setdefault(k, np.nan)
    return out


# --------------------------------------------------------------------------
# Classical nonlinear controls
# --------------------------------------------------------------------------
def esn_recurrent_features(X_seq, n_res, seed):
    """TRUE sequential echo-state features: process the chronological series with
    state recurrence (no reset-per-row), so the reservoir actually has memory."""
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=0.9, leaking_rate=0.5,
                           input_scaling=1.0, connectivity=0.05, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(X_seq.shape[1])
    esn.reset()
    F = np.empty((len(X_seq), n_res))
    for i, u in enumerate(X_seq):          # chronological, recurrent
        F[i] = esn.step(u)
    return F


def rbf_gamma(Xtr):
    """RBF bandwidth via the median heuristic on TRAIN rows only (no test peeking)."""
    rng = np.random.RandomState(0)
    idx = rng.choice(len(Xtr), min(400, len(Xtr)), replace=False)
    sub = Xtr[idx]
    D2 = np.sum((sub[:, None, :] - sub[None, :, :]) ** 2, axis=-1)
    med = np.median(D2[D2 > 0]) if np.any(D2 > 0) else 1.0
    return 1.0 / (med + 1e-12)


def rff_features(X, n_feat, seed, gamma):
    """Random Fourier features approximating an RBF kernel (classical nonlinear map).
    gamma is supplied (computed train-only) to avoid look-ahead."""
    rng = np.random.RandomState(seed)
    d = X.shape[1]
    W = rng.normal(0, np.sqrt(2 * gamma), (d, n_feat))
    b = rng.uniform(0, 2 * np.pi, n_feat)
    return np.sqrt(2.0 / n_feat) * np.cos(X @ W + b)


# --------------------------------------------------------------------------
# One window
# --------------------------------------------------------------------------
def run_window(label, tr, te, pool, X_har, y_logrv, y_rv, ns, seeds, focal=10):
    pool_s = fp.scale_pool(pool, tr)                  # [0,1] on train only (for encoders)
    yT_log, yT_rv = y_logrv[te], y_rv[te]

    def metrics(pred):
        v = np.exp(pred)
        return dict(rmse=rmse(yT_log, pred), qlike=qlike(yT_rv, v), mz=mz_r2(yT_rv, v))

    # plain HAR (weak bar)
    har_pred, _ = ridge_readout(X_har[tr], y_logrv[tr], X_har[te])
    har_loss = (har_pred - yT_log) ** 2
    out = {"HAR": dict(**metrics(har_pred), pred=har_pred)}

    results = {}
    for n in ns:
        rich = pool[:, :n]                            # raw rich inputs (first n pool cols)
        rich_s = pool_s[:, :n]                        # scaled, for encoders
        LINX = np.hstack([rich, X_har])              # the HAR-X linear block (rich + HAR)
        nfeat = ss.feat_dim(n)

        # HAR-X : strong linear bar (rich inputs used linearly)
        harx_pred, _ = ridge_readout(LINX[tr], y_logrv[tr], LINX[te])

        gamma = rbf_gamma(rich_s[tr])     # RFF bandwidth, train-only

        # stochastic nonlinear models, per seed (each NESTS HAR-X via the LINX block)
        per = {"ESN": [], "RFF": [], "CHIMERA": []}
        for sd in seeds:
            for name, F in (("CHIMERA", ss.chimera_features_n(rich_s, n, (2.0,), sd)),
                            ("ESN", esn_recurrent_features(rich_s, nfeat, sd)),
                            ("RFF", rff_features(rich_s, nfeat, sd, gamma))):
                D = np.hstack([F, LINX])
                pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
                per[name].append(pr)

        rec = {"HAR-X": dict(**metrics(harx_pred), pred=harx_pred, seeds_rmse=None)}
        for name, preds in per.items():
            ens = np.mean(preds, axis=0)
            seed_rmse = [rmse(yT_log, p) for p in preds]
            rec[name] = dict(**metrics(ens), pred=ens,
                             seeds_rmse=seed_rmse,
                             rmse_sd=float(np.std(seed_rmse)))
        results[n] = rec

    return out, results, har_loss, yT_log


def _print_window(label, har, results, har_loss, yT_log, focal):
    print("\n" + "=" * 92, flush=True)
    print(f"WINDOW: {label}    (HAR plain: RMSE={har['HAR']['rmse']:.4f}  MZ={har['HAR']['mz']:.3f})")
    print("=" * 92)
    fam = {}        # family of CHIMERA-vs-X p-values for Holm
    summary = []    # serializable rows for the npy (no prediction arrays)
    har_rmse = har["HAR"]["rmse"]; har_mz = har["HAR"]["mz"]
    for n, rec in results.items():
        print(f"\n n={n}   {'model':<9}{'RMSE':>9}{'±seed':>8}{'QLIKE':>9}{'MZ_R2':>8}"
              f"{'DM vs HAR-X':>13}{'p(HAC)':>9}", flush=True)
        harx_loss = (rec["HAR-X"]["pred"] - yT_log) ** 2
        for name in ("HAR-X", "ESN", "RFF", "CHIMERA"):
            m = rec[name]; sd = m.get("rmse_sd")
            sd_s = f"{sd:.4f}" if sd is not None else "   -"
            row = dict(window=label, n=n, model=name, rmse=m["rmse"], mz=m["mz"],
                       qlike=m["qlike"], rmse_sd=sd, har_rmse=har_rmse, har_mz=har_mz)
            if name == "HAR-X":
                dm_s = ""; p_s = ""
            else:
                stat, p = dm_hac((m["pred"] - yT_log) ** 2, harx_loss)
                dm_s = f"{stat:>+8.2f}"; p_s = f"{p:>9.3f}"
                row["dm_vs_harx_stat"] = stat; row["dm_vs_harx_p"] = p
                if name == "CHIMERA":
                    fam[f"{label}:n{n}:CHIMERAvsHARX"] = p
            summary.append(row)
            print(f"        {name:<9}{m['rmse']:>9.4f}{sd_s:>8}{m['qlike']:>9.4f}"
                  f"{m['mz']:>8.3f}{dm_s:>13}{p_s}", flush=True)
        # quantum-vs-classical at matched inputs
        c = rec["CHIMERA"]
        for cl in ("ESN", "RFF"):
            stat, p = dm_hac((c["pred"] - yT_log) ** 2, (rec[cl]["pred"] - yT_log) ** 2)
            fam[f"{label}:n{n}:CHIMERAvs{cl}"] = p
            summary.append(dict(window=label, n=n, model=f"CHIMERAvs{cl}",
                                dm_stat=stat, dm_p=p))
            print(f"        CHIMERA vs {cl}: DM(HAC)={stat:+.2f}  p={p:.3f}", flush=True)
    return fam, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    seeds = (0, 1, 2) if args.quick else RIG_SEEDS
    ns = [10] if args.quick else [8, 10, 12]

    t0 = time.time()
    print("#" * 92)
    print("CHIMERA-QRC AXIS-B (RIGOROUS): HAR-X + recurrent-ESN + RFF controls, "
          "HAC-DM, per-seed, Holm")
    print(f"seeds={seeds}  ns={ns}  focal n=10")
    print("#" * 92)

    d = fp.build_rich()
    pool, X_har = d["pool"], d["X_har"]
    y_logrv, y_rv = d["y_logrv"], d["y_rv"]
    dts = pd.to_datetime(d["dates"])

    fam_all = {}; summary_all = []; mcs_all = {}

    def _mcs_decisive(label, res_w, yT_w, focal=10):
        """Model Confidence Set on the DECISIVE Axis-B family (HAR-X/ESN/RFF/CHIMERA, focal n)."""
        foc = res_w[focal]
        losses = {m: (foc[m]["pred"] - yT_w) ** 2 for m in ("HAR-X", "ESN", "RFF", "CHIMERA")}
        surv, mp = model_confidence_set(losses)
        mcs_all[label] = dict(pvals=mp, survivors=sorted(surv))
        print(f"\n  MCS (decisive Axis-B family, {label}, n={focal}): "
              + ", ".join(f"{k} p={v:.3f}{'*' if k in surv else ''}" for k, v in mp.items()))
        print("   (* = retained in the 95% Model Confidence Set)")
    # crisis window
    tr = np.where(dts < CRISIS_TR)[0]
    te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]
    har, res, hl, yT = run_window("crisis", tr, te, pool, X_har, y_logrv, y_rv, ns, seeds)
    fam, summ = _print_window("crisis 2007-2012 (GFC in test)", har, res, hl, yT, 10)
    fam_all.update(fam); summary_all += summ
    if 10 in res:
        _mcs_decisive("crisis", res, yT)

    # calm window (robustness): 70/30 chronological -> test ~2014-2020
    if not args.quick:
        trc, tec = vd.make_splits(len(y_logrv), 0.70)
        har2, res2, hl2, yT2 = run_window("calm", trc, tec, pool, X_har, y_logrv, y_rv, [10], seeds)
        fam2, summ2 = _print_window("calm 2014-2020 (robustness)", har2, res2, hl2, yT2, 10)
        fam_all.update(fam2); summary_all += summ2
        _mcs_decisive("calm", res2, yT2)

    # Holm across the whole family
    adj = holm(fam_all)
    print("\n" + "=" * 92)
    print("MULTIPLE-COMPARISON CONTROL (Holm-adjusted p across the full family)")
    print("=" * 92)
    for k in sorted(fam_all):
        sig = "  *sig@0.05" if adj[k] < 0.05 else ""
        print(f"  {k:<34} raw p={fam_all[k]:.3f}   Holm p={adj[k]:.3f}{sig}")

    if not args.quick:           # --quick must not clobber the committed full 8-seed artifact
        np.save("axisB_rigorous_results.npy",
                dict(family_raw=fam_all, family_holm=adj, summary=summary_all, mcs=mcs_all),
                allow_pickle=True)
        print(f"\nsaved axisB_rigorous_results.npy   [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] skipped writing results (committed full-run artifact preserved) [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
