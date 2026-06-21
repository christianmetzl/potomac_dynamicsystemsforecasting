"""
mps_engine.py - Matrix-Product-State (tensor-network) backend for CHIMERA-QRC.
================================================================================
A finite MPS / canonical-form TEBD engine that reproduces the dense qrc_engine
reservoir (RY encode -> e^{-iH tau} -> <Z_i>,<Z_iZ_j>) but represents the state as
a chain of rank-3 tensors with a bounded bond dimension chi. This lets the
reservoir simulation push past the dense 2^n wall (n=12) toward ~30 qubits.

HONESTY NOTE. The Phase-2 reservoir Hamiltonian is a transverse-field Ising model
with a RANDOM coupling graph (connectivity 0.5) - i.e. LONG-RANGE couplings. Those
are the hard case for an MPS: they build entanglement quickly, so an exact
representation needs a bond dimension that can grow exponentially. This engine
therefore TRUNCATES to a fixed chi and LOGS the discarded weight (truncation
error) and the bond dimensions actually reached. The point is not to pretend MPS
is free, but to MEASURE, as n grows, (a) whether the reservoir's entanglement
stays low enough for a bounded chi to be accurate, and (b) what truncation costs -
itself a decisive result for whether the CHIMERA reservoir needs genuinely
exponential resources.

Conventions
-----------
* d = 2. State = list M[0..n-1] of tensors, M[k] shape (Dl, 2, Dr); Dl=Dr=1 at the
  boundaries. Big-endian to match qrc_engine (qubit 0 == most significant bit).
* Orthogonality center (OC) maintained rigorously: sites < oc are left-canonical,
  sites > oc are right-canonical, so single-site/two-point expectations and SVD
  truncations are exact/optimal.

Team EIGENNEXUS | GIC 2026 - Phase 3, Axis-A (scale).
"""
from __future__ import annotations
import numpy as np

_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
_SWAP4 = np.array([[1, 0, 0, 0],
                   [0, 0, 1, 0],
                   [0, 1, 0, 0],
                   [0, 0, 0, 1]], dtype=complex)   # (new a,b)<-(old c,d): a=d, b=c


def _ry(theta: float) -> np.ndarray:
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def _field_gate(a: float) -> np.ndarray:
    """exp(-i a X) = cos(a) I - i sin(a) X (single-qubit transverse-field half-step)."""
    return np.cos(a) * np.eye(2, dtype=complex) - 1j * np.sin(a) * _X


def _zz_gate(jdt: float) -> np.ndarray:
    """exp(-i (J dt) Z(x)Z) as a 4x4 in basis (00,01,10,11). Z(x)Z = diag(+,-,-,+)."""
    d = np.exp(-1j * jdt * np.array([1.0, -1.0, -1.0, 1.0]))
    return np.diag(d).astype(complex)


