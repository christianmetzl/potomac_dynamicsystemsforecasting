"""
arima_weather.py  [V3 — Track B spec baseline: ARIMA]

The Track-B brief lists ARIMA (classical Box-Jenkins) as a recommended baseline. v3_weather.py
uses persistence + ESN + a linear AR-X stand-in; this adds a proper ARIMA one-step-ahead baseline
on the SAME Jena hourly temperature data/split, so the named baseline is actually run.

We report ARIMA(p,d,q) one-step-ahead (h=1) test RMSE/MAE alongside persistence (the trivial bar
the brief notes is "surprisingly hard to beat at very short horizons"). h>1 multi-step ARIMA needs
seasonal SARIMA (24-h cycle) and is noted as the natural extension; our Linear AR-X already serves
as the linear/ARIMA-family multi-step bar in v3_weather.py.

Usage:  python3 arima_weather.py            # ARIMA(3,0,2), full test
        python3 arima_weather.py --quick    # smaller train for speed
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--order", type=int, nargs=3, default=[3, 0, 2])
    args = ap.parse_args()
    t0 = time.time()
    from statsmodels.tsa.arima.model import ARIMA

    d = np.load(os.path.join(HERE, "jena_hourly.npz"), allow_pickle=True)
    cols = [str(c) for c in d["cols"]]
    T = d["X"][:, cols.index("T (degC)")].astype(float)
    span = 26000
    T = T[-span:]
    ntr = int(0.7 * len(T))
    # fit on a recent train tail (fast, ample for short-memory ARIMA); evaluate one-step on test
    tr_tail = T[max(0, ntr - (3000 if args.quick else 6000)):ntr]
    yte = T[ntr:]
    persist = T[ntr - 1:len(T) - 1]                       # T_t as forecast of T_{t+1}

    res = ARIMA(tr_tail, order=tuple(args.order)).fit()
    # re-anchor fitted params to the test series -> one-step-ahead predictions using TRUE lags
    res2 = res.apply(yte)
    pred = np.asarray(res2.get_prediction(dynamic=False).predicted_mean)
    # first few points are warm-up; align and drop the initial transient
    k = max(args.order)
    a, p, q = yte[k:], pred[k:], persist[k:]
    rmse = lambda x, y: float(np.sqrt(np.mean((x - y) ** 2)))
    mae = lambda x, y: float(np.mean(np.abs(x - y)))
    r_ar, r_pe = rmse(a, p), rmse(a, q)

    print("#" * 80)
    print(f"V3 TRACK-B ARIMA{tuple(args.order)} one-step (h=1) — Jena hourly temperature")
    print(f"  train tail={len(tr_tail)}, test={len(a)}")
    print("#" * 80)
    print(f"  {'model':<14}{'RMSE(degC)':>11}{'MAE':>8}{'skill% vs persist':>19}")
    print(f"  {'Persistence':<14}{r_pe:>11.3f}{mae(a,q):>8.3f}{0.0:>19.1f}")
    print(f"  {'ARIMA'+str(tuple(args.order)):<14}{r_ar:>11.3f}{mae(a,p):>8.3f}{100*(1-r_ar/r_pe):>19.1f}")
    print(f"\n(For reference, v3_weather.py h=1: ESN 0.714, CHIMERA 0.725 degC on a larger span.)")
    if not args.quick:
        np.save(os.path.join(HERE, "arima_weather_results.npy"),
                dict(order=tuple(args.order), rmse_arima=r_ar, rmse_persist=r_pe,
                     mae_arima=mae(a, p)), allow_pickle=True)
        print(f"saved arima_weather_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
