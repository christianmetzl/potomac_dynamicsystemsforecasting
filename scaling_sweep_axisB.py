"""
scaling_sweep_axisB.py - the decisive Axis-B experiment.

The fixed-input sweep (scaling_sweep.py) REFUTED H0: adding idle qubits to a
univariate 8-lag encoder monotonically degrades kernel distinctness g(n) and
crisis forecast accuracy. The pre-registered conclusion was that qubits must carry
NEW information. This script tests exactly that, head-to-head, at matched qubit
count:

  univariate : encode the 8 log-RV lags; qubits beyond 8 sit idle  (the baseline)
  rich       : encode an information pool that scales with n - the 8 lags PLUS
               leverage / realized-semivariance / jump / overnight features
               (feature_pool.py), so every added qubit is informed.

At n=8 the two are identical by construction (rich's first 8 columns ARE the 8
lags); divergence appears at n>=10 where 'univariate' wastes qubits and 'rich'
feeds them new realized-measure information.

FAIRNESS CONTROL (rubric-critical). For every (n, encoder) we run BOTH the quantum
reservoir AND the matched classical reservoir (ESN, same feature count, same rich
inputs, same hybrid HAR readout). This isolates QUANTUM value at fixed inputs: the
gain must not be merely "better inputs help any model". Reported:
  - q  MZ-gap  : CHIMERA MZ_R2 - HAR MZ_R2          (does quantum beat HAR)
  - e  MZ-gap  : ESN     MZ_R2 - HAR MZ_R2          (does classical also gain)
  - DM(C vs E) : Diebold-Mariano CHIMERA vs ESN     (does quantum beat classical
                 at IDENTICAL rich inputs)

Reuses the validated engine, kernel helpers, and pre-registration thresholds.

Usage:
  python3 scaling_sweep_axisB.py            # n = 8,10,12
  python3 scaling_sweep_axisB.py --quick    # n = 8,10 ; 1 seed
  python3 scaling_sweep_axisB.py --ns 8 10 12 --scheme rich

Team EIGENNEXUS | GIC 2026 - Phase 3 (Axis B)
"""
import argparse
import time
import numpy as np

import volatility_data as vd
import feature_pool as fp
import preregistration as prereg
import scaling_sweep as ss      # geom_diff, lin_kernel, eff_dim, num_rank, kta, chimera_features_n, feat_dim
from vol_fair_benchmark import (
    SEEDS, rmse, qlike, mz_r2, dm_test, ridge_readout, esn_features,
)
import pandas as pd

MAX_DENSE_N = ss.MAX_DENSE_N


def _kernel_point(Q, n, yc, seed=0):
    """g(ESN||CHIMERA), control, D_eff, rank, KTA for encoded input Q at n qubits."""
    FQ = ss.chimera_features_n(Q, n, (2.0,), seed)
    nr = ss.feat_dim(n)
    Fe = esn_features(Q, nr, seed)
    Feb = esn_features(Q, nr, seed + 1)
    KQ, Ke, Keb = ss.lin_kernel(FQ), ss.lin_kernel(Fe), ss.lin_kernel(Feb)
    return dict(g=ss.geom_diff(Ke, KQ), g_ctrl=ss.geom_diff(Ke, Keb),
                d_eff=ss.eff_dim(KQ), rank=ss.num_rank(KQ), kta=ss.kta(KQ, yc),
                n_feat=FQ.shape[1])


def _ensemble(features_list, LIN, y_logrv, tr, te):
    preds = []
    for F in features_list:
        D = np.hstack([F, LIN])
        pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
        preds.append(pr)
    return np.mean(preds, axis=0)


