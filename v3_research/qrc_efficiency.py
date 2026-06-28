"""
qrc_efficiency.py  [V3 — the resource-efficiency question: small QRC vs larger classical?]

"Not more accurate than a SIZE-MATCHED classical reservoir" matched the *readout dimension*. The
sharper question: can a SMALL quantum reservoir match a LARGER classical one — i.e., is the quantum
feature map more efficient *per feature*? We trace the quality-vs-size frontier: forecast quality
(test RMSE) as a function of #reservoir features, for CHIMERA (qubit count n -> d = n + n(n-1)/2) vs
RFF and ESN (node count).

FAIRNESS (the part that matters): the INPUT INFORMATION is held FIXED across every n. We fix a small
pool of informed inputs and DATA-RE-UPLOAD it onto n qubits (feature_pool.encode '..reupload..'), so
only the reservoir SIZE changes, never the information it sees. (Without this, a smaller n would
literally see fewer input columns — an apples-to-oranges confound.) The fair classical counterpart of
the static CHIMERA map is RFF (also a static nonlinear map of the same fixed input); the ESN is
RECURRENT (extra internal memory) so it is reported as context, not as the matched control.

Reservoir-features-only ridge (no linear block) so the curve reflects the reservoir's own efficiency.
Task: Jena hourly T, 1h ahead, AR pool = 5 recent T lags (fixed for all n).

Usage:  python3 qrc_efficiency.py            # n=5..10, 5 seeds
        python3 qrc_efficiency.py --quick    # n=5..8, 2 seeds
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import scaling_sweep as ss
import feature_pool as fp
from vol_fair_benchmark import ridge_readout
from axisB_rigorous import esn_recurrent_features, rff_features, rbf_gamma

HERE = os.path.dirname(os.path.abspath(__file__))
POOL_LAGS = (0, 1, 2, 3, 4)          # 5 recent hourly T lags -> the FIXED input pool (P=5)


def rmse(a, b): return float(np.sqrt(np.mean((a - b) ** 2)))


def build(span, h=1, data="jena_hourly.npz"):
    d = np.load(os.path.join(HERE, data), allow_pickle=True)
    X = d["X"].astype(float); cols = [str(c) for c in d["cols"]]
    X = X[-span:]
    T = X[:, cols.index("T (degC)")]
    rows, y = [], []
    ml = max(POOL_LAGS)
    for t in range(ml, len(X) - h):
        rows.append([T[t - L] for L in POOL_LAGS])     # 5-dim fixed pool
        y.append(T[t + h])
    return np.array(rows), np.array(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--data", default="jena_hourly.npz")
    args = ap.parse_args()
    seeds = (0, 1) if args.quick else (0, 1, 2, 3, 4)
    span = 8000 if args.quick else 16000
    ns = [5, 6, 7, 8] if args.quick else [5, 6, 7, 8, 9, 10]
    t0 = time.time()

    Xin, y = build(span, 1, args.data)
    m = len(y); ntr = int(0.7 * m); tr = np.arange(ntr); te = np.arange(ntr, m)
    yT = y[te]
    pool = fp.scale_pool(Xin, tr) if hasattr(fp, "scale_pool") else None
    if pool is None:                                    # local [0,1] scaling on train (fallback)
        lo, hi = Xin[tr].min(0), Xin[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
        pool = np.clip((Xin - lo) / rng, 0, 1)
    gamma = rbf_gamma(pool[tr])

    qdims = [n + n * (n - 1) // 2 for n in ns]
    cdims = sorted(set(qdims + ([20, 40, 80] if args.quick else [20, 40, 80, 160, 320, 640])))

    def feat_rmse(F):
        pr, _ = ridge_readout(F[tr], y[tr], F[te]); return rmse(yT, pr)

    print("#" * 84)
    print(f"V3 QRC EFFICIENCY FRONTIER — quality vs #features, FIXED input (5 T-lags, reuploaded)")
    print(f"  Jena T+1h  span={span} test={len(te)} seeds={seeds}; CHIMERA n={ns} -> d={qdims}")
    print("#" * 84)

    chi = {}
    for n, d in zip(ns, qdims):
        Qn = fp.encode(pool, n, "reupload")             # fixed 5-feature info -> n qubits
        rs = [feat_rmse(ss.chimera_features_n(Qn, n, (2.0,), sd)) for sd in seeds]
        chi[d] = float(np.mean(rs))
        print(f"  CHIMERA  n={n:>2}  d={d:>3}   RMSE={chi[d]:.4f}", flush=True)
    esn = {}; rff = {}
    for d in cdims:
        esn[d] = float(np.mean([feat_rmse(esn_recurrent_features(pool, d, sd)) for sd in seeds]))
        rff[d] = float(np.mean([feat_rmse(rff_features(pool, d, sd, gamma)) for sd in seeds]))
        print(f"  classical d={d:>3}   RFF(static)={rff[d]:.4f}   ESN(recurrent)={esn[d]:.4f}", flush=True)

    def match_size(curve, target):
        for dd in sorted(curve):
            if curve[dd] <= target:
                return dd
        return None

    print("\n" + "=" * 84)
    print("Exchange rate vs the FAIR static control (RFF): features needed to match each CHIMERA point")
    rff_more = 0; rff_le = 0
    for n, d in zip(ns, qdims):
        mr = match_size(rff, chi[d])
        if mr is None:
            tag = "RFF never matches it within the swept range (CHIMERA more efficient)"; rff_more += 1
        else:
            rel = "<" if mr < d else "=" if mr == d else ">"
            tag = f"RFF needs d'={mr} ({rel}{d})"
            rff_more += (mr > d); rff_le += (mr <= d)
        print(f"  CHIMERA n={n} (d={d}, RMSE {chi[d]:.4f}):  {tag}")
    print()
    if rff_more > rff_le:
        print("VERDICT: a SMALLER CHIMERA matches a LARGER RFF on most points — the quantum feature "
              "map shows a per-feature efficiency EDGE over the matched static classical map.")
    else:
        print("VERDICT: RFF matches each CHIMERA point at EQUAL or FEWER features — no per-feature "
              "efficiency advantage for the quantum map (consistent with the IPC finding).")
    bestc = min(chi.values()); bestrff = min(rff.values()); beste = min(esn.values())
    print(f"NOTE (absolute best across sizes): CHIMERA {bestc:.3f} | RFF {bestrff:.3f} (static) | "
          f"ESN {beste:.3f} (recurrent — extra memory, not a static-map control).")
    if not args.quick:
        np.save(os.path.join(HERE, "qrc_efficiency_results.npy"),
                dict(chi=chi, esn=esn, rff=rff, ns=ns, qdims=qdims, cdims=cdims, span=span),
                allow_pickle=True)
        print(f"saved qrc_efficiency_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