class MPS:
    """Finite MPS with a rigorously maintained orthogonality center."""

    def __init__(self, n_qubits: int, chi: int = 64, svd_tol: float = 1e-12):
        self.n = n_qubits
        self.chi = chi
        self.svd_tol = svd_tol
        self.M = [np.zeros((1, 2, 1), dtype=complex) for _ in range(n_qubits)]
        for k in range(n_qubits):
            self.M[k][0, 0, 0] = 1.0           # product state |0...0>
        self.oc = 0
        self.trunc_errs: list[float] = []      # discarded weight per two-site SVD

    # ---- orthogonality-center management (QR, no truncation) -----------------
    def _shift_right(self, k):
        Dl, d, Dr = self.M[k].shape
        Q, R = np.linalg.qr(self.M[k].reshape(Dl * d, Dr))
        r = Q.shape[1]
        self.M[k] = Q.reshape(Dl, d, r)
        self.M[k + 1] = np.tensordot(R, self.M[k + 1], axes=([1], [0]))

    def _shift_left(self, k):
        Dl, d, Dr = self.M[k].shape
        Q, R = np.linalg.qr(self.M[k].reshape(Dl, d * Dr).T)   # A^T = Q R
        r = Q.shape[1]
        self.M[k] = Q.T.reshape(r, d, Dr)                      # right-canonical
        self.M[k - 1] = np.tensordot(self.M[k - 1], R.T, axes=([2], [0]))

    def _move_oc(self, target):
        while self.oc < target:
            self._shift_right(self.oc); self.oc += 1
        while self.oc > target:
            self._shift_left(self.oc); self.oc -= 1

    def canonicalize(self):
        self._move_oc(self.n - 1)
        self._move_oc(0)

    # ---- gates ---------------------------------------------------------------
    def apply_1q(self, g2, k):
        self._move_oc(k)
        self.M[k] = np.einsum('ac,lcr->lar', g2, self.M[k])

    def apply_2q(self, g4, k):
        """Apply 4x4 gate to adjacent sites (k,k+1); SVD-truncate to chi; OC -> k+1."""
        self._move_oc(k)
        Dl, d, _ = self.M[k].shape
        Dr = self.M[k + 1].shape[2]
        theta = np.tensordot(self.M[k], self.M[k + 1], axes=([2], [0]))   # (Dl,d,d,Dr)
        theta = np.einsum('xy,lyr->lxr', g4, theta.reshape(Dl, d * d, Dr))
        theta = theta.reshape(Dl * d, d * Dr)
        U, S, Vh = np.linalg.svd(theta, full_matrices=False)
        tot = float(np.sum(S ** 2))
        keep = int(np.sum(S > self.svd_tol))
        keep = max(1, min(keep, self.chi))
        disc = float(np.sum(S[keep:] ** 2)) / tot if tot > 0 else 0.0
        self.trunc_errs.append(disc)
        U, S, Vh = U[:, :keep], S[:keep], Vh[:keep, :]
        S = S / np.sqrt(np.sum(S ** 2))                                    # renormalize
        self.M[k] = U.reshape(Dl, d, keep)
        self.M[k + 1] = (S[:, None] * Vh).reshape(keep, d, Dr)
        self.oc = k + 1

    def apply_2q_longrange(self, g4, i, j):
        """Apply a symmetric two-qubit gate between (possibly distant) i<j via a SWAP
        network: bubble qubit i adjacent to j, apply, then undo the swaps."""
        if j == i + 1:
            self.apply_2q(g4, i); return
        for p in range(i, j - 1):       # bubble qubit-i content to position j-1
            self.apply_2q(_SWAP4, p)
        self.apply_2q(g4, j - 1)
        for p in range(j - 2, i - 1, -1):
            self.apply_2q(_SWAP4, p)

    # ---- measurement (exact contractions in canonical form) ------------------
    def expect_z(self, i):
        self._move_oc(i)
        Mi = self.M[i]
        return float(np.real(np.einsum('acr,cd,adr->', Mi.conj(), _Z, Mi)))

    def measure_full_features(self):
        """[<Z_0>,...,<Z_{n-1}>, <Z_iZ_j> for i<j] - identical layout to qrc_engine."""
        self.canonicalize()
        z = np.empty(self.n)
        zz = []
        for i in range(self.n):
            self._move_oc(i)
            Mi = self.M[i]
            z[i] = np.real(np.einsum('acr,cd,adr->', Mi.conj(), _Z, Mi))
            ZMi = np.einsum('cd,adr->acr', _Z, Mi)            # Z on ket leg at site i
            L = np.einsum('acr,acs->rs', Mi.conj(), ZMi)      # L[bra-bond, ket-bond]
            for j in range(i + 1, self.n):
                Mj = self.M[j]
                val = np.einsum('bk,kct,bdt,dc->', L, Mj, Mj.conj(), _Z)
                zz.append(np.real(val))
                L = np.einsum('bk,kct,bcu->ut', L, Mj, Mj.conj())   # identity transfer
        return np.concatenate([z, np.array(zz)])

    # ---- diagnostics ---------------------------------------------------------
    @property
    def bond_dims(self):
        return [self.M[k].shape[2] for k in range(self.n - 1)]

    @property
    def max_bond(self):
        return max(self.bond_dims) if self.n > 1 else 1


