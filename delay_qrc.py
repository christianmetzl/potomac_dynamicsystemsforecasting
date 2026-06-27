"""
Delay-Embedding QRC Forecaster for autonomous chaotic prediction.
Encodes a delay-embedding vector (last k steps) across the qubits, so
trajectory history enters the quantum feature map explicitly. This is the
standard QRC approach for chaotic forecasting and gives the reservoir the
memory that a recurrence-free design otherwise lacks.

Team EIGENNEXUS | GIC 2026 — Phase 2
"""
import numpy as np
import time
from qrc_engine import (
    QuantumReservoir, build_ising_hamiltonian, build_heisenberg_hamiltonian,
    generate_coupling_matrix, time_evolve, apply_single_qubit_gate, Ry, Rz,
    measure_full_features, state_to_density, apply_amplitude_damping,
    apply_depolarizing, measure_features_density
)
from classical_baselines import EchoStateNetwork
from benchmarks import lorenz_system, normalize_data
from compute_vpt_util import compute_vpt


class DelayEmbeddingQRC:
    """
    QRC that encodes a delay embedding across input qubits.

    Architecture:
      - Input: delay embedding x_t = [s(t), s(t-1), ..., s(t-k+1)] flattened (k*d values)
      - Encode each value into one qubit via R_Y(pi * value)
      - Optional feedback: previous measurement re-injected via R_Z
      - Evolve under fixed Hamiltonian U = exp(-i H tau)
      - Optional amplitude-damping noise channel
      - Measure single + pairwise Pauli-Z -> feature vector
      - Linear readout -> prediction of s(t+1)
    """
    def __init__(self, n_qubits=10, tau=4.0, hamiltonian='ising',
                 hx=1.0, delta=0.8, connectivity=0.5, seed=0,
                 noise=None, noise_rate=0.0, feedback=False, a_fb=1.0):
        self.n = n_qubits
        self.tau = tau
        self.seed = seed
        self.noise = noise
        self.noise_rate = noise_rate
        self.feedback = feedback
        self.a_fb = a_fb
        J = generate_coupling_matrix(n_qubits, connectivity, seed=seed)
        if hamiltonian == 'ising':
            self.H = build_ising_hamiltonian(n_qubits, J, hx=hx)
        else:
            self.H = build_heisenberg_hamiltonian(n_qubits, J, delta=delta, h=hx)
        self.U = time_evolve(self.H, tau)
        self.feature_dim = n_qubits + n_qubits*(n_qubits-1)//2
        self.W_out = None
        self._prev_z = np.zeros(n_qubits)

    def _step_features(self, embedding):
        """Re-prepare state from embedding, evolve, measure features."""
        # state |0...0>
        psi = np.zeros(2**self.n, dtype=complex); psi[0] = 1.0
        # encode embedding values into qubits (one per qubit, up to n)
        m = min(len(embedding), self.n)
        for q in range(m):
            angle = np.pi * np.clip(embedding[q], 0, 1)
            psi = apply_single_qubit_gate(psi, Ry(angle), q, self.n)
        # feedback injection
        if self.feedback and self.a_fb > 0:
            for q in range(self.n):
                ang = self.a_fb * np.tanh(self._prev_z[q])
                psi = apply_single_qubit_gate(psi, Rz(ang), q, self.n)
        # evolve
        psi = self.U @ psi
        # measure
        if self.noise and self.noise_rate > 0:
            rho = state_to_density(psi)
            if self.noise == 'amplitude_damping':
                rho = apply_amplitude_damping(rho, self.noise_rate, self.n)
            elif self.noise == 'depolarizing':
                rho = apply_depolarizing(rho, self.noise_rate, self.n)
            feats = measure_features_density(rho, self.n)
        else:
            feats = measure_full_features(psi, self.n)
        self._prev_z = feats[:self.n]
        return feats

    def _build_embeddings(self, data, k):
        """Construct delay embeddings and next-step targets."""
        T, d = data.shape
        X, Y = [], []
        for t in range(k - 1, T - 1):
            emb = data[t-k+1:t+1][::-1].flatten()  # most recent first
            X.append(emb)
            Y.append(data[t+1])
        return np.array(X), np.array(Y)

    def train(self, data, k=3, ridge=1e-7, hybrid=True):
        self.k = k
        self.d = data.shape[1]
        self.hybrid = hybrid
        X, Y = self._build_embeddings(data, k)
        self._prev_z = np.zeros(self.n)
        feats = np.array([self._step_features(x) for x in X])
        if hybrid:
            # concatenate quantum features with raw embedding (linear lift)
            F = np.hstack([feats, X, np.ones((len(feats), 1))])
        else:
            F = np.hstack([feats, np.ones((len(feats), 1))])
        self.W_out = np.linalg.solve(F.T @ F + ridge*np.eye(F.shape[1]), F.T @ Y)
        pred = F @ self.W_out
        return 1 - np.sum((Y-pred)**2)/np.sum((Y-Y.mean(0))**2)

    def forecast(self, warmup_data, n_steps):
        """Autonomous rollout. warmup_data provides the initial k-window and
        synchronizes the feedback state."""
        k = self.k
        self._prev_z = np.zeros(self.n)
        for t in range(k-1, len(warmup_data)):
            emb = warmup_data[t-k+1:t+1][::-1].flatten()
            self._step_features(emb)
        window = list(warmup_data[-k:])
        preds = []
        for _ in range(n_steps):
            emb = np.array(window[-k:])[::-1].flatten()
            f = self._step_features(emb)
            if self.hybrid:
                nxt = np.hstack([f, emb, [1.0]]) @ self.W_out
            else:
                nxt = np.hstack([f, [1.0]]) @ self.W_out
            preds.append(nxt)
            window.append(nxt)
        return np.array(preds)


def run_quick_test():
    np.random.seed(0)
    raw = lorenz_system(T=5000, dt=0.02, warmup=2000)
    data, _, _ = normalize_data(raw)
    train = data[:3500]
    WARM, FS = 50, 400
    origins = [3600, 3900, 4200, 4500]

    print("Testing Delay-Embedding QRC (10 qubits) autonomous forecasting:")
    for k in [3, 4]:
        for tau in [2.0, 4.0, 8.0]:
            q = DelayEmbeddingQRC(n_qubits=10, tau=tau, hamiltonian='ising',
                                  hx=1.0, connectivity=0.5, seed=0)
            t0 = time.time()
            tr2 = q.train(train, k=k, ridge=1e-7)
            vpts = []
            for o in origins:
                pred = q.forecast(data[o-WARM:o], FS)
                vpt, ns, _ = compute_vpt(data[o:o+FS], pred)
                vpts.append(vpt)
            print(f"  k={k} tau={tau}: train_R2={tr2:.4f} "
                  f"VPT={np.mean(vpts):.2f}±{np.std(vpts):.2f} Lyap ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    run_quick_test()
