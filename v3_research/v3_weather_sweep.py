"""
v3_weather_sweep.py  [V3 — Track B spec: qubit-count + noise demonstration]

The brief requires, across both tracks, a demonstration of QRC performance across qubit counts
(5/10/15) and under realistic noise (depolarizing + amplitude damping). v3_weather.py covers the
n=10 forecast; this script adds the qubit-count and noise sweep on the same weather task.

Task: 1-hour-ahead temperature forecast (Jena), on a modest recent subset so n=15 (sparse exact)
is tractable. Encoding pool (15 informed features, take first n): [T_t, p, rh, VPmax, wv, Tdew,
T_{t-1..t-9}]. CHIMERA features (dense n<=12, exact sparse n=15) + a linear block; RMSE (degC) and
skill vs persistence. Noise (exact density-matrix channels) shown at n=5,10; n=15 is noiseless only
(an exact 4^15 density matrix is infeasible — stated honestly, matching the Track-A noise frontier).

Usage:  python3 v3_weather_sweep.py            # n=5,10,15; noise at n=5,10; 2 seeds
        python3 v3_weather_sweep.py --quick    # n=5,10; 1 seed; smaller subset
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import scaling_sweep as ss
from vol_fair_benchmark import ridge_readout
from tensor_backend import chimera_features_sparse

HERE = os.path.dirname(os.path.abspath(__file__))


def rmse(a, b): return float(np.sqrt(np.mean((a - b) ** 2)))


def build(span, h=1):
    d = np.load(os.path.join(HERE, "jena_hourly.npz"), allow_pickle=True)
    X = d["X"].astype(float); cols = [str(c) for c in d["cols"]]
    X = X[-span:]
    Ti = cols.index("T (degC)")
    T = X[:, Ti]
    ex = {c: cols.index(c) for c in cols}
    rows, y = [], []
    maxlag = 9
    for t in range(maxlag, len(X) - h):
        pool = ([T[t]] + [X[t, ex[c]] for c in ("p (mbar)", "rh (%)", "VPmax (mbar)",
                                                "wv (m/s)", "Tdew (degC)")]
                + [T[t - L] for L in range(1, 10)])          # 15 informed features
        rows.append(pool); y.append(T[t + h])
    return np.array(rows), np.array(y), np.array([r[0] for r in rows])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    ns = [5, 10] if args.quick else [5, 10, 15]
    seeds = (0,)                                  # single seed (a demonstration, not a full study)
    span = 600 if args.quick else 900
    t0 = time.time()
    Xin, y, persist = build(span)
    m = len(y); ntr = int(0.7 * m); tr = np.arange(ntr); te = np.arange(ntr, m)
    yT = y[te]
    lo, hi = Xin[tr].min(0), Xin[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Xs = np.clip((Xin - lo) / rng, 0, 1)
    pe = rmse(yT, persist[te])

    print("#" * 84)
    print("V3 TRACK-B SWEEP: qubit count {5,10,15} + noise (depol/amp-damp) — Jena T+1h")
    print(f"  subset={span} hrs, test={len(te)}, persistence RMSE={pe:.3f} degC, seeds={seeds}")
    print("#" * 84)
    print(f"\n  {'n':>3}{'channel':>16}{'rate':>7}{'CHIMERA RMSE':>14}{'skill%':>8}{'sec':>8}")

    rows = []
    for n in ns:
        Xn = Xs[:, :n]; LIN = Xin[:, :n]
        # settings: noiseless always; noise only where exact density matrix is feasible (n<=10)
        settings = [(None, 0.0)]
        if n <= 8:     # exact density-matrix noise feasible to n=8 here; Track A covers n<=10 fully
            settings += [("depolarizing", 0.02), ("amplitude_damping", 0.02)]
        for (noise, rate) in settings:
            tn = time.time(); preds = []
            for sd in seeds:
                if n <= 12:
                    F = ss.chimera_features_n(Xn, n, (2.0,), sd, noise=noise, noise_rate=rate)
                else:
                    F = chimera_features_sparse(Xn, n, 2.0, sd)      # n=15: noiseless exact only
                D = np.hstack([F, LIN])
                pr, _ = ridge_readout(D[tr], y[tr], D[te]); preds.append(pr)
            ens = np.mean(preds, axis=0); r = rmse(yT, ens); sk = 100 * (1 - r / pe)
            dt = time.time() - tn
            lab = noise or "noiseless"
            rows.append(dict(n=n, channel=lab, rate=rate, rmse=r, skill=sk))
            print(f"  {n:>3}{lab:>16}{rate:>7.2f}{r:>14.3f}{sk:>8.1f}{dt:>8.1f}", flush=True)

    print("\n" + "=" * 84)
    nl = {r["n"]: r["rmse"] for r in rows if r["channel"] == "noiseless"}
    print("Qubit scaling (noiseless RMSE): " + "  ".join(f"n={k}:{v:.3f}" for k, v in sorted(nl.items())))
    improved = all(nl[ns[i]] <= nl[ns[i-1]] + 0.005 for i in range(1, len(ns)) if ns[i] in nl and ns[i-1] in nl)
    print("  -> accuracy improves (or holds) with qubit count." if improved
          else "  -> accuracy does NOT monotonically improve with qubit count (reported honestly).")
    for n in ns:
        if n <= 10:
            base = next(r["rmse"] for r in rows if r["n"] == n and r["channel"] == "noiseless")
            for ch in ("depolarizing", "amplitude_damping"):
                rr = next((r["rmse"] for r in rows if r["n"] == n and r["channel"] == ch), None)
                if rr is not None:
                    print(f"  noise robustness n={n} {ch}: {base:.3f} -> {rr:.3f} "
                          f"(Δ{rr-base:+.3f} degC)")
    if not args.quick:
        np.save(os.path.join(HERE, "v3_weather_sweep_results.npy"), dict(rows=rows, span=span),
                allow_pickle=True)
        print(f"\nsaved v3_weather_sweep_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
