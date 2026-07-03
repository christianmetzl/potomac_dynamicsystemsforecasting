"""
mnist_benchmark.py - the challenge's COMMON cross-team benchmark.

The Phase-3 brief requires every team to "implement a common MNIST digit
classification benchmark using their QRC architecture, providing a standardized
comparison across teams and validating that the quantum reservoir exhibits
sufficient expressivity," and to "demonstrate how their QRC performs across
different qubit counts (e.g., 5, 10, 15 qubits) and under realistic noise models,
including depolarizing channels and amplitude damping."

This module does exactly that with the SAME CHIMERA-QRC engine used for the
financial track (so the cross-team comparison reflects our actual architecture,
not a bespoke image model):

  pixels (28x28) --PCA(n)--> [0,1] --RY(pi*x) on n qubits--> U=exp(-iH tau) Ising
  --> <Z_i>, <Z_iZ_j> features --> linear (ridge) multiclass readout --> digit.

Because each image is a single static input, this uses the recurrence-free
reservoir step (encode -> evolve -> measure), the standard QRC-for-images setup.
Input richness scales WITH the qubit count here (n PCA components -> n qubits), so
- unlike the univariate financial encoder - more qubits genuinely carry more image
information; we therefore expect accuracy to grow with n (a clean expressivity test).

Fair controls (rubric: "beating ESN is what justifies QRC"):
  - ESN(matched)  : classical reservoir, same PCA inputs, same #features, same readout
  - Linear(PCA)   : ridge directly on the PCA features (no reservoir) -> isolates the
                    reservoir's nonlinear lift.

Data: real MNIST fetched ONCE from the public Keras .npz mirror (numpy-only; no
scikit-learn/openml dependency) and cached to data/mnist_subset.npz, after which
the benchmark runs fully offline (consistent with the repo's bundled-data doctrine).

Usage:
  python3 mnist_benchmark.py                 # default sweep (n=5,8,10) + noise
  python3 mnist_benchmark.py --quick         # fast smoke
  python3 mnist_benchmark.py --ns 5 8 10 12  # custom qubit counts
  python3 mnist_benchmark.py --no-noise

Team EIGENNEXUS | GIC 2026 - Phase 3 (common benchmark)
"""
import argparse
import os
import time
import numpy as np

from qrc_engine import QuantumReservoir
from classical_baselines import EchoStateNetwork

MNIST_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "data", "mnist_subset.npz")
# Real MNIST (Keras .npz mirror: x_train/y_train/x_test/y_test, uint8 28x28).
# Single numpy-loadable file -> no scikit-learn / openml dependency.
MNIST_NPZ_URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz"
MNIST_NPZ_FALLBACK = "https://ossci-datasets.s3.amazonaws.com/mnist/mnist.npz"
CACHE_NTRAIN = 6000       # generous cached subset (committed for offline reproducibility)
CACHE_NTEST = 1000
MAX_DENSE_N = 12          # dense statevector frontier for this pure-NumPy engine
MAX_NOISE_N = 10          # exact density-matrix noise frontier
DEFAULT_NTRAIN = 4000
DEFAULT_NTEST = 1000
N_CLASSES = 10
LAMBDAS = (1e-4, 1e-3, 1e-2, 1e-1, 1.0)
VAL_FRAC = 0.2


# ---------------------------------------------------------------------------
# Data: fetch once via sklearn, cache to npz, then numpy-only thereafter
# ---------------------------------------------------------------------------
def _download(url, dst, timeout=180):
    """Download url -> dst. Try urllib (honors *_proxy env), fall back to curl."""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, dst)
        return True
    except Exception as e:
        print(f"  urllib failed ({e}); trying curl...")
        import subprocess
        r = subprocess.run(["curl", "-sSL", "--max-time", str(timeout), "-o", dst, url])
        return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0


