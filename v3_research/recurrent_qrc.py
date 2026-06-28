"""
recurrent_qrc.py  [V3 — the recurrent CHIMERA, the architecturally-correct QRC for chaotic VPT]

The static delay-window QRC (V1/V2/v3_weather) re-encodes a window each step and keeps NO quantum
state between steps — wrong for autonomous chaotic rollout, where the recurrent ESN dominates
(lorenz_vpt.py: ESN 2.42 vs static CHIMERA 0.49 Lyapunov times). The QRC literature (Fujii-Nakajima
2017; Kornjaca 2024; Li 2025) instead uses a PERSISTENT quantum state with distinct INPUT and
MEMORY qubits: each step resets only the input qubits to encode u_t, keeps the memory qubits, and
evolves the whole system — so the quantum state itself is the reservoir memory (true recurrence).

This builds that recurrent QRC (density-matrix, exact) and runs the FAIR recurrent-vs-recurrent VPT
test on Lorenz-63: recurrent-CHIMERA vs the recurrent ESN. Honest by construction; no V1 file
touched. This is the one place a quantum reservoir is most likely to be at least *competitive*.

Architecture: n qubits = n_in input (encode the 3-D Lorenz state) + (n-n_in) memory. Step(u):
  rho_mem = Tr_input(rho);  rho = |phi(u)><phi(u)|_input (x) rho_mem;  rho = U rho U^dagger;
  features = [<Z_i>, <Z_iZ_j>]  (all Z-diagonal -> read from diag(rho)).
Trained teacher-forced (ridge: features -> next state), then autonomous generative rollout.

Usage:  python3 recurrent_qrc.py            # n=8 (3 input + 5 memory), 20 starts, 2 seeds
        python3 recurrent_qrc.py --quick    # n=7, 8 starts, 1 seed
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.linalg import expm
from qrc_engine import generate_coupling_matrix, build_ising_hamiltonian
from lorenz_vpt import lorenz, _vpt, esn_rollout, LYAP_STEPS, DT, THRESH

TAU = 2.0


class RecurrentQRC:
    """Persistent-state quantum reservoir with input-qubit reset (Fujii-Nakajima / Kornjaca)."""
    def __init__(self, n, n_in, seed):
        self.n, self.n_in, self.n_mem = n, n_in, n - n_in
        self.din, self.dmem = 2 ** n_in, 2 ** (n - n_in)
        J = generate_coupling_matrix(n, connectivity=0.5, seed=seed)
        self.U = expm(-1j * build_ising_hamiltonian(n, J, hx=1.0) * TAU)
        self.Ud = self.U.conj().T
        # Z-diagonals per qubit (qubit 0 = most significant), and pair products
        bits = ((np.arange(2 ** n)[:, None] >> (n - 1 - np.arange(n))) & 1)
        self.Z = 1 - 2 * bits                                   # (2^n, n) of +-1
        self.pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        self.reset()

    def reset(self):
        self.rho = np.zeros((2 ** self.n, 2 ** self.n), complex)
        self.rho[0, 0] = 1.0

    def _phi_in(self, u):
        """input-qubit product state |phi(u)>; one qubit per input dim, RY(pi*u) on |0>."""
        v = np.array([1.0])
        for q in range(self.n_in):
            a = np.pi * float(np.clip(u[q % len(u)], 0, 1)) / 2.0
            v = np.kron(v, np.array([np.cos(a), np.sin(a)]))
        return np.outer(v, v.conj())

    def step(self, u):
        R = self.rho.reshape(self.din, self.dmem, self.din, self.dmem)
        rho_mem = np.einsum('ikil->kl', R)                     # partial trace over input qubits
        self.rho = np.kron(self._phi_in(u), rho_mem)           # reset input qubits, keep memory
        self.rho = self.U @ self.rho @ self.Ud                 # evolve whole system
        d = np.real(np.diag(self.rho))                          # Z-diagonal observables
        zi = d @ self.Z                                        # <Z_i>
        zz = [float(d @ (self.Z[:, i] * self.Z[:, j])) for (i, j) in self.pairs]
        return np.concatenate([zi, zz])


def rqrc_rollout(traj_n, tr, starts, horizon, rms, n, n_in, seed):
    qr = RecurrentQRC(n, n_in, seed)
    # teacher-forced training: collect features over train, fit ridge features->next state
    qr.reset()
    for t in range(40):                                        # warm-up
        qr.step(traj_n[t])
    F = []
    for t in range(40, tr - 1):
        F.append(qr.step(traj_n[t]))
    F = np.array(F); Y = traj_n[41:tr]
    nfit = int(0.85 * len(F))
    Fb = np.hstack([F, np.ones((len(F), 1))])
    Wt = np.linalg.solve(Fb[:nfit].T @ Fb[:nfit] + 1e-4 * np.eye(Fb.shape[1]), Fb[:nfit].T @ Y[:nfit])
    # one-step diagnostic R^2 on the held-out train tail (is the reservoir learning at all?)
    pr = Fb[nfit:] @ Wt
    r2 = 1 - np.sum((Y[nfit:] - pr) ** 2) / np.sum((Y[nfit:] - Y[nfit:].mean(0)) ** 2)
    vpts = []; vpts_r2 = float(r2)
    for s0 in starts:
        qr.reset()
        for t in range(s0 - 60, s0):                           # warm up on true states
            qr.step(traj_n[t])
        true = traj_n[s0:s0 + horizon]; pred = np.empty((horizon, 3)); cur = traj_n[s0 - 1]
        for h in range(horizon):
            f = qr.step(cur)
            cur = np.hstack([f, 1.0]) @ Wt
            pred[h] = cur
        vpts.append(_vpt(true, pred, rms))
    return float(np.mean(vpts)), float(np.std(vpts)), vpts_r2


def matched_esn_rollout(traj_n, tr, starts, horizon, rms, n_res, seed):
    """ESN VPT with a SPECIFIED reservoir size (for a size-matched fair comparison)."""
    from classical_baselines import EchoStateNetwork
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=0.95, leaking_rate=0.3,
                           input_scaling=1.0, connectivity=0.2, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(3); esn.reset()
    S = np.array([esn.step(traj_n[t]) for t in range(tr - 1)])
    Fb = np.hstack([S, np.ones((tr - 1, 1))])
    Wt = np.linalg.solve(Fb.T @ Fb + 1e-6 * np.eye(Fb.shape[1]), Fb.T @ traj_n[1:tr])
    vpts = []
    for s0 in starts:
        esn.reset()
        for t in range(s0 - 60, s0):
            esn.step(traj_n[t])
        true = traj_n[s0:s0 + horizon]; pred = np.empty((horizon, 3)); cur = traj_n[s0 - 1]
        for h in range(horizon):
            st = esn.step(cur); cur = np.hstack([st, 1.0]) @ Wt; pred[h] = cur
        vpts.append(_vpt(true, pred, rms))
    return float(np.mean(vpts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n = 7 if args.quick else 8
    n_in = 3
    seeds = (0,) if args.quick else (0, 1)
    n_starts = 8 if args.quick else 20
    t0 = time.time()

    traj = lorenz(12000)
    lo, hi = traj.min(0), traj.max(0); traj_n = (traj - lo) / (hi - lo)
    tr = int(0.6 * len(traj_n))
    rms = float(np.sqrt(((traj_n - traj_n.mean(0)) ** 2).sum(1).mean()))
    horizon = int(7 * LYAP_STEPS)
    rng = np.random.RandomState(0)
    starts = rng.randint(tr + 100, len(traj_n) - horizon, size=n_starts)

    print("#" * 88)
    print("V3 RECURRENT QRC vs ESN — fair recurrent-vs-recurrent Lorenz-63 VPT (Lyapunov times)")
    print(f"  recurrent-CHIMERA: n={n} ({n_in} input + {n-n_in} memory), density-matrix exact; "
          f"{n_starts} starts, seeds={seeds}")
    print("#" * 88)

    feat = n + n * (n - 1) // 2
    rq = [rqrc_rollout(traj_n, tr, starts, horizon, rms, n, n_in, sd) for sd in seeds]
    rq_m = float(np.mean([x[0] for x in rq])); rq_r2 = float(np.mean([x[2] for x in rq]))
    esM = float(np.mean([matched_esn_rollout(traj_n, tr, starts, horizon, rms, feat, sd) for sd in seeds]))
    esS = float(np.mean([esn_rollout(traj_n, tr, starts, horizon, rms, sd)[0] for sd in seeds]))

    print(f"\n  recurrent-CHIMERA one-step train R^2 = {rq_r2:.3f} (sanity: is it learning?)")
    print(f"\n  {'model':<28}{'VPT (Lyapunov times)':>22}")
    print(f"  {'Recurrent-CHIMERA (n='+str(n)+')':<28}{rq_m:>14.2f} ± {np.std([x[0] for x in rq]):.2f}")
    print(f"  {'ESN, size-matched ('+str(feat)+' nodes)':<28}{esM:>14.2f}")
    print(f"  {'ESN, strong (300 nodes)':<28}{esS:>14.2f}")
    print("  (context, static delay-window: CHIMERA 0.49, RFF 1.18 — from lorenz_vpt.py)")
    print("\n" + "=" * 88)
    fair = "MATCHES/EXCEEDS" if rq_m >= esM else "is below"
    print(f"FAIR test (size-matched, both recurrent, ~{feat} readout dims): recurrent-CHIMERA "
          f"({rq_m:.2f}) {fair} the size-matched ESN ({esM:.2f}).")
    if rq_m >= esM:
        print("  -> at matched size the recurrent quantum reservoir is COMPETITIVE on chaotic VPT.")
    else:
        print("  -> no quantum advantage on VPT even in the fair recurrent, size-matched paradigm.")
    print(f"NOTE: the strong 300-node ESN ({esS:.2f}) far exceeds any n<=8 reservoir — at simulable "
          f"scale the quantum memory (few qubits) is tiny vs a large classical reservoir; a genuine")
    print(f"QRC VPT edge, if it exists, needs the 100+ qubit regime (Kornjaca 2024) beyond simulation.")
    if not args.quick:
        np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recurrent_qrc_results.npy"),
                dict(rqrc=rq_m, rqrc_r2=rq_r2, esn_matched=esM, esn_strong=esS, n=n, n_in=n_in, feat=feat),
                allow_pickle=True)
        print(f"saved recurrent_qrc_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
