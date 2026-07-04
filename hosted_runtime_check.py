"""
hosted_runtime_check.py - run the quantum core of EVERY experiment family through
qBraid's HOSTED runtime (free simulator tier) and verify it reproduces the local engine.

Answers "could we run all our code through qBraid's hosted runtime?" honestly:
  - Full-scale re-execution is neither feasible nor desirable: the studies evaluate
    the reservoir on ~10^5-10^6 inputs with EXACT analytic expectations (which the
    DM/Holm statistics rely on); hosted execution is ~30-60 s/job with shot noise
    eps ~ 1/sqrt(S). What CAN and SHOULD run hosted is the QUANTUM CORE itself.
  - This script therefore takes REAL representative inputs from each domain -
    S&P-500 RV lag windows (Track A), MNIST PCA(n) encodings (mandatory benchmark),
    hourly weather windows (Track B / V3) - runs the identical CHIMERA circuit on
    qBraid's cloud simulator, and scores the returned features against
      (a) the local analytic Trotter circuit  -> expect the SHOT FLOOR (~1/sqrt(S))
      (b) the exact NumPy engine              -> expect the Trotter-20 systematic (~0.04)
    If (a) sits at the shot floor for every domain and qubit count, the hosted
    runtime and the local engine are interchangeable - i.e. every experiment's
    quantum step is validated on qBraid's hosted stack.

Usage:  QBRAID_API_KEY=... python3 hosted_runtime_check.py            # ~15 cloud jobs, free
        QBRAID_API_KEY=... python3 hosted_runtime_check.py --quick    # ~6 jobs
"""
import argparse
import json
import os
import time
import numpy as np

from qrc_engine import generate_coupling_matrix
from qbraid_submit import engine_features, real_rv_windows
from qpu_run import base_ops, to_qasm2, probs_from_counts, features_from_probs, QbraidRunner

DEVICE = "qbraid:qbraid:sim:qir-sv"     # free hosted simulator tier
LAYERS = 20


def local_analytic(ops, n):
    """Local analytic expectations for the SAME op list (the Trotter reference)."""
    import pennylane as qml
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def circ():
        for g, wires, a in ops:
            if g == "cx":
                qml.CNOT(wires=list(wires))
            else:
                getattr(qml, {"ry": "RY", "rx": "RX", "rz": "RZ"}[g])(a, wires=wires[0])
        return [qml.expval(o) for o in
                ([qml.PauliZ(i) for i in range(n)]
                 + [qml.PauliZ(i) @ qml.PauliZ(j) for i in range(n) for j in range(i + 1, n)])]
    return np.array(circ())


def mnist_inputs(n, k):
    from mnist_benchmark import load_mnist, pca_encode
    Xtr, ytr, Xte, yte = load_mnist(400, 100)
    Ptr, Pte = pca_encode(Xtr, Xte, n)
    return Pte[:k]


def weather_inputs(n, k):
    d = np.load(os.path.join("v3_research", "jena_hourly.npz"), allow_pickle=True)
    X = d["X"].astype(float)[-4000:]
    cols = [str(c) for c in d["cols"]]
    Ti = cols.index("T (degC)")
    T = X[:, Ti]
    ex = [i for i, c in enumerate(cols) if c != "T (degC)"]
    rows = [[T[t - L] for L in (0, 1, 2, 3, 4)] + [X[t, j] for j in ex]
            for t in range(4, 4 + 50)]
    W = np.array(rows)
    lo, hi = W.min(0), W.max(0)
    W = np.clip((W - lo) / np.where(hi - lo == 0, 1, hi - lo), 0, 1)
    idx = np.linspace(0, len(W) - 1, k).astype(int)
    return W[idx, :n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=2000)   # free-tier per-job cap
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    k = 2 if args.quick else 3
    batt = ([("finance", 8, real_rv_windows(8, k=k)),
             ("finance", 10, real_rv_windows(10, k=k)),
             ("mnist", 10, mnist_inputs(10, k)),
             ("weather", 10, weather_inputs(10, k))]
            + ([] if args.quick else [("finance", 12, real_rv_windows(12, k=k)),
                                      ("mnist", 8, mnist_inputs(8, k))]))
    runner = QbraidRunner(DEVICE)
    floor = 1 / np.sqrt(args.shots)
    t0 = time.time()
    print("#" * 84)
    print(f"HOSTED-RUNTIME EQUIVALENCE - every experiment family's quantum core on {DEVICE}")
    print(f"  shots={args.shots}/circuit (shot floor ~{floor:.4f});  Trotter-{LAYERS} "
          f"systematic ~0.04;  {sum(len(w) for _, _, w in batt)} circuits")
    print("#" * 84)
    rows = []
    for domain, n, wins in batt:
        J = generate_coupling_matrix(n, 0.5, seed=0)
        eng = engine_features(n, 0)
        d_loc, d_eng = [], []
        for w in wins:
            ops = base_ops(w, n, J, LAYERS)
            counts = runner.run(to_qasm2(ops, n), args.shots)
            F_cloud = features_from_probs(probs_from_counts(counts, n), n)
            d_loc.append(np.abs(F_cloud - local_analytic(ops, n)))
            d_eng.append(np.abs(F_cloud - eng(w)))
        r = dict(domain=domain, n=n, k=len(wins),
                 vs_local_mean=float(np.mean(d_loc)), vs_local_max=float(np.max(d_loc)),
                 vs_engine_mean=float(np.mean(d_eng)), vs_engine_max=float(np.max(d_eng)))
        rows.append(r)
        print(f"  {domain:<9} n={n:<3} |cloud-local| mean={r['vs_local_mean']:.4f} "
              f"max={r['vs_local_max']:.4f}   |cloud-engine| mean={r['vs_engine_mean']:.4f} "
              f"max={r['vs_engine_max']:.4f}", flush=True)

    ok = all(r["vs_local_mean"] < 3 * floor for r in rows)
    print("\n" + "=" * 84)
    if ok:
        print(f"VERDICT: hosted-runtime features match the local circuit at the shot floor "
              f"(all means < 3x{floor:.4f}) across finance, MNIST and weather inputs - the "
              f"hosted runtime and the local engine are interchangeable; every experiment's "
              f"quantum core is validated on qBraid's hosted stack.")
    else:
        print("VERDICT: deviation above the shot floor in at least one domain (investigate).")
    out = dict(device=DEVICE, shots=args.shots, rows=rows, job_ids=runner.job_ids,
               shot_floor=floor, wall_clock_s=round(time.time() - t0, 1))
    if not args.quick:
        with open("results/hosted_runtime_check.json", "w") as f:
            json.dump(out, f, indent=1)
        print(f"saved results/hosted_runtime_check.json  ({len(runner.job_ids)} cloud jobs) "
              f"[{out['wall_clock_s']}s]")
    else:
        print(f"[--quick] not written  [{out['wall_clock_s']}s]")


if __name__ == "__main__":
    main()
