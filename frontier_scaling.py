"""
frontier_scaling.py  [Phase-3 extension] — does classical-IRREPRODUCIBILITY keep growing to the
n=16 sparse frontier under FULLY-INFORMED encoding?

The original `scaling_sweep` H0 curve used the FIXED univariate 8-lag encoder, so for n>8 the
extra qubits are idle and g(n) declines (the input bottleneck). Axis B fixed that at n≤12. Here
we push the *informed* encoding to the **n=16 sparse-statevector frontier** and ask the one
honest, striking question still open at simulable scale:

  Under fully-informed encoding (the first n columns of the rich realized-measure pool — P=19
  features, so NO idle qubits up to n=16), does the geometric difference g(ESN_n || CHIMERA_n)
  — i.e. how badly a matched classical reservoir fails to reproduce the quantum kernel — keep
  GROWING with n, or saturate?

This is explicitly a statement about CLASSICAL IRREPRODUCIBILITY (a *necessary, not sufficient*
precondition for any beyond-frontier advantage), NOT a forecasting-advantage claim. A growing,
diverging-from-control curve is the strongest honest evidence that the regime where the quantum
map becomes hard to replicate opens up with scale; a saturating curve is another honest negative.

Same g machinery as `scaling_sweep` (Huang et al. 2021 geometric difference) and the matched ESN
reference; dense engine for n≤12, exact sparse backend (expm_multiply) for n=14,16.

Usage:  python3 frontier_scaling.py            # n=8,10,12,14,16
        python3 frontier_scaling.py --quick    # n=8,10,12 (dense only), smaller subsample
"""
import argparse
import time
import numpy as np

import feature_pool as fp
import scaling_sweep as ss
import volatility_data as vd
from vol_fair_benchmark import esn_features
from tensor_backend import chimera_features_sparse


def _spearman(x, y):
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    rx = rx - rx.mean(); ry = ry - ry.mean()
    return float((rx @ ry) / (np.sqrt((rx**2).sum() * (ry**2).sum()) + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    ns = [8, 10, 12] if args.quick else [8, 10, 12, 14, 16]
    sub = 200 if args.quick else 400
    t0 = time.time()

    d = fp.build_rich()
    pool, y = d["pool"], d["y_logrv"]
    tr, te = vd.make_splits(len(y), 0.70)
    pool_s = fp.scale_pool(pool, tr)
    idx = np.linspace(0, len(tr) - 1, min(sub, len(tr))).astype(int)
    trk = np.array(tr)[idx]
    yc = y[trk] - y[trk].mean()

    print("#" * 88)
    print("FRONTIER SCALING: classical-irreproducibility g(n) under FULLY-INFORMED encoding")
    print(f"  ns={ns}  kernel N_sub={len(trk)}  pool P={pool.shape[1]} (>= n, so no idle qubits)")
    print(f"  dense engine n<=12; exact sparse (expm_multiply) n>=14")
    print("#" * 88)
    print(f"\n{'n':>3}{'#feat':>7}{'g(ESN||CHIM)':>14}{'g_control':>11}{'g/ctrl':>8}"
          f"{'D_eff':>8}{'rank':>6}{'KTA':>9}{'sec':>8}", flush=True)

    rows = []
    for n in ns:
        tn = time.time()
        Qn = pool_s[:, :n]                         # fully-informed: first n informative pool cols
        if n <= 12:
            FQ = ss.chimera_features_n(Qn[trk], n, (2.0,), 0)
        else:
            FQ = chimera_features_sparse(Qn[trk], n, 2.0, 0)
        nr = ss.feat_dim(n)
        Fe = esn_features(Qn[trk], nr, 0)
        Feb = esn_features(Qn[trk], nr, 1)
        KQ, Ke, Keb = ss.lin_kernel(FQ), ss.lin_kernel(Fe), ss.lin_kernel(Feb)
        g_q = ss.geom_diff(Ke, KQ)
        g_c = ss.geom_diff(Ke, Keb)
        de, rk, kt = ss.eff_dim(KQ), ss.num_rank(KQ), ss.kta(KQ, yc)
        dt = time.time() - tn
        rows.append(dict(n=n, n_feat=int(FQ.shape[1]), g_quantum=g_q, g_control=g_c,
                         ratio=g_q / max(g_c, 1e-9), d_eff=de, rank=rk, kta=kt, sec=dt))
        print(f"{n:>3}{FQ.shape[1]:>7}{g_q:>14.2f}{g_c:>11.2f}{g_q/max(g_c,1e-9):>8.1f}"
              f"{de:>8.2f}{rk:>6}{kt:>9.4f}{dt:>8.1f}", flush=True)

    nsv = [r["n"] for r in rows]
    gq = [r["g_quantum"] for r in rows]
    ratio = [r["ratio"] for r in rows]
    rho_g = _spearman(nsv, gq); rho_r = _spearman(nsv, ratio)
    print("\n" + "=" * 88)
    print(f"Spearman rho(n, g_quantum)   = {rho_g:+.2f}")
    print(f"Spearman rho(n, g/control)   = {rho_r:+.2f}")
    grows = rho_g > 0.5 and gq[-1] > gq[0]
    if grows and rho_r > 0.5:
        print("VERDICT: under fully-informed encoding, classical-irreproducibility g GROWS to the")
        print("  n=16 frontier AND diverges from the classical control — the strongest HONEST")
        print("  evidence that the hard-to-replicate regime opens with scale (necessary, NOT")
        print("  sufficient, for beyond-frontier advantage; no advantage is claimed here).")
    elif grows:
        print("VERDICT: g grows with n but does not clearly diverge from the control — partial.")
    else:
        print("VERDICT: g SATURATES/declines even under fully-informed encoding — honest negative;")
        print("  classical-irreproducibility does not widen with scale in the testable range.")
    if not args.quick:
        np.save("frontier_scaling_results.npy",
                dict(rows=rows, rho_g=rho_g, rho_ratio=rho_r), allow_pickle=True)
        print(f"\nsaved frontier_scaling_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
