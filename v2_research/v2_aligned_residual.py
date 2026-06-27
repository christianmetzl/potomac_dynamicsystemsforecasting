"""
v2_aligned_residual.py  [V2 — EXPLORATORY, NOT part of the V1 submission]

Two ideas to make the quantum reservoir "see better", both tested honestly vs HAR-X
(the strong linear baseline) on the crisis window, n=10, with HAC-DM:

B1 — AIM THE LENS (kernel-target-alignment search). V1 used a random/fixed reservoir
     (tau=2, hx=1, ising, conn=0.5). Here we search reservoir physics (tau-bank, hx,
     connectivity, Ising vs Heisenberg) and pick the config that MAXIMISES kernel-target
     alignment (KTA) on TRAIN only (no test peeking), then forecast. Does aiming the
     distinct features at the target help?

B2 — RESIDUAL HYBRID. Let HAR-X do the linear bulk; fit the quantum reservoir ONLY on
     HAR-X's residuals; final = HAR-X + quantum-residual. If any exploitable nonlinear
     residual exists, this additive design is where it shows.

Honest by construction: selection is train-only; significance is HAC-DM vs HAR-X. We report
whatever it shows. No V1 file is modified.
"""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import feature_pool as fp
from multiscale_chimera import MultiScaleCHIMERA
from scaling_sweep import lin_kernel, kta, feat_dim
from vol_fair_benchmark import ridge_readout, rmse, qlike, mz_r2
from axisB_rigorous import dm_hac

CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
N = 10


def chimera_feats(Qn, n, taus, hx, conn, ham, seed):
    ch = MultiScaleCHIMERA(n_qubits=n, taus=taus, hamiltonian=ham, hx=hx,
                           connectivity=conn, seed=seed)
    ch._reset_feedback()
    return np.array([ch._all_features(w) for w in Qn])


def main():
    t0 = time.time()
    d = fp.build_rich()
    pool, X_har = d["pool"], d["X_har"]
    y_logrv, y_rv = d["y_logrv"], d["y_rv"]
    dts = pd.to_datetime(d["dates"])
    tr = np.where(dts < CRISIS_TR)[0]
    te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]
    yT_log, yT_rv = y_logrv[te], y_rv[te]

    pool_s = fp.scale_pool(pool, tr)
    rich_s = pool_s[:, :N]
    rich_raw = pool[:, :N]
    LINX = np.hstack([rich_raw, X_har])           # HAR-X linear block (rich + HAR)

    def metrics(pred):
        v = np.exp(pred)
        return rmse(yT_log, pred), qlike(yT_rv, v), mz_r2(yT_rv, v)

    # ---- strong linear baseline ----
    harx_pred, _ = ridge_readout(LINX[tr], y_logrv[tr], LINX[te])
    harx_loss = (harx_pred - yT_log) ** 2
    hr, hq, hm = metrics(harx_pred)

    print("#" * 90)
    print("V2 ALIGNED + RESIDUAL (exploratory)  n=10, crisis window")
    print(f"  HAR-X (strong linear baseline): RMSE={hr:.4f}  QLIKE={hq:.4f}  MZ={hm:.3f}")
    print("#" * 90)

    yc_tr = y_logrv[tr] - y_logrv[tr].mean()

    # =================== B1: KTA-alignment search (train-only) ===================
    DEFAULT = dict(taus=(2.0,), hx=1.0, conn=0.5, ham="ising")
    grid = []
    for taus in [(2.0,), (4.0,), (8.0,), (1.0, 2.0, 4.0)]:
        for hx in [0.5, 1.0, 2.0]:
            for conn in [0.5, 0.8]:
                grid.append(dict(taus=taus, hx=hx, conn=conn, ham="ising"))
    grid += [dict(taus=(2.0,), hx=1.0, conn=0.5, ham="heisenberg"),
             dict(taus=(2.0,), hx=0.5, conn=0.8, ham="heisenberg")]

    print("\nB1 — kernel-target-alignment search (KTA on TRAIN; pick best, then forecast):")
    best = None
    for cfg in grid:
        F = chimera_feats(rich_s, N, cfg["taus"], cfg["hx"], cfg["conn"], cfg["ham"], 0)
        k = abs(kta(lin_kernel(F[tr]), yc_tr))
        if best is None or k > best[0]:
            best = (k, cfg)
    # forecast default vs best (3-seed ensemble), each NESTS HAR-X via LINX
    def forecast(cfg, seeds=(0, 1, 2)):
        preds = []
        for s in seeds:
            F = chimera_feats(rich_s, N, cfg["taus"], cfg["hx"], cfg["conn"], cfg["ham"], s)
            D = np.hstack([F, LINX])
            pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
            preds.append(pr)
        return np.mean(preds, axis=0)

    print(f"  best-KTA config: {best[1]}  (train KTA={best[0]:.4f})")
    out = {}
    for label, cfg in [("CHIMERA-default", DEFAULT), ("CHIMERA-aligned", best[1])]:
        pr = forecast(cfg)
        r, q, m = metrics(pr)
        ds, p = dm_hac((pr - yT_log) ** 2, harx_loss)
        out[label] = dict(rmse=r, mz=m, dm=ds, p=p)
        print(f"  {label:<17} RMSE={r:.4f}  MZ={m:.3f}  DM vs HAR-X={ds:+.2f} p={p:.3f}")

    # =================== B2: residual hybrid ===================
    print("\nB2 — residual hybrid (HAR-X linear bulk + quantum on the residual):")
    harx_tr, _ = ridge_readout(LINX[tr], y_logrv[tr], LINX[tr])   # in-sample HAR-X fit on train
    resid_tr = y_logrv[tr] - harx_tr
    preds = []
    for s in (0, 1, 2):
        F = chimera_feats(rich_s, N, DEFAULT["taus"], DEFAULT["hx"], DEFAULT["conn"], DEFAULT["ham"], s)
        # regress HAR-X residual on quantum features only (standardized inside ridge_readout)
        rp, _ = ridge_readout(F[tr], resid_tr, F[te])
        preds.append(harx_pred + rp)            # final = HAR-X(test) + quantum-residual(test)
    hybrid = np.mean(preds, axis=0)
    r, q, m = metrics(hybrid)
    ds, p = dm_hac((hybrid - yT_log) ** 2, harx_loss)
    out["HAR-X+quantum-residual"] = dict(rmse=r, mz=m, dm=ds, p=p)
    print(f"  HAR-X+quantum-residual  RMSE={r:.4f}  MZ={m:.3f}  DM vs HAR-X={ds:+.2f} p={p:.3f}")

    beat = [k for k, v in out.items() if v["dm"] < 0 and v["p"] < 0.05]
    print("\nVERDICT: " + (f"{beat} significantly beat HAR-X (inspect)"
          if beat else "no V2 variant significantly beats HAR-X (honest negative persists at n=10 crisis)"))
    np.save(os.path.join(os.path.dirname(__file__), "v2_aligned_residual_results.npy"),
            dict(harx=dict(rmse=hr, mz=hm), variants=out, best_cfg=best[1]), allow_pickle=True)
    print(f"[{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