def _forecast_models(Qf, n, LIN, y_logrv, tr, te, seeds):
    """Return ensemble test predictions for CHIMERA and the matched ESN at n qubits."""
    q = _ensemble([ss.chimera_features_n(Qf, n, (2.0,), sd) for sd in seeds],
                  LIN, y_logrv, tr, te)
    nr = ss.feat_dim(n)
    e = _ensemble([esn_features(Qf, nr, sd) for sd in seeds],
                  LIN, y_logrv, tr, te)
    return q, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--scheme", choices=["rich", "reupload"], default="rich")
    args = ap.parse_args()
    ns = args.ns or ([8, 10] if args.quick else [8, 10, 12])
    seeds = (0,) if args.quick else SEEDS
    kern_sub = 300 if args.quick else ss.KERNEL_SUBSAMPLE

    t_all = time.time()
    print("#" * 84)
    print("CHIMERA-QRC AXIS-B SWEEP  (univariate vs rich encoder, matched qubits)")
    print(f"qubit counts: {ns}   seeds: {seeds}   rich scheme: {args.scheme}")
    print("#" * 84)

    d = fp.build_rich()
    pool, names = d["pool"], d["names"]
    X_lags, X_har = d["X_lags"], d["X_har"]
    y_logrv, y_rv = d["y_logrv"], d["y_rv"]
    dts = pd.to_datetime(d["dates"])
    P = pool.shape[1]
    print(f"rich pool: N={len(y_logrv)} rows, P={P} features")
    print(f"priority order: {names}\n")

    # ---- kernel geometry (calm 70/30 split) ----
    trk_full, _ = vd.make_splits(len(y_logrv), 0.70)
    idx = np.linspace(0, len(trk_full) - 1, min(kern_sub, len(trk_full))).astype(int)
    trk = np.array(trk_full)[idx]
    yc = y_logrv[trk] - y_logrv[trk].mean()
    pool_sk = fp.scale_pool(pool, trk_full)

    # ---- forecast crisis split ----
    tr = np.where(dts < ss.CRISIS_TRAIN_END)[0]
    te = np.where((dts >= ss.CRISIS_TRAIN_END) & (dts < ss.CRISIS_TEST_END))[0]
    pool_sc = fp.scale_pool(pool, tr)
    LIN = np.hstack([X_lags, X_har])           # identical linear info for both encoders
    yT_log, yT_rv = y_logrv[te], y_rv[te]
    har_pred, _ = ridge_readout(X_har[tr], y_logrv[tr], X_har[te])
    mz_har = mz_r2(yT_rv, np.exp(har_pred))
    rmse_har = rmse(yT_log, har_pred)
    har_loss = (har_pred - yT_log) ** 2
    print(f"HAR baseline (crisis): RMSE={rmse_har:.4f}  MZ_R2={mz_har:.3f}\n")

    print("=" * 84)
    print(f"{'n':>3}{'enc':>6}{'#f':>4}{'g(E||C)':>10}{'D_eff':>7}"
          f"{'qMZgap':>8}{'qDMvH':>7}{'eMZgap':>8}{'C-vs-E DM_p':>12}")
    print("-" * 84)
    rows = {"univariate": [], args.scheme: []}
    for n in ns:
        if n > MAX_DENSE_N:
            print(f"{n:>3}  -- skipped (dense frontier n={MAX_DENSE_N}; sparse follow-up)")
            continue
        for scheme in ("univariate", args.scheme):
            if scheme == "univariate":
                Qk = pool_sk[:, :min(n, 8)][trk]
                Qf = pool_sc[:, :min(n, 8)]
                n_enc = min(n, 8)
            else:
                Qk = fp.encode(pool_sk, n, scheme)[trk]
                Qf = fp.encode(pool_sc, n, scheme)
                n_enc = Qf.shape[1]
            kp = _kernel_point(Qk, n, yc)
            q_ens, e_ens = _forecast_models(Qf, n, LIN, y_logrv, tr, te, seeds)
            mz_q = mz_r2(yT_rv, np.exp(q_ens)); mz_e = mz_r2(yT_rv, np.exp(e_ens))
            _, qdm_h = dm_test((q_ens - yT_log) ** 2, har_loss)            # CHIMERA vs HAR
            _, ce_dm = dm_test((q_ens - yT_log) ** 2, (e_ens - yT_log) ** 2)  # CHIMERA vs ESN
            rec = dict(n=n, scheme=scheme, n_enc=n_enc, mz_q=mz_q, mz_e=mz_e,
                       mz_gap=mz_q - mz_har, e_mz_gap=mz_e - mz_har,
                       q_dm_har=qdm_h, c_vs_e_dm=ce_dm,
                       rmse_gap=rmse(yT_log, q_ens) - rmse_har, **kp)
            rows[scheme].append(rec)
            print(f"{n:>3}{scheme[:5]:>6}{n_enc:>4}{kp['g']:>10.2f}{kp['d_eff']:>7.2f}"
                  f"{mz_q - mz_har:>+8.3f}{qdm_h:>7.3f}{mz_e - mz_har:>+8.3f}{ce_dm:>12.3f}")
        print("-" * 84)

    # ---- head-to-head verdict + pre-registration on the rich arm ----
    uni, rich = rows["univariate"], rows[args.scheme]
    print("\n" + "=" * 84)
    print("AXIS-B HEAD-TO-HEAD")
    print("  dg = rich g - univariate g (informed vs idle qubits)")
    print("  dMZ = rich MZ-gap - univariate MZ-gap")
    print("  quantum edge = rich CHIMERA MZ-gap - rich ESN MZ-gap (same rich inputs)")
    print("=" * 84)
    for u, r in zip(uni, rich):
        dg = r["g"] - u["g"]; dmz = r["mz_gap"] - u["mz_gap"]
        qedge = r["mz_gap"] - r["e_mz_gap"]
        print(f"  n={r['n']:>2}: dg={dg:>+8.2f}  dMZ={dmz:>+.3f}  "
              f"rich qMZ-gap={r['mz_gap']:>+.3f}(DMvH p={r['q_dm_har']:.3f})  "
              f"quantum-edge-vs-ESN={qedge:>+.3f}(DM p={r['c_vs_e_dm']:.3f})")

    if len(rich) >= 2:
        ns_c = [r["n"] for r in rich]
        v0 = prereg.evaluate_H0(ns_c, [r["g"] for r in rich],
                                [r["mz_gap"] for r in rich],
                                [r["q_dm_har"] for r in rich],
                                float(np.median([r["g_ctrl"] for r in rich])))
        v4 = prereg.evaluate_H4(ns_c, [r["d_eff"] for r in rich])
        print("\nPRE-REGISTERED ADJUDICATION (rich encoder):")
        for v in (v0, v4):
            rho = v.get("g_spearman_rho", v.get("d_eff_spearman_rho"))
            print(f"  [{v['hypothesis']}] {v['verdict']}  (rho={rho})")

    _figure(uni, rich, args.scheme)
    np.save("scaling_sweep_axisB_results.npy",
            dict(ns=ns, univariate=uni, rich=rich, scheme=args.scheme,
                 mz_har=mz_har, rmse_har=rmse_har), allow_pickle=True)
    print(f"\nsaved scaling_sweep_axisB_results.npy")
    print(f"[total wall-clock {time.time() - t_all:.1f}s]")


