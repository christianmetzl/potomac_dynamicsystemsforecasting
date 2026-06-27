"""
Multi-Scale CHIMERA Forecaster — combines K delay-embedding QRC reservoirs at
geometrically separated evolution times. Tests CHIMERA Innovation 1 (multi-scale)
and Innovation 2 (feedback) on autonomous chaotic forecasting.

Team EIGENNEXUS | GIC 2026 — Phase 2
"""
import numpy as np
import time
from delay_qrc import DelayEmbeddingQRC
from benchmarks import lorenz_system, normalize_data
from compute_vpt_util import compute_vpt


class MultiScaleCHIMERA:
    """Bank of delay-embedding QRC reservoirs at different tau, fused readout."""
    def __init__(self, n_qubits=10, taus=(2.0, 3.0), hamiltonian='ising',
                 hx=1.0, connectivity=0.5, seed=0,
                 noise=None, noise_rate=0.0, feedback=False, a_fb=1.0):
        self.reservoirs = [
            DelayEmbeddingQRC(n_qubits=n_qubits, tau=t, hamiltonian=hamiltonian,
                              hx=hx, connectivity=connectivity, seed=seed+i,
                              noise=noise, noise_rate=noise_rate,
                              feedback=feedback, a_fb=a_fb)
            for i, t in enumerate(taus)
        ]
        self.taus = taus

    def _all_features(self, emb):
        return np.concatenate([r._step_features(emb) for r in self.reservoirs])

    def _reset_feedback(self):
        for r in self.reservoirs:
            r._prev_z = np.zeros(r.n)

    def train(self, data, k=3, ridge=1e-5):
        self.k = k; self.d = data.shape[1]
        T = len(data)
        X, Y = [], []
        for t in range(k-1, T-1):
            X.append(data[t-k+1:t+1][::-1].flatten()); Y.append(data[t+1])
        X, Y = np.array(X), np.array(Y)
        self._reset_feedback()
        feats = np.array([self._all_features(x) for x in X])
        F = np.hstack([feats, X, np.ones((len(feats), 1))])
        self.W_out = np.linalg.solve(F.T @ F + ridge*np.eye(F.shape[1]), F.T @ Y)
        pred = F @ self.W_out
        return 1 - np.sum((Y-pred)**2)/np.sum((Y-Y.mean(0))**2)

    def forecast(self, warmup_data, n_steps):
        k = self.k
        self._reset_feedback()
        for t in range(k-1, len(warmup_data)):
            emb = warmup_data[t-k+1:t+1][::-1].flatten()
            self._all_features(emb)
        window = list(warmup_data[-k:])
        preds = []
        for _ in range(n_steps):
            emb = np.array(window[-k:])[::-1].flatten()
            f = self._all_features(emb)
            nxt = np.hstack([f, emb, [1.0]]) @ self.W_out
            preds.append(nxt); window.append(nxt)
        return np.array(preds)


if __name__ == "__main__":
    np.random.seed(0)
    raw = lorenz_system(T=5500, dt=0.02, warmup=2000)
    data, _, _ = normalize_data(raw)
    train = data[:4000]
    WARM, FS = 50, 400
    origins = [4100, 4400, 4700, 5000]

    def eval_model(m, k=3, ridge=1e-5):
        tr2 = m.train(train, k=k, ridge=ridge)
        vpts = []
        for o in origins:
            pred = m.forecast(data[o-WARM:o], FS)
            v, ns, _ = compute_vpt(data[o:o+FS], pred); vpts.append(v)
        return tr2, np.mean(vpts), np.std(vpts)

    print("CHIMERA Multi-Scale ablation (10 qubits/reservoir):")
    print("-" * 60)

    configs = [
        ("Single tau=2.0", dict(taus=(2.0,))),
        ("Single tau=3.0", dict(taus=(3.0,))),
        ("Multi tau=(2,3)", dict(taus=(2.0, 3.0))),
        ("Multi tau=(1,2,4)", dict(taus=(1.0, 2.0, 4.0))),
        ("Multi tau=(2,4,8)", dict(taus=(2.0, 4.0, 8.0))),
    ]
    for name, cfg in configs:
        t0 = time.time()
        m = MultiScaleCHIMERA(n_qubits=10, hamiltonian='ising', hx=1.0,
                              connectivity=0.5, seed=0, **cfg)
        tr2, vpt_m, vpt_s = eval_model(m)
        print(f"  {name:<20} VPT={vpt_m:.2f}±{vpt_s:.2f} Lyap  (tr_R2={tr2:.4f}, {time.time()-t0:.0f}s)")