def _fetch_and_cache_mnist(n_train, n_test, seed=0):
    print("(MNIST cache miss -> fetching real MNIST .npz, one time...)")
    raw = os.path.join(os.path.dirname(MNIST_CACHE), "_mnist_raw.npz")
    os.makedirs(os.path.dirname(MNIST_CACHE), exist_ok=True)
    if not os.path.exists(raw):
        ok = _download(MNIST_NPZ_URL, raw) or _download(MNIST_NPZ_FALLBACK, raw)
        if not ok:
            raise RuntimeError("Could not download MNIST. On qBraid this works; "
                               "in a restricted sandbox, pre-place mnist.npz at "
                               f"{raw} or data/mnist_subset.npz.")
    d = np.load(raw)
    Xtr_f = d["x_train"].reshape(len(d["x_train"]), -1).astype(np.uint8)  # (60000,784)
    ytr_f = d["y_train"].astype(np.int64)
    Xte_f = d["x_test"].reshape(len(d["x_test"]), -1).astype(np.uint8)    # (10000,784)
    yte_f = d["y_test"].astype(np.int64)
    rng = np.random.RandomState(seed)
    tri = rng.permutation(len(Xtr_f))[:n_train]
    tei = rng.permutation(len(Xte_f))[:n_test]
    Xtr, ytr, Xte, yte = Xtr_f[tri], ytr_f[tri], Xte_f[tei], yte_f[tei]
    np.savez_compressed(MNIST_CACHE, X_train=Xtr, y_train=ytr, X_test=Xte, y_test=yte)
    print(f"  cached -> {MNIST_CACHE}  (train={len(Xtr)}, test={len(Xte)}, real MNIST 28x28)")
    return Xtr, ytr, Xte, yte


def load_mnist(n_train=DEFAULT_NTRAIN, n_test=DEFAULT_NTEST, seed=0):
    if os.path.exists(MNIST_CACHE):
        d = np.load(MNIST_CACHE)
        Xtr, ytr, Xte, yte = d["X_train"], d["y_train"], d["X_test"], d["y_test"]
        # honor requested sizes if the cache is at least that big
        if len(Xtr) >= n_train and len(Xte) >= n_test:
            return (Xtr[:n_train].astype(float), ytr[:n_train],
                    Xte[:n_test].astype(float), yte[:n_test])
    Xtr, ytr, Xte, yte = _fetch_and_cache_mnist(max(n_train, CACHE_NTRAIN),
                                                max(n_test, CACHE_NTEST), seed)
    return (Xtr[:n_train].astype(float), ytr[:n_train],
            Xte[:n_test].astype(float), yte[:n_test])


# ---------------------------------------------------------------------------
# Preprocess: PCA(n) on train, scale to [0,1] for RY encoding (train stats only)
# ---------------------------------------------------------------------------
def pca_encode(Xtr, Xte, n_comp):
    """PCA via SVD (fit on train), project both, min-max scale to [0,1] on train."""
    mu = Xtr.mean(0)
    Xtr_c = Xtr - mu; Xte_c = Xte - mu
    # right singular vectors = principal axes
    _, _, Vt = np.linalg.svd(Xtr_c, full_matrices=False)
    W = Vt[:n_comp].T                         # (784, n_comp)
    Ztr = Xtr_c @ W; Zte = Xte_c @ W
    lo, hi = Ztr.min(0), Ztr.max(0)
    rng = np.where((hi - lo) == 0, 1.0, hi - lo)
    Ptr = np.clip((Ztr - lo) / rng, 0.0, 1.0)
    Pte = np.clip((Zte - lo) / rng, 0.0, 1.0)
    return Ptr, Pte


# ---------------------------------------------------------------------------
# Feature maps
# ---------------------------------------------------------------------------
def feat_dim(n):
    return n + n * (n - 1) // 2


def quantum_features(P, n, tau, seed, noise=None, noise_rate=0.0):
    """CHIMERA reservoir features for static inputs P (one row per image)."""
    if n > MAX_DENSE_N:                      # sparse-exact path (noiseless only), matches dense
        assert noise is None, "noise sim is density-matrix (dense, n<=%d) only" % MAX_NOISE_N
        from tensor_backend import chimera_features_sparse
        return chimera_features_sparse(P, n, tau, seed)
    qr = QuantumReservoir(n_qubits=n, tau=tau, hamiltonian_type="ising",
                          input_qubits=list(range(n)),   # ALL qubits receive a PCA feature
                          hx=1.0, connectivity=0.5, seed=seed,
                          noise_type=noise, noise_rate=noise_rate)
    F = np.empty((len(P), qr.feature_dim))
    for i, x in enumerate(P):
        F[i] = qr.step(x)
    return F


def esn_features(P, n_res, seed):
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=0.9, leaking_rate=0.5,
                           input_scaling=1.0, connectivity=0.05, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(P.shape[1])
    F = np.empty((len(P), n_res))
    for i, x in enumerate(P):
        esn.reset(); F[i] = esn.step(x)
    return F


