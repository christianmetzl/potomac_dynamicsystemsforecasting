"""
tensor_backend.py - sparse / tensor-network backend to push CHIMERA-QRC past the
dense statevector wall (n=12) and to quantify quantum complexity via the
entanglement (Schmidt / bond-dimension) spectrum.

Two capabilities:

1. SPARSE EXACT EVOLUTION.  The dense engine forms U = exp(-iH tau) as a
   2^n x 2^n matrix (infeasible beyond ~12 qubits). Here we never form U: we build
   H as a sparse operator (diagonal ZZ part + sparse transverse-field X part) and
   apply exp(-iH tau)|psi> with scipy.sparse.linalg.expm_multiply, batched over
   inputs. Inputs are product states (RY angle encoding), built directly by
   Kronecker product. This reaches n ~ 16-18 exactly on a single node and lets the
   g(n) / effective-rank curves continue past the dense frontier (covering the
   brief's 5/10/15-qubit examples).

2. BOND DIMENSION AS A COMPLEXITY METRIC.  For the FULLY-CONNECTED random-coupling
   Ising reservoir, an MPS/TEBD simulation would need a bond dimension chi set by
   the state's entanglement. Rather than claim an MPS compression that does not help
   for an all-to-all Hamiltonian, we MEASURE it honestly: across a balanced
   bipartition we SVD the exact evolved statevector to obtain the Schmidt spectrum,
   the entanglement entropy S, and the effective bond dimension chi_eff (Schmidt
   rank above a tolerance). We report chi_eff(n) and S(n): if chi_eff grows toward
   2^(n/2) (the max), classical MPS simulation cost ~ chi^2 explodes - precisely the
   classical-intractability precondition the quantum-advantage hypothesis needs.

Correctness: a built-in equivalence check confirms the sparse path reproduces the
dense engine's features to ~1e-10 at small n.

Usage:
  python3 tensor_backend.py --check                 # equivalence vs dense engine
  python3 tensor_backend.py --ns 8 10 12 14 16      # g(n), rank(n), chi(n), S(n)

Team EIGENNEXUS | GIC 2026 - Phase 3 (item 7: scaling frontier + complexity metric)
"""
import argparse
import time
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import expm_multiply

from qrc_engine import generate_coupling_matrix
# kernel-geometry helpers + matched ESN + data loader (scaling_sweep has a __main__ guard)
from scaling_sweep import (
    lin_kernel, eff_dim, num_rank, kta, geom_diff, feat_dim,
    esn_features, load_calm_kernel_data,
)

HX = 1.0
CONNECTIVITY = 0.5
DEFAULT_TAU = 2.0


# ---------------------------------------------------------------------------
# Sparse Ising Hamiltonian (matches qrc_engine.build_ising_hamiltonian convention:
# qubit 0 = most-significant bit; H = sum_{i<j} J_ij Z_iZ_j + hx sum_i X_i)
# ---------------------------------------------------------------------------
def _bit_signs(n):
    """signs[q, b] = (-1)^{bit q of b}, big-endian (qubit 0 = MSB)."""
    idx = np.arange(2 ** n)
    bits = np.array([((idx >> (n - 1 - q)) & 1) for q in range(n)])
    return 1 - 2 * bits                                  # (n, 2^n)


def build_sparse_ising(n, J, hx=HX):
    dim = 2 ** n
    signs = _bit_signs(n)
    # diagonal ZZ part
    diag = np.zeros(dim)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(J[i, j]) > 1e-12:
                diag += J[i, j] * signs[i] * signs[j]
    H = sp.diags(diag, format="csr").astype(complex)
    # transverse field: hx * sum_i X_i  (X_i flips bit i)
    if abs(hx) > 1e-12:
        cols = np.arange(dim)
        rows_all, cols_all = [], []
        for i in range(n):
            mask = 1 << (n - 1 - i)
            rows_all.append(cols ^ mask)
            cols_all.append(cols)
        rows = np.concatenate(rows_all); cols2 = np.concatenate(cols_all)
        data = np.full(len(rows), hx, dtype=complex)
        H = H + sp.csr_matrix((data, (rows, cols2)), shape=(dim, dim))
    return H


