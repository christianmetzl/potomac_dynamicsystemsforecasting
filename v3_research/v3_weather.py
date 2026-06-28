"""
v3_weather.py  [V3 — EXPLORATORY, NOT part of the V1 submission]

Track B (weather) — apply the SAME CHIMERA engine and the SAME adversarial protocol as Track A to
hourly temperature forecasting (Jena climate). Honest by construction; no V1 file touched.

Task: forecast T (deg C) h hours ahead from a 10-dim informed window = [5 recent hourly T lags +
current p, rh, VPmax, wv, Tdew] (so all 10 qubits carry information, Axis-B style). Horizons h=1
(next hour) and h=24 (next day, the standard Keras-tutorial task).

Models (all share the SAME information; CHIMERA/ESN/RFF NEST the linear block, so a quantum win
needs nonlinearity beyond the linear span — identical discipline to Track A's HAR-X):
  Persistence : T_{t+h} = T_t                              (naive bar)
  Linear      : ridge on [the 10-d window + extra T lags]  (strong linear bar = "AR-X")
  ESN         : recurrent echo-state features + linear      (classical nonlinear)
  RFF         : random-Fourier RBF features + linear        (classical kernel)
  CHIMERA     : quantum reservoir features + linear         (quantum nonlinear)

Metrics: RMSE / MAE (deg C), skill vs persistence; Diebold-Mariano with Newey-West HAC (hourly
errors are serially correlated; lag >= h) comparing CHIMERA to the best classical model.

Usage:  python3 v3_weather.py            # h=1 and h=24, 5 seeds
        python3 v3_weather.py --quick    # h=1, 3 seeds, smaller span
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import scaling_sweep as ss
from vol_fair_benchmark import ridge_readout
from axisB_rigorous import dm_hac, esn_recurrent_features, rff_features, rbf_gamma

HERE = os.path.dirname(os.path.abspath(__file__))
N_FOCAL = 10
T_LAGS = (0, 1, 2, 3, 4)            # recent hourly temperature lags (5) -> 5 of the 10 qubits


def rmse(a, b): return float(np.sqrt(np.mean((a - b) ** 2)))
def mae(a, b): return float(np.mean(np.abs(a - b)))


def build(h, span, data="jena_hourly.npz"):
    d = np.load(os.path.join(HERE, data), allow_pickle=True)
    X = d["X"].astype(float); cols = [str(c) for c in d["cols"]]
    if span and len(X) > span:
        X = X[-span:]                                   # most-recent contiguous span (tractable)
    Ti = cols.index("T (degC)")
    T = X[:, Ti]
    exog_idx = [i for i, c in enumerate(cols) if c != "T (degC)"]
    P = len(X)
    # informed 10-d input: [T_t, T_{t-1}.. T_{t-4}, current exog(5)]; target T_{t+h}
    rows, y, extra = [], [], []
    maxlag = max(T_LAGS)
    for t in range(maxlag, P - h):
        win = [T[t - L] for L in T_LAGS] + [X[t, j] for j in exog_idx]   # 10 informed values
        rows.append(win)
        extra.append([T[t - L] for L in (5, 8, 12, 24) if t - L >= 0] or [T[t]])  # extra T lags
        y.append(T[t + h])
    Xin = np.array(rows); y = np.array(y)
    # pad extra lags to fixed width 4 (older rows may miss long lags -> use T_t)
    EX = np.array([(e + [e[-1]] * 4)[:4] for e in extra])
    LIN = np.hstack([Xin, EX])                          # linear block ("AR-X": window + extra lags)
    persist = Xin[:, 0]                                 # T_t  (persistence forecast of T_{t+h})
    return Xin, LIN, y, persist


def run(h, span, seeds, data="jena_hourly.npz"):
    Xin, LIN, y, persist = build(h, span, data)
    m = len(y); ntr = int(0.7 * m); tr = np.arange(ntr); te = np.arange(ntr, m)
    yT = y[te]
    lo, hi = Xin[tr].min(0), Xin[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Xs = np.clip((Xin - lo) / rng, 0, 1)               # [0,1] for encoders, train-only scaling
    lag = max(h, 24)                                    # HAC lag for hourly autocorrelation

    out = {}
    out["Persistence"] = dict(rmse=rmse(yT, persist[te]), mae=mae(yT, persist[te]), pred=persist[te])
    lin, _ = ridge_readout(LIN[tr], y[tr], LIN[te])
    out["Linear"] = dict(rmse=rmse(yT, lin), mae=mae(yT, lin), pred=lin)
    gamma = rbf_gamma(Xs[tr])
    per = {"ESN": [], "RFF": [], "CHIMERA": []}
    for sd in seeds:
        for nm, F in (("CHIMERA", ss.chimera_features_n(Xs, N_FOCAL, (2.0,), sd)),
                      ("ESN", esn_recurrent_features(Xs, ss.feat_dim(N_FOCAL), sd)),
                      ("RFF", rff_features(Xs, ss.feat_dim(N_FOCAL), sd, gamma))):
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y[tr], D[te])
            per[nm].append(pr)
    for nm in ("ESN", "RFF", "CHIMERA"):
        ens = np.mean(per[nm], axis=0)
        out[nm] = dict(rmse=rmse(yT, ens), mae=mae(yT, ens), pred=ens,
                       sd=float(np.std([rmse(yT, p) for p in per[nm]])))
    # best CLASSICAL nonlinear (ESN/RFF/Linear) for the decisive comparison
    classical = {k: out[k] for k in ("Linear", "ESN", "RFF")}
    best = min(classical, key=lambda k: classical[k]["rmse"])
    ch = out["CHIMERA"]
    ds, p = dm_hac((ch["pred"] - yT) ** 2, (out[best]["pred"] - yT) ** 2, lag=lag)
    pe = out["Persistence"]["rmse"]
    print(f"\n=== h={h}h  (test {len(te)} hrs; persistence RMSE={pe:.3f} degC) ===")
    print(f"  {'model':<12}{'RMSE(degC)':>11}{'MAE':>8}{'skill%':>8}")
    for nm in ("Persistence", "Linear", "ESN", "RFF", "CHIMERA"):
        sk = 100 * (1 - out[nm]["rmse"] / pe)
        print(f"  {nm:<12}{out[nm]['rmse']:>11.3f}{out[nm]['mae']:>8.3f}{sk:>8.1f}")
    print(f"  -> best classical = {best} (RMSE {out[best]['rmse']:.3f}); "
          f"CHIMERA vs it: DM(HAC)={ds:+.2f} p={p:.3f}  "
          f"{'(CHIMERA better)' if ds < 0 and p < 0.05 else '(n.s.)' if p>=0.05 else '(CHIMERA worse)'}")
    return dict(h=h, best=best, dm=ds, p=p,
                rows={k: {kk: vv for kk, vv in v.items() if kk != 'pred'} for k, v in out.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--data", default="jena_hourly.npz",
                    help="panel npz (jena_hourly.npz or noaa_hourly.npz)")
    args = ap.parse_args()
    seeds = (0, 1, 2) if args.quick else (0, 1, 2, 3, 4)
    span = 12000 if args.quick else 26000      # ~1.4y / ~3y of hourly data (tractable)
    horizons = [1] if args.quick else [1, 24]
    t0 = time.time()
    stem = os.path.basename(args.data).replace("_hourly.npz", "").replace(".npz", "")
    LABELS = {"jena": "Jena (MPI)", "noaa": "NOAA Chicago O'Hare", "denver": "NOAA Denver Intl",
              "great_falls": "NOAA Great Falls MT", "rapid_city": "NOAA Rapid City SD",
              "cheyenne": "NOAA Cheyenne WY"}
    src = LABELS.get(stem, stem)
    print("#" * 84)
    print(f"V3 TRACK-B (weather): hourly temperature forecast — CHIMERA vs classical controls")
    print(f"  source={src} [{args.data}]  span={span} hrs  seeds={seeds}  horizons={horizons}")
    print("#" * 84)
    res = [run(h, span, seeds, args.data) for h in horizons]
    print("\n" + "=" * 84)
    wins = [r for r in res if r["dm"] < 0 and r["p"] < 0.05]
    if wins:
        print(f"VERDICT: CHIMERA significantly beats the best classical at horizons "
              f"{[r['h'] for r in wins]} — investigate (would be the first such result).")
    else:
        print("VERDICT: no horizon shows a significant CHIMERA advantage over the best classical "
              "model. Honest negative persists in Track B (weather) too — but see per-horizon signs/skill.")
    if not args.quick:
        # source-keyed filename so different stations/datasets don't clobber each other
        fn = "v3_weather_results.npy" if stem == "jena" else f"v3_weather_results_{stem}.npy"
        np.save(os.path.join(HERE, fn), dict(res=res, span=span, data=args.data, src=src),
                allow_pickle=True)
        print(f"saved {fn}  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