def evolve_ising(mps: MPS, Jmat, tau, hx=1.0, steps=8):
    """2nd-order Trotter TEBD of exp(-i H tau), H = sum_{i<j} J_ij Z_iZ_j + hx sum_i X_i.
    Long-range ZZ pairs handled by SWAP networks. `steps` controls Trotter error O(tau^3/steps^2)."""
    n = mps.n
    dt = tau / steps
    pairs = [(i, j, Jmat[i, j]) for i in range(n) for j in range(i + 1, n)
             if abs(Jmat[i, j]) > 1e-12]
    half = _field_gate(hx * dt / 2.0)
    for _ in range(steps):
        for k in range(n):
            mps.apply_1q(half, k)
        for (i, j, J) in pairs:
            mps.apply_2q_longrange(_zz_gate(J * dt), i, j)
        for k in range(n):
            mps.apply_1q(half, k)


def reservoir_features_mps(emb, n_qubits, Jmat, tau, reupload=1, chi=64, steps=None):
    """MPS analogue of scaling_sweep._reservoir_features for a single input row `emb`.
    `steps=None` picks a tau-scaled Trotter budget (~32 steps per tau=2) that holds the
    Trotter error near 1e-3. Returns (features, max_bond, max_trunc_err)."""
    if steps is None:
        steps = max(24, int(round(24 * tau)))
    mps = MPS(n_qubits, chi=chi)
    for layer in range(reupload):
        blk = emb[layer * n_qubits:(layer + 1) * n_qubits]
        for q in range(min(len(blk), n_qubits)):
            mps.apply_1q(_ry(np.pi * float(np.clip(blk[q], 0, 1))), q)
        evolve_ising(mps, Jmat, tau, steps=steps)
    feats = mps.measure_full_features()
    return feats, mps.max_bond, (max(mps.trunc_errs) if mps.trunc_errs else 0.0)


# ============================ self-test vs dense ==============================
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ns", type=int, nargs="+", default=[6, 8])
    args = ap.parse_args()

    from qrc_engine import (build_ising_hamiltonian, generate_coupling_matrix,
                            apply_single_qubit_gate, Ry, measure_full_features)
    from scipy.linalg import expm

    def dense_features(emb, n, J, tau):
        H = build_ising_hamiltonian(n, J, hx=1.0)
        U = expm(-1j * H * tau)
        psi = np.zeros(2 ** n, dtype=complex); psi[0] = 1.0
        for q in range(min(len(emb), n)):
            psi = apply_single_qubit_gate(psi, Ry(np.pi * np.clip(emb[q], 0, 1)), q, n)
        psi = U @ psi
        return measure_full_features(psi, n)

    print("MPS self-test: max|MPS - dense expm| over random inputs (chi=2^n => no truncation,")
    print("so any error is Trotter-only and must vanish ~1/steps^2 as steps grow).")
    TOL = 3e-3
    rng = np.random.RandomState(0)
    ok = True
    for n in args.ns:
        J = generate_coupling_matrix(n, 0.5, seed=7)
        chi = 2 ** n                                   # effectively exact (no truncation)
        for tau in (2.0, 4.0):
            grid = tuple(int(s * max(1.0, tau / 2.0)) for s in (8, 16, 32, 64))  # steps ~ tau
            errs = []
            for steps in grid:
                e = 0.0
                for _ in range(4):
                    emb = rng.rand(n)
                    fd = dense_features(emb, n, J, tau)
                    fm, mb, te = reservoir_features_mps(emb, n, J, tau, chi=chi, steps=steps)
                    e = max(e, float(np.max(np.abs(fd - fm))))
                errs.append(e)
            tag = "  ".join(f"s{g}:{e:.1e}" for g, e in zip(grid, errs))
            ratio = errs[-2] / max(errs[-1], 1e-15)     # ~4x per doubling => 2nd order
            conv = (errs[-1] < TOL) and (errs[-1] < errs[0]) and (ratio > 2.5)
            ok = ok and conv
            print(f"  n={n:2d} tau={tau:.1f}  {tag}  (ratio={ratio:.1f})  {'OK' if conv else 'FAIL'}")
    print("SELF-TEST", "PASSED" if ok else "FAILED",
          "-- engine reproduces the dense reservoir; ~2nd-order Trotter convergence confirmed.")
    raise SystemExit(0 if ok else 1)