# ---------------------------------------------------------------------------
# Product-state encoding (RY(pi*x) on |0...0>) and Pauli-Z readout
# ---------------------------------------------------------------------------
def encode_product_states(X, n):
    """X: (B, m) inputs in [0,1], m<=n. Returns (2^n, B) product statevectors."""
    B, m = X.shape
    states = np.ones((B, 1), dtype=complex)
    for q in range(n):
        if q < m:
            th = np.pi * np.clip(X[:, q], 0, 1)
            qb = np.stack([np.cos(th / 2), np.sin(th / 2)], axis=1)   # (B,2)
        else:
            qb = np.tile(np.array([1.0, 0.0]), (B, 1))
        # kron along the state axis: (B, 2^q) x (B,2) -> (B, 2^{q+1})
        states = (states[:, :, None] * qb[:, None, :]).reshape(B, -1)
    return states.T                                       # (2^n, B)


def measure_features_batch(psi, n):
    """psi: (2^n, B). Returns (B, n + n(n-1)/2) of <Z_i> and <Z_iZ_j>."""
    probs = np.abs(psi) ** 2                               # (2^n, B)
    signs = _bit_signs(n)                                  # (n, 2^n)
    z = signs @ probs                                      # (n, B)
    pairs = [(signs[i] * signs[j]) @ probs
             for i in range(n) for j in range(i + 1, n)]
    zz = np.array(pairs) if pairs else np.zeros((0, psi.shape[1]))
    return np.vstack([z, zz]).T                            # (B, featdim)


def chimera_features_sparse(X, n, tau=DEFAULT_TAU, seed=0, chunk=512):
    """Sparse-exact CHIMERA features at n qubits (matches the dense engine)."""
    J = generate_coupling_matrix(n, CONNECTIVITY, seed=seed)
    A = (-1j * tau) * build_sparse_ising(n, J, HX)
    out = []
    for s in range(0, len(X), chunk):
        psi0 = encode_product_states(X[s:s + chunk], n)    # (2^n, b)
        psi = expm_multiply(A, psi0)                        # (2^n, b)
        out.append(measure_features_batch(psi, n))
    return np.vstack(out)


# ---------------------------------------------------------------------------
# Entanglement / bond-dimension across a balanced bipartition
# ---------------------------------------------------------------------------
def entanglement_of_states(X, n, tau=DEFAULT_TAU, seed=0, tol=1e-10, sample=64):
    """Mean entanglement entropy S and effective bond dimension chi_eff over a
    sample of evolved reservoir states, for the balanced cut [0..nA) | [nA..n)."""
    J = generate_coupling_matrix(n, CONNECTIVITY, seed=seed)
    A = (-1j * tau) * build_sparse_ising(n, J, HX)
    Xs = X[:sample]
    psi0 = encode_product_states(Xs, n)
    psi = expm_multiply(A, psi0)                            # (2^n, b)
    nA = n // 2; nB = n - nA
    S_list, chi_list = [], []
    for k in range(psi.shape[1]):
        M = psi[:, k].reshape(2 ** nA, 2 ** nB)
        sv = np.linalg.svd(M, compute_uv=False)
        p = sv ** 2; p = p[p > tol]
        S_list.append(float(-(p * np.log(p)).sum()))
        chi_list.append(int((sv > np.sqrt(tol)).sum()))
    return float(np.mean(S_list)), float(np.mean(chi_list)), 2 ** min(nA, nB)


# ---------------------------------------------------------------------------
# Equivalence check vs the dense engine
# ---------------------------------------------------------------------------
def equivalence_check(ns=(6, 8), tau=DEFAULT_TAU, seed=0):
    from delay_qrc import DelayEmbeddingQRC
    print("Sparse-vs-dense equivalence check (should be ~1e-10):")
    ok = True
    rng = np.random.RandomState(0)
    for n in ns:
        m = min(n, 8)
        X = rng.uniform(0, 1, (5, m))
        Fs = chimera_features_sparse(X, n, tau, seed)
        d = DelayEmbeddingQRC(n_qubits=n, tau=tau, hamiltonian='ising',
                              hx=HX, connectivity=CONNECTIVITY, seed=seed)
        Fd = np.array([d._step_features(x) for x in X])
        delta = float(np.abs(Fs - Fd).max())
        print(f"  n={n}: max|sparse - dense| = {delta:.2e}  {'OK' if delta < 1e-8 else 'MISMATCH'}")
        ok = ok and delta < 1e-8
    return ok