# ---------------------------------------------------------------------------
# Linear multiclass ridge readout (one-hot regression; numpy only)
# ---------------------------------------------------------------------------
def _standardize_fit(F):
    mu, sd = F.mean(0), F.std(0); sd = np.where(sd < 1e-8, 1.0, sd)
    return mu, sd


def multiclass_ridge_accuracy(F_tr, y_tr, F_te, y_te, lambdas=LAMBDAS, val_frac=VAL_FRAC):
    """Train a linear (ridge) one-hot readout, pick lambda on a validation tail,
    refit on full train, return test accuracy. The ONLY trained layer (QRC doctrine)."""
    Y = np.eye(N_CLASSES)[y_tr]
    n = len(y_tr); nval = int(round(n * val_frac)); nfit = n - nval
    Ff, yf, Fv, yv = F_tr[:nfit], Y[:nfit], F_tr[nfit:], y_tr[nfit:]
    mu, sd = _standardize_fit(Ff)
    Xf = (Ff - mu) / sd; Xv = (Fv - mu) / sd
    A = Xf.T @ Xf; rhs = Xf.T @ yf; I = np.eye(A.shape[0])
    best_l, best_acc = lambdas[0], -1.0
    for lam in lambdas:
        W = np.linalg.solve(A + lam * I, rhs)
        pred = np.argmax(Xv @ W, axis=1)
        acc = float(np.mean(pred == yv))
        if acc > best_acc:
            best_acc, best_l = acc, lam
    # refit on full train
    mu, sd = _standardize_fit(F_tr)
    Xtr = (F_tr - mu) / sd; Xte = (F_te - mu) / sd
    W = np.linalg.solve(Xtr.T @ Xtr + best_l * np.eye(Xtr.shape[1]), Xtr.T @ Y)
    pred = np.argmax(Xte @ W, axis=1)
    return float(np.mean(pred == y_te)), best_l


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------
def run_accuracy_sweep(ns, Xtr, ytr, Xte, yte, seeds, tau=2.0):
    rows = []
    print("\n" + "=" * 78)
    print("MNIST ACCURACY vs QUBIT COUNT  (PCA(n) -> n qubits -> linear readout)")
    print(f"train={len(ytr)}  test={len(yte)}  seeds={seeds}")
    print("=" * 78)
    print(f"{'n':>3}{'#qfeat':>8}{'CHIMERA':>10}{'+-sd':>7}{'ESN':>9}{'Linear(PCA)':>13}{'sec':>7}")
    for n in ns:
        if n > MAX_DENSE_N:
            print(f"{n:>3}  -- sparse-exact backend (n>{MAX_DENSE_N}; ~1-2 s/image, noiseless)",
                  flush=True)
        t0 = time.time()
        Ptr, Pte = pca_encode(Xtr, Xte, n)
        # linear-on-PCA baseline (no reservoir)
        lin_acc, _ = multiclass_ridge_accuracy(Ptr, ytr, Pte, yte)
        # quantum (per seed) + matched ESN
        q_accs, e_accs = [], []
        for sd in seeds:
            FQ_tr = quantum_features(Ptr, n, tau, sd)
            FQ_te = quantum_features(Pte, n, tau, sd)
            qa, _ = multiclass_ridge_accuracy(FQ_tr, ytr, FQ_te, yte)
            q_accs.append(qa)
            FE_tr = esn_features(Ptr, feat_dim(n), sd)
            FE_te = esn_features(Pte, feat_dim(n), sd)
            ea, _ = multiclass_ridge_accuracy(FE_tr, ytr, FE_te, yte)
            e_accs.append(ea)
        dt = time.time() - t0
        rows.append(dict(n=n, n_feat=feat_dim(n), chimera=float(np.mean(q_accs)),
                         chimera_sd=float(np.std(q_accs)), esn=float(np.mean(e_accs)),
                         linear=lin_acc, sec=dt))
        print(f"{n:>3}{feat_dim(n):>8}{np.mean(q_accs):>10.4f}{np.std(q_accs):>7.4f}"
              f"{np.mean(e_accs):>9.4f}{lin_acc:>13.4f}{dt:>7.1f}")
    return rows


