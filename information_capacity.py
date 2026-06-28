"""
information_capacity.py  [Phase-3 extension] — the reservoir-intrinsic capability test.

Does the quantum reservoir's 2^n Hilbert space buy MORE nonlinear information-processing
capacity than a matched classical reservoir, *decoupled from the (linear-dominated) RV task*?
This is the strongest remaining place a genuine quantum-RC advantage could hide. We measure it
directly with an Information-Processing-Capacity-style probe (Dambre et al. 2012):

  - iid input u_t ~ Uniform[-1,1]; delay-embed the last n values -> window X (every model gets
    the SAME X, scaled to [0,1] for fair angle-encoding / kernel input).
  - target basis = products of Legendre polynomials of the lagged inputs, grouped by total
    polynomial DEGREE (1 = linear memory, 2/3 = nonlinear memory).
  - capacity for a target = out-of-sample R^2 of a ridge readout on the reservoir features
    (clipped to [0,1]); capacity by degree = sum over that degree's basis.

Compared at MATCHED feature count: CHIMERA (Pauli-Z features) vs RFF (random-Fourier RBF) vs a
recurrent ESN. Averaged over seeds. Honest by construction: we report whatever it shows.

(An earlier one-off probe found CHIMERA *lower*; this formalizes it with multiple seeds and a
graded Legendre basis. If confirmed, it DEEPENS the negative — the quantum reservoir is not even
more expressive at matched scale, which is *why* a linear model wins on RV.)

Usage:  python3 information_capacity.py            # n=10, 3 seeds
        python3 information_capacity.py --quick    # n=8, 2 seeds, shorter series
"""
import argparse
import time
import numpy as np

import scaling_sweep as ss
from axisB_rigorous import rff_features, rbf_gamma, esn_recurrent_features
from vol_fair_benchmark import ridge_readout


def _legendre(x, d):
    if d == 1: return x
    if d == 2: return 0.5 * (3 * x ** 2 - 1)
    if d == 3: return 0.5 * (5 * x ** 3 - 3 * x)
    raise ValueError(d)


def build_targets(X, n):
    """Graded polynomial target basis on the centered lags c = 2*(u-0.5) in [-1,1].
    Returns dict degree -> list of (name, y)."""
    c = 2.0 * (X - 0.5)
    tg = {1: [], 2: [], 3: []}
    for k in range(min(n, 8)):                              # degree-1: linear memory over lags
        tg[1].append((f"u{k+1}", c[:, k]))
    deg2 = [(0, 1), (0, 2), (1, 3), (2, 5), (0, 4)]         # cross products (degree 2)
    for i, j in deg2:
        if i < n and j < n:
            tg[2].append((f"u{i+1}u{j+1}", c[:, i] * c[:, j]))
    for k in (1, 3, 5):                                     # squares P2 (degree 2)
        if k < n:
            tg[2].append((f"P2(u{k+1})", _legendre(c[:, k], 2)))
    deg3 = [(0, 1, 2), (0, 2, 4)]                           # triple products (degree 3)
    for i, j, l in deg3:
        if l < n:
            tg[3].append((f"u{i+1}u{j+1}u{l+1}", c[:, i] * c[:, j] * c[:, l]))
    for k in (1, 3):                                        # P3 (degree 3)
        if k < n:
            tg[3].append((f"P3(u{k+1})", _legendre(c[:, k], 3)))
    return tg


def _r2(y, p):
    return 1.0 - np.sum((y - p) ** 2) / (np.sum((y - y.mean()) ** 2) + 1e-12)


def run_trial(n, T, seed):
    rng = np.random.RandomState(seed)
    u = rng.uniform(0.0, 1.0, T)
    X = np.array([u[t - n:t][::-1] for t in range(n, T)])    # X[:,0]=u_{t-1}, ...
    m = len(X); tr = np.arange(int(0.7 * m)); te = np.arange(int(0.7 * m), m)
    nf = ss.feat_dim(n)
    feats = {
        "CHIMERA": ss.chimera_features_n(X, n, (2.0,), seed),
        "RFF": rff_features(X, nf, seed, rbf_gamma(X[tr])),
        "ESN": esn_recurrent_features(X, nf, seed),
    }
    tg = build_targets(X, n)
    cap = {k: {1: 0.0, 2: 0.0, 3: 0.0} for k in feats}
    for deg, items in tg.items():
        for _, y in items:
            for k, F in feats.items():
                p, _ = ridge_readout(F[tr], y[tr], F[te])
                cap[k][deg] += max(0.0, _r2(y[te], p))
    return cap, {d: len(v) for d, v in tg.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n = 8 if args.quick else 10
    T = 1500 if args.quick else 3000
    seeds = (0, 1) if args.quick else (0, 1, 2)
    t0 = time.time()

    print("#" * 84)
    print("INFORMATION-PROCESSING CAPACITY (reservoir-intrinsic) — CHIMERA vs matched RFF/ESN")
    print(f"  n={n}, T={T}, seeds={seeds}, matched feat={ss.feat_dim(n)}; capacity = Σ test R^2")
    print("#" * 84)

    agg = {k: {1: [], 2: [], 3: []} for k in ("CHIMERA", "RFF", "ESN")}
    counts = None
    for s in seeds:
        cap, counts = run_trial(n, T, s)
        for k in agg:
            for d in (1, 2, 3):
                agg[k][d].append(cap[k][d])

    print(f"\n  basis sizes: degree1={counts[1]}  degree2={counts[2]}  degree3={counts[3]}")
    print(f"\n  {'model':<9}{'linear(d1)':>12}{'nonlin(d2)':>12}{'nonlin(d3)':>12}"
          f"{'NONLIN tot':>12}{'TOTAL':>10}")
    summary = {}
    for k in ("CHIMERA", "RFF", "ESN"):
        d1 = np.mean(agg[k][1]); d2 = np.mean(agg[k][2]); d3 = np.mean(agg[k][3])
        nl = d2 + d3; tot = d1 + nl
        summary[k] = dict(d1=d1, d2=d2, d3=d3, nonlinear=nl, total=tot,
                          d1_sd=float(np.std(agg[k][1])), nl_sd=float(np.std(np.array(agg[k][2])+np.array(agg[k][3]))))
        print(f"  {k:<9}{d1:>12.3f}{d2:>12.3f}{d3:>12.3f}{nl:>12.3f}{tot:>10.3f}")

    best_nl = max(summary, key=lambda k: summary[k]["nonlinear"])
    q = summary["CHIMERA"]["nonlinear"]
    best_cl = max(("RFF", "ESN"), key=lambda k: summary[k]["nonlinear"])
    print("\n" + "=" * 84)
    if best_nl == "CHIMERA" and q > summary[best_cl]["nonlinear"] + summary[best_cl]["nl_sd"]:
        print("VERDICT: CHIMERA has the HIGHEST nonlinear capacity — a genuine quantum-RC capability")
        print("  advantage at matched scale. Investigate (this would be striking).")
    else:
        print(f"VERDICT: CHIMERA does NOT have higher nonlinear capacity (best = {best_nl}; "
              f"CHIMERA {q:.2f} vs {best_cl} {summary[best_cl]['nonlinear']:.2f}).")
        print("  Even decoupled from the financial task, the quantum reservoir is not more")
        print("  nonlinearly expressive at matched feature count — this DEEPENS the honest negative")
        print("  and explains why a linear model wins on (linear-dominated) realized volatility.")
    if not args.quick:
        np.save("information_capacity_results.npy",
                dict(summary=summary, n=n, T=T, seeds=list(seeds), counts=counts), allow_pickle=True)
        print(f"\nsaved information_capacity_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
