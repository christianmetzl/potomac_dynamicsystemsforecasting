"""
dissipative_qrc.py  [V3 — the mechanism test: does ENGINEERED DISSIPATION recover autonomous VPT?]

Our recurrent-QRC study diagnosed WHY the quantum reservoir fails autonomous chaotic rollout:
unitary evolution is norm-preserving (non-dissipative), so it lacks the contraction that gives
classical ESNs their "generalized synchronization" (Ahmed-Tennie-Magri 2025). That diagnosis makes
a FALSIFIABLE prediction: adding engineered dissipation to the reservoir memory should IMPROVE
autonomous VPT, with an optimum at moderate dissipation (too little -> no contraction; too much ->
no memory). This experiment tests exactly that — the panel's "turn the borrowed mechanism into a
demonstrated one".

Setup: the same persistent-state recurrent QRC (recurrent_qrc.py; n=8 = 3 input + 5 memory,
density-matrix exact), now with per-step AMPLITUDE DAMPING (rate gamma) applied to each MEMORY
qubit after the unitary — the "dissipation-as-feature" channel the engine already exposes, used
here as reservoir contraction. Sweep gamma; measure teacher-forced one-step R^2 and autonomous
Lorenz-63 VPT (same protocol/starts as recurrent_qrc.py); compare to the gamma=0 baseline and the
size-matched ESN.

Usage:  python3 dissipative_qrc.py            # gamma sweep, 15 starts, 2 seeds
        python3 dissipative_qrc.py --quick    # coarse sweep, 6 starts, 1 seed
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from recurrent_qrc import RecurrentQRC, matched_esn_rollout
from lorenz_vpt import lorenz, _vpt, LYAP_STEPS

HERE = os.path.dirname(os.path.abspath(__file__))


def _amp_damp(rho, q, n, gamma):
    """Exact amplitude-damping channel on qubit q of an n-qubit density matrix,
    via index slicing (no 2^n x 2^n matmuls): for the qubit's (row i, col j) block
    structure R[a,i,b,j]:  00 += g*11;  01,10 *= sqrt(1-g);  11 *= (1-g)."""
    s = np.sqrt(1 - gamma)
    R = rho.reshape(2 ** q, 2, 2 ** (n - 1 - q), 2 ** q, 2, 2 ** (n - 1 - q))
    out = R.copy()
    out[:, 0, :, :, 0, :] += gamma * R[:, 1, :, :, 1, :]
    out[:, 0, :, :, 1, :] *= s
    out[:, 1, :, :, 0, :] *= s
    out[:, 1, :, :, 1, :] *= (1 - gamma)
    return out.reshape(rho.shape)


class DissipativeRQRC(RecurrentQRC):
    """Recurrent QRC + per-step amplitude damping (rate gamma) on each MEMORY qubit."""

    def __init__(self, n, n_in, seed, gamma):
        super().__init__(n, n_in, seed)
        self.gamma = float(gamma)

    def step(self, u):
        R = self.rho.reshape(self.din, self.dmem, self.din, self.dmem)
        rho_mem = np.einsum('ikil->kl', R)
        self.rho = np.kron(self._phi_in(u), rho_mem)
        self.rho = self.U @ self.rho @ self.Ud
        if self.gamma > 0:
            for q in range(self.n_in, self.n):            # engineered contraction (memory only)
                self.rho = _amp_damp(self.rho, q, self.n, self.gamma)
        d = np.real(np.diag(self.rho))
        zi = d @ self.Z
        zz = [float(d @ (self.Z[:, i] * self.Z[:, j])) for (i, j) in self.pairs]
        return np.concatenate([zi, zz])


def rollout(traj_n, tr, starts, horizon, rms, n, n_in, seed, gamma):
    qr = DissipativeRQRC(n, n_in, seed, gamma)
    qr.reset()
    for t in range(40):
        qr.step(traj_n[t])
    F = np.array([qr.step(traj_n[t]) for t in range(40, tr - 1)])
    Y = traj_n[41:tr]
    nfit = int(0.85 * len(F))
    Fb = np.hstack([F, np.ones((len(F), 1))])
    Wt = np.linalg.solve(Fb[:nfit].T @ Fb[:nfit] + 1e-4 * np.eye(Fb.shape[1]),
                         Fb[:nfit].T @ Y[:nfit])
    pr = Fb[nfit:] @ Wt
    r2 = 1 - np.sum((Y[nfit:] - pr) ** 2) / np.sum((Y[nfit:] - Y[nfit:].mean(0)) ** 2)
    vpts = []
    for s0 in starts:
        qr.reset()
        for t in range(s0 - 60, s0):
            qr.step(traj_n[t])
        true = traj_n[s0:s0 + horizon]
        pred = np.empty((horizon, 3)); cur = traj_n[s0 - 1]
        for h in range(horizon):
            f = qr.step(cur)
            cur = np.hstack([f, 1.0]) @ Wt
            pred[h] = cur
        vpts.append(_vpt(true, pred, rms))
    return float(np.mean(vpts)), float(np.std(vpts)), float(r2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n, n_in = 8, 3
    gammas = [0.0, 0.1, 0.3] if args.quick else [0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5]
    seeds = (0,) if args.quick else (0, 1)
    n_starts = 6 if args.quick else 15
    t0 = time.time()

    traj = lorenz(12000)
    lo, hi = traj.min(0), traj.max(0)
    traj_n = (traj - lo) / (hi - lo)
    tr = int(0.6 * len(traj_n))
    rms = float(np.sqrt(((traj_n - traj_n.mean(0)) ** 2).sum(1).mean()))
    horizon = int(7 * LYAP_STEPS)
    rng = np.random.RandomState(0)
    starts = rng.randint(tr + 100, len(traj_n) - horizon, size=n_starts)
    feat = n + n * (n - 1) // 2

    print("#" * 88)
    print("V3 ENGINEERED DISSIPATION — does memory-qubit damping recover autonomous VPT?")
    print(f"  recurrent n={n} ({n_in} input + {n-n_in} memory); amplitude damping rate gamma "
          f"per step on memory qubits")
    print(f"  gammas={gammas}  starts={n_starts}  seeds={seeds}   "
          f"(pre-registered prediction: inverted-U in gamma)")
    print("#" * 88)
    print(f"  {'gamma':>6}{'VPT (Lyap times)':>18}{'one-step R^2':>14}")
    rows = []
    for g in gammas:
        res = [rollout(traj_n, tr, starts, horizon, rms, n, n_in, sd, g) for sd in seeds]
        v = float(np.mean([r[0] for r in res])); sd_ = float(np.std([r[0] for r in res]))
        r2 = float(np.mean([r[2] for r in res]))
        rows.append(dict(gamma=g, vpt=v, vpt_sd=sd_, r2=r2))
        print(f"  {g:>6.2f}{v:>12.2f} ± {sd_:<4.2f}{r2:>13.3f}", flush=True)

    esn = float(np.mean([matched_esn_rollout(traj_n, tr, starts, horizon, rms, feat, sd)
                         for sd in seeds]))
    base = rows[0]["vpt"]
    best = max(rows, key=lambda r: r["vpt"])
    print(f"\n  size-matched ESN ({feat} nodes): VPT {esn:.2f}")
    print("=" * 88)
    if best["gamma"] > 0 and best["vpt"] > base + 0.05:
        rel = "and MATCHES/EXCEEDS" if best["vpt"] >= esn else "but stays below"
        print(f"VERDICT: dissipation HELPS — gamma={best['gamma']} lifts VPT {base:.2f} -> "
              f"{best['vpt']:.2f} ({rel} the size-matched ESN {esn:.2f}).")
        print("The diagnosed mechanism (non-dissipative unitarity -> no generalized "
              "synchronization) is now DEMONSTRATED, not just argued: engineered contraction "
              "recovers autonomous stability.")
    else:
        print(f"VERDICT: no significant VPT gain from memory damping (best gamma={best['gamma']}: "
              f"{best['vpt']:.2f} vs baseline {base:.2f}) — the mechanism hypothesis is NOT "
              f"confirmed by this channel (reported honestly; other dissipation designs remain open).")
    if not args.quick:
        np.save(os.path.join(HERE, "dissipative_qrc_results.npy"),
                dict(rows=rows, esn_matched=esn, n=n, n_in=n_in, starts=n_starts,
                     seeds=list(seeds)), allow_pickle=True)
        print(f"saved dissipative_qrc_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
