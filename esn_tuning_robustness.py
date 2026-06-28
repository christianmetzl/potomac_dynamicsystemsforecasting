"""
esn_tuning_robustness.py  [rigor hardening — rebut "the ESN was size-matched-to-cripple, never tuned"]

A reviewer's sharpest fair objection to the decisive Axis-B test (`axisB_rigorous.py`) is that the
recurrent ESN is given exactly feat_dim(n)=n+C(n,2) nodes (55 at n=10) with FIXED hyperparameters
(spectral_radius=0.9, leaking_rate=0.5), i.e. matched on readout DIMENSION, not capacity, and never
tuned. This script removes that objection: on the IDENTICAL crisis window / data / split / HAR-X
nesting, it gives the classical ESN every advantage — a grid over reservoir SIZE (up to 800 nodes,
>14x the quantum readout) and (spectral radius, leaking rate), SELECTED on a chronological
validation tail (no test peeking) — then compares the TUNED ESN's test RMSE to CHIMERA's.

If the tuned, size-unconstrained ESN ties or beats CHIMERA, the honest negative is STRENGTHENED:
the quantum reservoir shows no edge even against a properly optimized classical reservoir.

Usage:  python3 esn_tuning_robustness.py            # focal n=10 crisis window
        python3 esn_tuning_robustness.py --quick    # smaller grid
"""
import argparse
import time
import numpy as np
import pandas as pd

import feature_pool as fp
import scaling_sweep as ss
from classical_baselines import EchoStateNetwork
from vol_fair_benchmark import rmse, ridge_readout

CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
N = 10


def esn_feat(X_seq, n_res, sr, leak, seed):
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=sr, leaking_rate=leak,
                           input_scaling=1.0, connectivity=0.05, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(X_seq.shape[1]); esn.reset()
    F = np.empty((len(X_seq), n_res))
    for i, u in enumerate(X_seq):
        F[i] = esn.step(u)
    return F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    sizes = [55, 200, 800] if args.quick else [55, 100, 200, 400, 800]
    srs = [0.9] if args.quick else [0.80, 0.95, 0.99]
    leaks = [0.5] if args.quick else [0.3, 0.6, 0.9]
    esn_seeds = (0,) if args.quick else (0, 1)
    chim_seeds = (0, 1, 2) if args.quick else (0, 1, 2, 3, 4)
    t0 = time.time()

    d = fp.build_rich()
    pool, X_har = d["pool"], d["X_har"]
    y = d["y_logrv"]; dts = pd.to_datetime(d["dates"])
    tr = np.where(dts < CRISIS_TR)[0]
    te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]
    pool_s = fp.scale_pool(pool, tr)
    rich_s = pool_s[:, :N]
    LINX = np.hstack([pool[:, :N], X_har])           # HAR-X linear block (rich + HAR), nested by all
    yT = y[te]

    # chronological validation tail INSIDE crisis-train for hyperparameter selection (no test peek)
    cut = int(0.8 * len(tr)); tr_in, val = tr[:cut], tr[cut:]

    print("#" * 88)
    print("ESN TUNING ROBUSTNESS — does a TUNED, size-unconstrained ESN change the verdict?")
    print(f"  crisis window (GFC in test); focal n={N}; HAR-X nested by every model")
    print(f"  ESN grid: sizes={sizes} (quantum readout = {ss.feat_dim(N)}), spectral_radius={srs}, "
          f"leak={leaks}; selected on a chronological val tail")
    print("#" * 88)

    # ---- CHIMERA reference (seed-averaged), same protocol as the headline ----
    chim = np.mean([ridge_readout(np.hstack([ss.chimera_features_n(rich_s, N, (2.0,), sd), LINX])[tr],
                                  y[tr],
                                  np.hstack([ss.chimera_features_n(rich_s, N, (2.0,), sd), LINX])[te])[0]
                    for sd in chim_seeds], axis=0)
    chim_rmse = rmse(yT, chim)

    # ---- HAR-X (linear bar) and the headline size-matched, untuned ESN ----
    harx = ridge_readout(LINX[tr], y[tr], LINX[te])[0]
    harx_rmse = rmse(yT, harx)
    base_esn = np.mean([ridge_readout(np.hstack([esn_feat(rich_s, ss.feat_dim(N), 0.9, 0.5, sd), LINX])[tr],
                                      y[tr],
                                      np.hstack([esn_feat(rich_s, ss.feat_dim(N), 0.9, 0.5, sd), LINX])[te])[0]
                        for sd in esn_seeds], axis=0)
    base_esn_rmse = rmse(yT, base_esn)

    # ---- tuned ESN: select (size, sr, leak) on the validation tail, then evaluate on test ----
    best = None
    for nres in sizes:
        for sr in srs:
            for lk in leaks:
                val_errs, te_preds = [], []
                for sd in esn_seeds:
                    F = esn_feat(rich_s, nres, sr, lk, sd)
                    D = np.hstack([F, LINX])
                    # fit on tr_in, score on val (selection); also keep a full-train->test pred
                    vpred = ridge_readout(D[tr_in], y[tr_in], D[val])[0]
                    val_errs.append(rmse(y[val], vpred))
                    te_preds.append(ridge_readout(D[tr], y[tr], D[te])[0])
                vscore = float(np.mean(val_errs))
                te_rmse = rmse(yT, np.mean(te_preds, axis=0))
                if best is None or vscore < best["val"]:
                    best = dict(val=vscore, test=te_rmse, nres=nres, sr=sr, lk=lk)

    print(f"\n  {'model':<40}{'test RMSE(logRV)':>18}")
    print(f"  {'HAR-X (linear bar)':<40}{harx_rmse:>18.4f}")
    print(f"  {'CHIMERA (quantum, '+str(ss.feat_dim(N))+' feat)':<40}{chim_rmse:>18.4f}")
    print(f"  {'ESN headline (size-matched '+str(ss.feat_dim(N))+', untuned)':<40}{base_esn_rmse:>18.4f}")
    print(f"  {'ESN TUNED ('+str(best['nres'])+' nodes, sr='+str(best['sr'])+', leak='+str(best['lk'])+')':<40}{best['test']:>18.4f}")
    print("\n" + "=" * 88)
    print(f"Selected ESN config (on val tail, no test peek): {best['nres']} nodes, "
          f"spectral_radius={best['sr']}, leak={best['lk']}.")
    if best["test"] <= chim_rmse + 1e-9:
        print(f"VERDICT: the TUNED, size-unconstrained ESN ({best['test']:.4f}) ties/beats CHIMERA "
              f"({chim_rmse:.4f}) — the honest negative is STRENGTHENED, not weakened: the quantum")
        print(f"reservoir shows no edge even against a properly optimized, far larger classical reservoir.")
    else:
        print(f"VERDICT: CHIMERA ({chim_rmse:.4f}) edges even the tuned ESN ({best['test']:.4f}) — "
              f"a genuine (small) quantum edge survives ESN tuning; investigate further.")
    print(f"[{time.time()-t0:.1f}s]")
    np.save("esn_tuning_robustness_results.npy",
            dict(harx=harx_rmse, chimera=chim_rmse, esn_base=base_esn_rmse,
                 esn_tuned=best["test"], best_cfg=best), allow_pickle=True)


if __name__ == "__main__":
    main()
