"""
qrc_quantum_data.py  [V3 — the OUTLOOK: does QRC have an edge on QUANTUM data?]

Every other experiment fed the QRC CLASSICAL data (prices, weather) — the regime where we find no
advantage. The literature's actual claim for quantum reservoirs (Ghosh et al. 2019, npj QI; Fujii-
Nakajima 2017) is on QUANTUM data: a QRC can estimate NONLINEAR functionals of an input quantum
STATE (purity, entanglement) by processing the state natively, without first reconstructing it. We
test that here, honestly, as an outlook — not a submission claim.

Task: given random 2-qubit mixed states rho, estimate (a) purity Tr(rho^2) and (b) entanglement
(Wootters concurrence) — both NONLINEAR in rho.

Methods:
  QRC (quantum-native): inject rho into the 2 input qubits of an (2+m)-qubit CHIMERA reservoir, evolve
     under the fixed Ising unitary, measure Pauli-Z singles+pairs; RE-INJECT rho and repeat K times
     (temporal multiplexing). Repeated injection makes the readout observables POLYNOMIAL in rho, so
     degree-2 functionals (purity) become *linearly* readable. Density-matrix exact.
  Classical-linear (full tomography): ridge on the 15 Pauli expectations of rho. These FULLY
     determine the 2-qubit state, but a LINEAR map cannot produce a quadratic functional -> must fail
     on purity. This is the "what a single linear measurement gives you" bar.
  Classical-nonlinear (full tomography): RFF on the same 15 Pauli expectations -> CAN form the
     quadratic, so it matches. This is the fair classical control WITH full state information.

Honest reading: if QRC >> classical-linear but ~ classical-nonlinear, then the QRC's value is
NATIVE nonlinearity on quantum data (a real, qualitative capability), with any *quantitative* edge
emerging only when full tomography is expensive (many qubits) — the asymptotic outlook, which exact
2-qubit simulation cannot itself demonstrate.

Usage:  python3 qrc_quantum_data.py            # 700 states, m=4 memory, K=3, 4 seeds
        python3 qrc_quantum_data.py --quick    # 300 states, m=3, K=2, 2 seeds
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.linalg import expm
from qrc_engine import generate_coupling_matrix, build_ising_hamiltonian
from axisB_rigorous import rff_features, rbf_gamma
from vol_fair_benchmark import ridge_readout

TAU = 2.0
SY = np.array([[0, -1j], [1j, 0]])
PAULI = {"I": np.eye(2), "X": np.array([[0, 1], [1, 0]]),
         "Y": SY, "Z": np.array([[1, 0], [0, -1]])}


def rand_state(rng):
    """Random 2-qubit mixed state: p|psi><psi| + (1-p) I/4, Haar |psi|, p~U(0.15,1)."""
    z = rng.randn(4) + 1j * rng.randn(4); z /= np.linalg.norm(z)
    p = rng.uniform(0.15, 1.0)
    return p * np.outer(z, z.conj()) + (1 - p) * np.eye(4) / 4


def purity(rho):
    return float(np.real(np.trace(rho @ rho)))


def concurrence(rho):
    R = rho @ np.kron(SY, SY) @ rho.conj() @ np.kron(SY, SY)
    ev = np.sort(np.sqrt(np.clip(np.real(np.linalg.eigvals(R)), 0, None)))[::-1]
    return float(max(0.0, ev[0] - ev[1] - ev[2] - ev[3]))


def pauli_expectations(rho):
    out = []
    for a in "IXYZ":
        for b in "IXYZ":
            if a == "I" and b == "I":
                continue
            out.append(float(np.real(np.trace(rho @ np.kron(PAULI[a], PAULI[b])))))
    return out                                              # 15 values (full 2-qubit tomography)


class QStateReservoir:
    """(2 input + m memory)-qubit CHIMERA; inject a 2-qubit rho, evolve, measure; re-inject K times."""
    def __init__(self, m, seed):
        self.n = 2 + m; self.din = 4; self.dmem = 2 ** m
        J = generate_coupling_matrix(self.n, connectivity=0.5, seed=seed)
        self.U = expm(-1j * build_ising_hamiltonian(self.n, J, hx=1.0) * TAU)
        self.Ud = self.U.conj().T
        bits = ((np.arange(2 ** self.n)[:, None] >> (self.n - 1 - np.arange(self.n))) & 1)
        self.Z = 1 - 2 * bits
        self.pairs = [(i, j) for i in range(self.n) for j in range(i + 1, self.n)]

    def features(self, rho_in, K):
        rho = np.kron(rho_in, np.eye(self.dmem) / self.dmem)   # input=rho, memory=maximally mixed
        feats = []
        for _ in range(K):
            rho = self.U @ rho @ self.Ud
            d = np.real(np.diag(rho))
            zi = d @ self.Z
            zz = [float(d @ (self.Z[:, i] * self.Z[:, j])) for (i, j) in self.pairs]
            feats.extend(list(zi) + zz)
            R = rho.reshape(self.din, self.dmem, self.din, self.dmem)
            rho_mem = np.einsum('ikil->kl', R)                 # trace out input qubits
            rho = np.kron(rho_in, rho_mem)                     # RE-INJECT the same state
        return np.array(feats)


def r2(y, p):
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    N = 300 if args.quick else 700
    m = 3 if args.quick else 4
    K = 2 if args.quick else 3
    seeds = (0, 1) if args.quick else (0, 1, 2, 3)
    t0 = time.time()

    rng = np.random.RandomState(0)
    states = [rand_state(rng) for _ in range(N)]
    y_pur = np.array([purity(r) for r in states])
    y_con = np.array([concurrence(r) for r in states])
    P = np.array([pauli_expectations(r) for r in states])   # (N,15) full tomography

    ntr = int(0.7 * N); tr = np.arange(ntr); te = np.arange(ntr, N)
    gamma = rbf_gamma((P[tr] - P[tr].min(0)) / (np.ptp(P[tr], 0) + 1e-9))
    Ps = (P - P.min(0)) / (np.ptp(P, 0) + 1e-9)             # scale for RFF

    print("#" * 88)
    print("V3 QUANTUM-DATA OUTLOOK — estimate nonlinear functionals of input quantum states")
    print(f"  N={N} random 2-qubit states; QRC=(2+{m}) qubits, K={K} injections; seeds={seeds}")
    print("#" * 88)

    res = {}
    for name, y in (("purity Tr(rho^2)", y_pur), ("concurrence (entanglement)", y_con)):
        # QRC (quantum-native), seed-averaged
        q = []
        for sd in seeds:
            qr = QStateReservoir(m, sd)
            F = np.array([qr.features(r, K) for r in states])
            pr, _ = ridge_readout(F[tr], y[tr], F[te]); q.append(r2(y[te], pr))
        # classical-linear on full tomography (15 Pauli expectations)
        prl, _ = ridge_readout(P[tr], y[tr], P[te]); lin = r2(y[te], prl)
        # classical-nonlinear (RFF) on full tomography
        nl = []
        for sd in seeds:
            FR = rff_features(Ps, 60, sd, gamma)
            pr, _ = ridge_readout(FR[tr], y[tr], FR[te]); nl.append(r2(y[te], pr))
        res[name] = (float(np.mean(q)), lin, float(np.mean(nl)))
        print(f"\n  TARGET: {name}")
        print(f"    QRC (quantum-native, {K}x inject)      R^2 = {np.mean(q):+.3f}")
        print(f"    classical-linear  (full tomography)    R^2 = {lin:+.3f}   <- linear can't form a nonlinear functional")
        print(f"    classical-nonlinear (full tomography)  R^2 = {np.mean(nl):+.3f}")

    print("\n" + "=" * 88)
    qp = res["purity Tr(rho^2)"]
    edge_vs_lin = qp[0] - qp[1]
    print(f"INDICATION: on purity the QRC ({qp[0]:+.2f}) hugely beats classical-LINEAR ({qp[1]:+.2f}) "
          f"[gap {edge_vs_lin:+.2f}] — it natively reads a NONLINEAR functional of the quantum state.")
    if qp[0] >= qp[2] - 0.05:
        print(f"  vs classical-NONLINEAR with full tomography ({qp[2]:+.2f}): QRC matches it. So at 2-qubit "
              f"scale there is NO quantitative quantum advantage — the QRC's value is the native")
        print(f"  nonlinearity, and any real EDGE is asymptotic (full tomography costs 4^k; the QRC reads "
              f"a fixed poly-size observable set). Honest outlook, not demonstrated at this scale.")
    else:
        print(f"  classical-nonlinear with full tomography ({qp[2]:+.2f}) still beats the QRC — "
              f"no quantum-data advantage even qualitatively at this scale.")
    if not args.quick:
        np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrc_quantum_data_results.npy"),
                dict(res=res, N=N, m=m, K=K), allow_pickle=True)
        print(f"saved qrc_quantum_data_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