def run_noise_sweep(ns, Xtr, ytr, Xte, yte, settings, seeds, tau=2.0):
    rows = []
    print("\n" + "=" * 78)
    print("MNIST NOISE SWEEP  (exact density-matrix channels; n capped at %d)" % MAX_NOISE_N)
    print("=" * 78)
    print(f"{'n':>3}  {'channel':>18}{'rate':>7}{'CHIMERA acc':>13}{'sec':>7}")
    for n in ns:
        if n > MAX_NOISE_N:
            print(f"{n:>3}  -- skipped (exact-noise frontier n={MAX_NOISE_N})")
            continue
        Ptr, Pte = pca_encode(Xtr, Xte, n)
        for (noise, rate) in settings:
            t0 = time.time()
            accs = []
            for sd in seeds:
                FQ_tr = quantum_features(Ptr, n, tau, sd, noise=noise, noise_rate=rate)
                FQ_te = quantum_features(Pte, n, tau, sd, noise=noise, noise_rate=rate)
                a, _ = multiclass_ridge_accuracy(FQ_tr, ytr, FQ_te, yte)
                accs.append(a)
            dt = time.time() - t0
            label = noise if noise else "noiseless"
            rows.append(dict(n=n, channel=label, rate=rate, acc=float(np.mean(accs)), sec=dt))
            print(f"{n:>3}  {label:>18}{rate:>7.3f}{np.mean(accs):>13.4f}{dt:>7.1f}")
    return rows