def _figure(uni, rich, scheme, path="figures/fig_scaling_axisB.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(figure skipped: {e})")
        return
    if not uni or not rich:
        return
    nu = [r["n"] for r in uni]; nr = [r["n"] for r in rich]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
    ax[0].plot(nu, [r["g"] for r in uni], "s--", color="gray", label="univariate (idle qubits)")
    ax[0].plot(nr, [r["g"] for r in rich], "o-", color="C0", label=f"{scheme} (informed)")
    ax[0].set_title("Kernel distinctness g(n)"); ax[0].set_xlabel("qubits n")
    ax[0].set_ylabel("g(ESN||CHIMERA)"); ax[0].legend(fontsize=8)
    ax[1].axhline(0, color="k", lw=0.8)
    ax[1].plot(nu, [r["mz_gap"] for r in uni], "s--", color="gray", label="univariate (CHIMERA)")
    ax[1].plot(nr, [r["mz_gap"] for r in rich], "o-", color="C3", label=f"{scheme} (CHIMERA)")
    ax[1].plot(nr, [r["e_mz_gap"] for r in rich], "^:", color="C1", label=f"{scheme} (ESN control)")
    ax[1].set_title("Crisis MZ gap over HAR"); ax[1].set_xlabel("qubits n")
    ax[1].set_ylabel("MZ_R2(model) - MZ_R2(HAR)"); ax[1].legend(fontsize=8)
    fig.suptitle("Axis B: informed encoding-density vs idle qubit scaling", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"saved figure -> {path}")


if __name__ == "__main__":
    main()
