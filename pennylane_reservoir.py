"""
pennylane_reservoir.py - CHIMERA-QRC reservoir as a hardware-deployable quantum circuit.
================================================================================
This expresses the EXACT Phase-2/Phase-3 reservoir of qrc_engine.py as a PennyLane
QNode, so the same model can run on:
  * default.qubit (exact statevector) - reproduces qrc_engine to ~1e-12,
  * default.qubit with shots=K        - finite-shot (hardware-realistic) features,
  * any qBraid-dispatched QPU          - IonQ / QuEra / IBM via PennyLane plugins,
with a Trotterized evolution for gate-based hardware.

Model (identical to qrc_engine): per qubit RY(pi*clip(x,0,1)); evolve under the
transverse-field Ising H = sum_{i<j} J_ij Z_iZ_j + hx sum_i X_i for time tau; read
out <Z_i> and <Z_iZ_j> (i<j) -> n + n(n-1)/2 features, in the SAME order.

Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
from __future__ import annotations
import numpy as np
import pennylane as qml

from qrc_engine import generate_coupling_matrix


def ising_hamiltonian(n_qubits, J, hx=1.0):
    """qml.Hamiltonian for H = sum_{i<j} J_ij Z_iZ_j + hx sum_i X_i (matches qrc_engine)."""
    coeffs, ops = [], []
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            if abs(J[i, j]) > 1e-12:
                coeffs.append(float(J[i, j])); ops.append(qml.PauliZ(i) @ qml.PauliZ(j))
    for i in range(n_qubits):
        coeffs.append(float(hx)); ops.append(qml.PauliX(i))
    return qml.Hamiltonian(coeffs, ops)


def feature_observables(n_qubits):
    """[Z_0..Z_{n-1}, Z_iZ_j for i<j] - identical layout to qrc_engine.measure_full_features."""
    obs = [qml.PauliZ(i) for i in range(n_qubits)]
    obs += [qml.PauliZ(i) @ qml.PauliZ(j)
            for i in range(n_qubits) for j in range(i + 1, n_qubits)]
    return obs


def make_reservoir_qnode(n_qubits, J, tau, hx=1.0, shots=None, trotter_steps=None,
                         device="default.qubit", diff_method=None):
    """Build the reservoir QNode. trotter_steps=None -> exact exp(-iH tau) (simulator);
    an int -> Suzuki-Trotter evolution (gate-based hardware). shots=None -> analytic."""
    H = ising_hamiltonian(n_qubits, J, hx)
    obs = feature_observables(n_qubits)
    dev = qml.device(device, wires=n_qubits)

    @qml.qnode(dev, diff_method=diff_method)
    def circuit(x):
        for q in range(n_qubits):
            qml.RY(np.pi * x[q], wires=q)
        if trotter_steps is None:
            qml.evolve(H, tau)                              # exact exp(-iH tau)
        else:
            qml.TrotterProduct(H, time=tau, n=trotter_steps, order=2)
        return [qml.expval(o) for o in obs]

    if shots is not None:
        circuit = qml.set_shots(circuit, shots=shots)      # finite-shot (hardware-realistic)
    return circuit


def reservoir_features(X, n_qubits, jseed, tau, hx=1.0, shots=None, trotter_steps=None,
                       connectivity=0.5):
    """Drop-in analogue of scaling_sweep._reservoir_features: features for each row of X.
    Couplings generated identically to qrc_engine (generate_coupling_matrix(n, conn, seed))."""
    J = generate_coupling_matrix(n_qubits, connectivity, seed=jseed)
    circ = make_reservoir_qnode(n_qubits, J, tau, hx, shots, trotter_steps)
    out = np.empty((len(X), n_qubits + n_qubits * (n_qubits - 1) // 2))
    for i, x in enumerate(X):
        out[i] = np.array(circ(np.clip(x[:n_qubits], 0.0, 1.0)))
    return out


# ============================ self-test vs qrc_engine =========================
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[6, 8])
    ap.add_argument("--shots", type=int, default=20000)
    args = ap.parse_args()

    from qrc_engine import (build_ising_hamiltonian, apply_single_qubit_gate, Ry,
                            measure_full_features)
    from scipy.linalg import expm

    def dense(x, n, J, tau):
        H = build_ising_hamiltonian(n, J, hx=1.0); U = expm(-1j * H * tau)
        psi = np.zeros(2 ** n, dtype=complex); psi[0] = 1.0
        for q in range(n):
            psi = apply_single_qubit_gate(psi, Ry(np.pi * np.clip(x[q], 0, 1)), q, n)
        return measure_full_features(U @ psi, n)

    rng = np.random.RandomState(0)
    print("PennyLane reservoir self-test vs qrc_engine (exact statevector):")
    ok = True
    for n in args.ns:
        J = generate_coupling_matrix(n, 0.5, seed=7)
        circ = make_reservoir_qnode(n, J, 2.0)
        e_exact = e_trot = 0.0
        circ_t = make_reservoir_qnode(n, J, 2.0, trotter_steps=40)
        for _ in range(4):
            x = rng.rand(n)
            fd = dense(x, n, J, 2.0)
            fp = np.array(circ(np.clip(x, 0, 1)))
            ft = np.array(circ_t(np.clip(x, 0, 1)))
            e_exact = max(e_exact, float(np.max(np.abs(fd - fp))))
            e_trot = max(e_trot, float(np.max(np.abs(fd - ft))))
        # finite-shot sanity (one input)
        circ_s = make_reservoir_qnode(n, J, 2.0, shots=args.shots)
        x = rng.rand(n); fd = dense(x, n, J, 2.0)
        fs = np.array(circ_s(np.clip(x, 0, 1)))
        e_shot = float(np.max(np.abs(fd - fs)))
        good = e_exact < 1e-9 and e_trot < 5e-3
        ok = ok and good
        print(f"  n={n:2d}  exact|err|={e_exact:.2e}  trot40|err|={e_trot:.2e}  "
              f"shot{args.shots}|err|={e_shot:.2e}   {'OK' if good else 'FAIL'}")
    print("SELF-TEST", "PASSED" if ok else "FAILED",
          "- PennyLane circuit reproduces the exact reservoir; Trotter + shots behave.")
    raise SystemExit(0 if ok else 1)