def make_noise_curve_figure(noise_rows, path="figures/fig_mnist_noise.png"):
    """Accuracy vs noise RATE, one line per (n, channel) - the robustness curve."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(noise figure skipped: {e})")
        return
    if not noise_rows:
        return
    from collections import defaultdict
    series = defaultdict(list)
    for r in noise_rows:
        series[(r["n"], r["channel"])].append((r["rate"], r["acc"]))
    fig, ax = plt.subplots(figsize=(6, 4))
    for (n, ch), pts in sorted(series.items()):
        if ch == "noiseless":
            continue
        pts = sorted(pts)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", label=f"n={n} {ch}")
    ax.set_title("MNIST accuracy vs noise rate (CHIMERA-QRC)")
    ax.set_xlabel("noise rate"); ax.set_ylabel("test accuracy")
    ax.legend(fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"\nsaved noise figure -> {path}")


def make_figure(acc_rows, noise_rows, path="figures/fig_mnist.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(figure skipped: {e})")
        return
    if not acc_rows:
        return
    npanels = 2 if noise_rows else 1
    fig, ax = plt.subplots(1, npanels, figsize=(5.5 * npanels, 3.8), squeeze=False)
    ns = [r["n"] for r in acc_rows]
    ax[0][0].plot(ns, [r["chimera"] for r in acc_rows], "o-", label="CHIMERA (quantum)")
    ax[0][0].plot(ns, [r["esn"] for r in acc_rows], "s--", label="ESN (matched)")
    ax[0][0].plot(ns, [r["linear"] for r in acc_rows], "^:", color="gray", label="Linear(PCA)")
    ax[0][0].set_title("MNIST accuracy vs qubit count")
    ax[0][0].set_xlabel("qubits n"); ax[0][0].set_ylabel("test accuracy")
    ax[0][0].legend(fontsize=8)
    if noise_rows:
        from collections import defaultdict
        by_ch = defaultdict(list)
        for r in noise_rows:
            by_ch[r["channel"]].append((r["n"], r["acc"]))
        for ch, pts in by_ch.items():
            pts.sort()
            ax[0][1].plot([p[0] for p in pts], [p[1] for p in pts], "o-", label=ch)
        ax[0][1].set_title("MNIST accuracy under noise")
        ax[0][1].set_xlabel("qubits n"); ax[0][1].set_ylabel("test accuracy")
        ax[0][1].legend(fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"\nsaved figure -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-noise", action="store_true")
    ap.add_argument("--noise-only", action="store_true",
                    help="skip accuracy sweep; run only the noise-rate robustness curve")
    ap.add_argument("--ntrain", type=int, default=DEFAULT_NTRAIN)
    ap.add_argument("--ntest", type=int, default=DEFAULT_NTEST)
    ap.add_argument("--n15", action="store_true",
                    help="brief's 5/10/15 closure: run n=12 (dense) and n=15 (sparse-exact) on "
                         "the SAME reduced subset (1500/500, 1 seed) for a like-for-like point")
    args = ap.parse_args()

    if args.n15:
        ntr, nte = 1500, 500          # same subset the noise sweep uses; keeps n=15 tractable
        seeds = (0,)
        t_all = time.time()
        print("#" * 78)
        print("CHIMERA-QRC MNIST - n=15 CLOSURE (brief's 5/10/15; sparse-exact backend)")
        print(f"paired n=12 (dense) vs n=15 (sparse) on the SAME subset {ntr}/{nte}, seed {seeds}")
        print("#" * 78)
        Xtr, ytr, Xte, yte = load_mnist(ntr, nte)
        rows = run_accuracy_sweep([12, 15], Xtr, ytr, Xte, yte, seeds)
        np.save("mnist_n15_results.npy", dict(rows=rows, n_train=ntr, n_test=nte, seeds=seeds),
                allow_pickle=True)
        print(f"\nsaved mnist_n15_results.npy   [total {time.time()-t_all:.1f}s]")
        return

    if args.noise_only:
        ns = args.ns or [5, 8]
        seeds = (0, 1)
        ntr, nte = 1500, 500   # smaller subset keeps the density-matrix sweep tractable
        t_all = time.time()
        print("#" * 78)
        print("CHIMERA-QRC MNIST - NOISE-RATE ROBUSTNESS CURVE")
        print(f"qubit counts: {ns}   seeds: {seeds}   subset {ntr}/{nte}")
        print("#" * 78)
        Xtr, ytr, Xte, yte = load_mnist(ntr, nte)
        rates = [0.0, 0.05, 0.1, 0.2, 0.3]
        settings = ([(None, 0.0)]
                    + [("depolarizing", r) for r in rates if r > 0]
                    + [("amplitude_damping", r) for r in rates if r > 0])
        # tag the noiseless point as rate 0.0 for both channels in the figure
        noise_rows = run_noise_sweep(ns, Xtr, ytr, Xte, yte, settings, seeds)
        # duplicate the noiseless accuracy as the rate=0 anchor for each channel
        base = {r["n"]: r["acc"] for r in noise_rows if r["channel"] == "noiseless"}
        for n, acc in base.items():
            for ch in ("depolarizing", "amplitude_damping"):
                noise_rows.append(dict(n=n, channel=ch, rate=0.0, acc=acc, sec=0.0))
        make_noise_curve_figure(noise_rows)
        np.save("mnist_noise_results.npy", dict(noise=noise_rows, n_train=ntr, n_test=nte),
                allow_pickle=True)
        print(f"\nsaved mnist_noise_results.npy   [total {time.time()-t_all:.1f}s]")
        return

    if args.quick:
        ns = args.ns or [5, 8]
        seeds = (0,); do_noise = False
        ntr, nte = 1500, 500
    else:
        ns = args.ns or [5, 8, 10]
        seeds = (0, 1, 2); do_noise = not args.no_noise
        ntr, nte = args.ntrain, args.ntest

    t_all = time.time()
    print("#" * 78)
    print("CHIMERA-QRC COMMON BENCHMARK - MNIST digit classification")
    print(f"qubit counts: {ns}   seeds: {seeds}   dense frontier n<={MAX_DENSE_N}")
    print("#" * 78)

    Xtr, ytr, Xte, yte = load_mnist(ntr, nte)
    print(f"data: train={len(ytr)}  test={len(yte)}  (10 classes)")

    acc_rows = run_accuracy_sweep(ns, Xtr, ytr, Xte, yte, seeds)

    noise_rows = []
    if do_noise:
        noise_ns = [n for n in ns if n <= MAX_NOISE_N][:2] or [5]
        settings = [(None, 0.0), ("depolarizing", 0.02), ("amplitude_damping", 0.02)]
        noise_rows = run_noise_sweep(noise_ns, Xtr, ytr, Xte, yte, settings, seeds[:2])

    if not args.quick:           # --quick must not clobber committed full-run artifacts
        make_figure(acc_rows, noise_rows)
        out = dict(ns=ns, accuracy=acc_rows, noise=noise_rows,
                   n_train=len(ytr), n_test=len(yte))
        np.save("mnist_results.npy", out, allow_pickle=True)
        print(f"\nsaved mnist_results.npy")
    else:
        print("\n[--quick] skipped writing figure/results (committed full-run artifacts preserved)")
    print(f"[total wall-clock {time.time() - t_all:.1f}s]")


if __name__ == "__main__":
    main()