# ---------------------------------------------------------------------------
# High-n sweep: g(n), rank(n), entanglement chi(n), S(n)
# ---------------------------------------------------------------------------
def run_highn_sweep(ns, seed=0, subsample=600):
    Q, y, tr = load_calm_kernel_data()
    idx = np.linspace(0, len(tr) - 1, min(subsample, len(tr))).astype(int)
    trk = np.array(tr)[idx]
    yc = y[trk] - y[trk].mean()
    n_lags = Q.shape[1]

    rows = []
    print("\n" + "=" * 84)
    print(f"HIGH-N SWEEP (sparse exact)  N_sub={len(trk)}  cut=balanced bipartition")
    print("=" * 84)
    print(f"{'n':>3}{'enc':>5}{'#feat':>7}{'g(E||C)':>10}{'g_ctrl':>9}{'D_eff':>8}"
          f"{'rank':>6}{'S_ent':>8}{'chi_eff':>9}{'chi_max':>9}{'sec':>7}")
    for n in ns:
        t0 = time.time()
        m = min(n, n_lags)
        Qn = Q[:, :m]
        FQ = chimera_features_sparse(Qn[trk], n, DEFAULT_TAU, seed)
        nr = feat_dim(n)
        Fe = esn_features(Qn[trk], nr, seed)
        Feb = esn_features(Qn[trk], nr, seed + 1)
        KQ, Ke, Keb = lin_kernel(FQ), lin_kernel(Fe), lin_kernel(Feb)
        g_q = geom_diff(Ke, KQ); g_c = geom_diff(Ke, Keb)
        de = eff_dim(KQ); rk = num_rank(KQ)
        S, chi, chimax = entanglement_of_states(Qn[trk], n, DEFAULT_TAU, seed)
        dt = time.time() - t0
        rows.append(dict(n=n, n_enc=m, n_feat=FQ.shape[1], g_quantum=g_q, g_control=g_c,
                         d_eff=de, rank=rk, S_ent=S, chi_eff=chi, chi_max=chimax, sec=dt))
        print(f"{n:>3}{m:>5}{FQ.shape[1]:>7}{g_q:>10.1f}{g_c:>9.1f}{de:>8.2f}{rk:>6}"
              f"{S:>8.3f}{chi:>9.1f}{chimax:>9}{dt:>7.1f}")
    return rows


def make_figure(rows, path="figures/fig_tensor_complexity.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(figure skipped: {e})"); return
    if not rows:
        return
    ns = [r["n"] for r in rows]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(ns, [r["chi_eff"] for r in rows], "o-", label="chi_eff (entanglement)")
    ax[0].plot(ns, [r["chi_max"] for r in rows], "k--", label="chi_max = 2^(n/2)")
    ax[0].set_yscale("log"); ax[0].set_title("Bond dimension vs qubits (all-to-all Ising)")
    ax[0].set_xlabel("qubits n"); ax[0].set_ylabel("effective bond dimension chi")
    ax[0].legend(fontsize=8)
    ax[1].plot(ns, [r["g_quantum"] for r in rows], "o-", label="g(ESN||CHIMERA)")
    ax[1].plot(ns, [r["g_control"] for r in rows], "s--", color="gray", label="control")
    ax[1].set_title("Kernel distinctness g(n) (sparse exact)")
    ax[1].set_xlabel("qubits n"); ax[1].set_ylabel("g")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"\nsaved figure -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[8, 10, 12, 14])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--subsample", type=int, default=600)
    args = ap.parse_args()

    print("#" * 84)
    print("CHIMERA-QRC TENSOR / SPARSE BACKEND - scaling frontier + complexity metric")
    print("#" * 84)
    ok = equivalence_check()
    if not ok:
        print("!! equivalence check FAILED - aborting (sparse path must match dense)")
        return
    if args.check:
        return
    rows = run_highn_sweep(args.ns, subsample=args.subsample)
    make_figure(rows)
    np.save("tensor_backend_results.npy", dict(rows=rows), allow_pickle=True)
    print("\nsaved tensor_backend_results.npy")


if __name__ == "__main__":
    main()
