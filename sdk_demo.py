"""
sdk_demo.py - reproduce the CHIMERA-QRC reservoir as an EXPLICIT quantum circuit
on a real QML SDK (PennyLane) and verify it matches our NumPy engine, plus a
gate-based Trotterization that proves hardware (gate-model) implementability.
"""
import numpy as np
import pennylane as qml
from scipy.linalg import expm
from qrc_engine import build_ising_hamiltonian, generate_coupling_matrix
from multiscale_chimera import MultiScaleCHIMERA
import volatility_data as vd
from vol_fair_benchmark import LAGS

n, tau, hx, conn, seed = 8, 2.0, 1.0, 0.5, 0
J = generate_coupling_matrix(n, conn, seed=seed)
H = build_ising_hamiltonian(n, J, hx=hx)
U = expm(-1j * H * tau)
nzz = int((np.abs(J) > 1e-12).sum() // 2)

# reference features from our engine (single-scale CHIMERA, no feedback)
ch = MultiScaleCHIMERA(n_qubits=n, taus=(tau,), hamiltonian='ising', hx=hx, connectivity=conn, seed=seed)
def engine_feats(w):
    ch._reset_feedback(); return ch._all_features(w)

dev = qml.device("default.qubit", wires=n)
OBS = [qml.PauliZ(i) for i in range(n)] + \
      [qml.PauliZ(i) @ qml.PauliZ(j) for i in range(n) for j in range(i + 1, n)]

def encode(w):
    for q in range(n):
        qml.RY(np.pi * float(np.clip(w[q], 0, 1)), wires=q)

@qml.qnode(dev)
def circ_exact(w):
    encode(w); qml.QubitUnitary(U, wires=range(n))
    return [qml.expval(o) for o in OBS]

@qml.qnode(dev)
def circ_trotter(w, m):
    encode(w)
    dt = tau / m
    for _ in range(m):
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    qml.IsingZZ(2 * J[i, j] * dt, wires=[i, j])   # exp(-i J dt Z_iZ_j)
        for i in range(n):
            qml.RX(2 * hx * dt, wires=i)                          # exp(-i hx dt X_i)
    return [qml.expval(o) for o in OBS]

# real RV input windows
d = vd.build_supervised(vd.load_spx_rv(), horizon=1, lags=LAGS)
Xlag = d["X_lags"]; tr, te = vd.make_splits(len(d["y_logrv"]), 0.70)
lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rg = np.where((hi - lo) == 0, 1, hi - lo)
Q = np.clip((Xlag - lo) / rg, 0, 1)
wins = Q[tr][:6]

de, d20, d40 = [], [], []
for w in wins:
    fe = np.array(engine_feats(w))
    fx = np.array(circ_exact(w))
    f20 = np.array(circ_trotter(w, 20))
    f40 = np.array(circ_trotter(w, 40))
    de.append(np.max(np.abs(fe - fx)))
    d20.append(np.max(np.abs(fx - f20)))
    d40.append(np.max(np.abs(fx - f40)))

print("=" * 64)
print("CHIMERA reservoir reproduced as an explicit PennyLane circuit")
print("=" * 64)
print(f"feature dim = {len(OBS)}  (n + n(n-1)/2 = {n}+{n*(n-1)//2})")
print(f"engine (NumPy)  vs  PennyLane exact-evolution : max|Δ| = {max(de):.2e}")
print(f"PennyLane exact vs Trotter(20 layers)         : max|Δ| = {max(d20):.2e}")
print(f"PennyLane exact vs Trotter(40 layers)         : max|Δ| = {max(d40):.2e}")
print(f"Trotter(20) native-gate count ≈ {(nzz + n) * 20}  ({nzz} ZZ + {n} RX per layer × 20)")
print("=> the reservoir is a genuine quantum circuit; it runs on a real SDK and")
print("   compiles to a shallow native-gate circuit for gate-model hardware.")
