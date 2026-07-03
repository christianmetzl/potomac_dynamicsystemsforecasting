"""
Unit Tests for CHIMERA-QRC Core Engine
=======================================
Verifies quantum mechanical correctness of all components.

Team EIGENNEXUS | GIC 2026
"""

import numpy as np
import sys

from qrc_engine import (
    I2, X, Y, Z, Ry, Rz, tensor_op, two_qubit_op,
    build_ising_hamiltonian, build_heisenberg_hamiltonian,
    time_evolve, encode_input, measure_pauli_z, measure_full_features,
    state_to_density, apply_amplitude_damping, apply_depolarizing,
    measure_features_density, QuantumReservoir, MultiScaleQRC,
    generate_coupling_matrix
)


def assert_close(a, b, tol=1e-10, msg=""):
    """Assert two values are close within tolerance."""
    diff = np.max(np.abs(np.array(a) - np.array(b)))
    assert diff < tol, f"FAILED {msg}: diff={diff:.2e} > tol={tol:.2e}"


passed = 0
failed = 0


def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1


# ============================================================
# PAULI ALGEBRA TESTS
# ============================================================

def test_pauli_algebra():
    """Verify Pauli matrices satisfy σ_i² = I, σ_i σ_j = iε_{ijk} σ_k."""
    assert_close(X @ X, I2, msg="X² ≠ I")
    assert_close(Y @ Y, I2, msg="Y² ≠ I")
    assert_close(Z @ Z, I2, msg="Z² ≠ I")
    assert_close(X @ Y, 1j * Z, msg="XY ≠ iZ")
    assert_close(Y @ Z, 1j * X, msg="YZ ≠ iX")
    assert_close(Z @ X, 1j * Y, msg="ZX ≠ iY")

def test_pauli_trace():
    """Pauli matrices are traceless."""
    assert_close(np.trace(X), 0, msg="Tr(X) ≠ 0")
    assert_close(np.trace(Y), 0, msg="Tr(Y) ≠ 0")
    assert_close(np.trace(Z), 0, msg="Tr(Z) ≠ 0")

def test_pauli_hermitian():
    """Pauli matrices are Hermitian."""
    assert_close(X, X.conj().T, msg="X not Hermitian")
    assert_close(Y, Y.conj().T, msg="Y not Hermitian")
    assert_close(Z, Z.conj().T, msg="Z not Hermitian")


# ============================================================
# ROTATION GATE TESTS
# ============================================================

def test_ry_zero():
    """R_Y(0) = I."""
    assert_close(Ry(0), I2, msg="R_Y(0) ≠ I")

def test_ry_pi():
    """R_Y(π) maps |0⟩ → |1⟩."""
    state = np.array([1, 0], dtype=complex)
    result = Ry(np.pi) @ state
    expected = np.array([0, 1], dtype=complex)
    assert_close(np.abs(result), np.abs(expected), tol=1e-10, msg="R_Y(π)|0⟩ ≠ |1⟩")

def test_ry_half_pi():
    """R_Y(π/2)|0⟩ = (|0⟩ + |1⟩)/√2 → ⟨Z⟩ = 0."""
    state = Ry(np.pi / 2) @ np.array([1, 0], dtype=complex)
    z_exp = np.real(state.conj() @ Z @ state)
    assert_close(z_exp, 0, tol=1e-10, msg="⟨Z⟩ ≠ 0 for R_Y(π/2)|0⟩")

def test_rz_unitary():
    """R_Z(θ) is unitary for arbitrary θ."""
    for theta in [0, np.pi/4, np.pi, 2*np.pi, 3.7]:
        U = Rz(theta)
        assert_close(U @ U.conj().T, I2, tol=1e-10, msg=f"R_Z({theta}) not unitary")


# ============================================================
# TENSOR PRODUCT TESTS
# ============================================================

def test_tensor_identity():
    """Tensor product of identities = identity."""
    I4 = tensor_op(I2, 0, 2)
    assert_close(I4, np.eye(4), msg="I⊗I ≠ I_4")

def test_tensor_z_on_first():
    """Z⊗I on |00⟩ gives eigenvalue +1."""
    ZI = tensor_op(Z, 0, 2)
    state = np.array([1, 0, 0, 0], dtype=complex)  # |00⟩
    assert_close(state.conj() @ ZI @ state, 1.0, msg="⟨00|Z⊗I|00⟩ ≠ 1")

def test_tensor_z_on_second():
    """I⊗Z on |01⟩ gives eigenvalue -1."""
    IZ = tensor_op(Z, 1, 2)
    state = np.array([0, 1, 0, 0], dtype=complex)  # |01⟩
    assert_close(state.conj() @ IZ @ state, -1.0, msg="⟨01|I⊗Z|01⟩ ≠ -1")


# ============================================================
# HAMILTONIAN TESTS
# ============================================================

def test_hamiltonian_hermitian():
    """Hamiltonians must be Hermitian."""
    J = generate_coupling_matrix(4, connectivity=0.5, seed=42)
    H_ising = build_ising_hamiltonian(4, J, hx=1.0)
    H_heis = build_heisenberg_hamiltonian(4, J, delta=0.8)
    assert_close(H_ising, H_ising.conj().T, tol=1e-12, msg="Ising H not Hermitian")
    assert_close(H_heis, H_heis.conj().T, tol=1e-12, msg="Heisenberg H not Hermitian")

def test_evolution_unitary():
    """Time evolution operator must be unitary."""
    J = generate_coupling_matrix(3, seed=42)
    H = build_ising_hamiltonian(3, J)
    U = time_evolve(H, tau=2.0)
    dim = 2**3
    assert_close(U @ U.conj().T, np.eye(dim), tol=1e-10, msg="U not unitary")


# ============================================================
# MEASUREMENT TESTS
# ============================================================

def test_measure_z_ground_state():
    """All ⟨Z_i⟩ = +1 for |0...0⟩ state."""
    n = 3
    state = np.zeros(2**n, dtype=complex)
    state[0] = 1.0
    z_vals = measure_pauli_z(state, n)
    assert_close(z_vals, np.ones(n), tol=1e-10, msg="⟨Z⟩ ≠ 1 for |000⟩")

def test_measure_z_excited():
    """⟨Z_0⟩ = -1 for |1⟩⊗|0⟩⊗|0⟩."""
    n = 3
    state = np.zeros(2**n, dtype=complex)
    state[4] = 1.0  # |100⟩ in big-endian
    z_vals = measure_pauli_z(state, n)
    assert_close(z_vals[0], -1.0, tol=1e-10, msg="⟨Z_0⟩ ≠ -1 for |100⟩")
    assert_close(z_vals[1], 1.0, tol=1e-10, msg="⟨Z_1⟩ ≠ +1 for |100⟩")
    assert_close(z_vals[2], 1.0, tol=1e-10, msg="⟨Z_2⟩ ≠ +1 for |100⟩")

def test_bell_state_correlations():
    """Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2 has ⟨Z₁Z₂⟩ = +1, ⟨Z₁⟩ = ⟨Z₂⟩ = 0."""
    state = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
    z_vals = measure_pauli_z(state, 2)
    assert_close(z_vals[0], 0, tol=1e-10, msg="⟨Z_0⟩ ≠ 0 for Bell state")
    assert_close(z_vals[1], 0, tol=1e-10, msg="⟨Z_1⟩ ≠ 0 for Bell state")
    
    features = measure_full_features(state, 2)
    # ZZ correlation should be +1
    assert_close(features[2], 1.0, tol=1e-10, msg="⟨Z₁Z₂⟩ ≠ 1 for |Φ+⟩")


# ============================================================
# NOISE CHANNEL TESTS
# ============================================================

def test_amplitude_damping_trace_preserving():
    """Amplitude damping preserves trace of density matrix."""
    state = Ry(np.pi / 3) @ np.array([1, 0], dtype=complex)
    rho = state_to_density(np.kron(state, state))  # 2-qubit state
    rho_noisy = apply_amplitude_damping(rho, gamma=0.1, n_qubits=2)
    assert_close(np.trace(rho_noisy), 1.0, tol=1e-10, msg="AD not trace-preserving")

def test_amplitude_damping_non_unital():
    """Amplitude damping is NON-unital: E(I/d) ≠ I/d."""
    n = 1
    rho_max_mixed = np.eye(2) / 2
    rho_after = apply_amplitude_damping(rho_max_mixed, gamma=0.1, n_qubits=1)
    # After AD, the maximally mixed state should shift toward |0⟩
    # So ⟨Z⟩ should become positive (closer to |0⟩)
    z_exp = np.real(np.trace(rho_after @ Z))
    assert z_exp > 0.01, f"AD should shift ⟨Z⟩ positive, got {z_exp:.6f}"

def test_depolarizing_unital():
    """Depolarizing channel IS unital: E(I/d) = I/d."""
    rho_max_mixed = np.eye(2) / 2
    rho_after = apply_depolarizing(rho_max_mixed, p=0.1, n_qubits=1)
    assert_close(rho_after, rho_max_mixed, tol=1e-10, msg="Depolarizing not unital")

def test_full_damping_goes_to_ground():
    """γ = 1.0 amplitude damping sends everything to |0⟩."""
    state = np.array([0, 1], dtype=complex)  # |1⟩
    rho = state_to_density(state)
    rho_damped = apply_amplitude_damping(rho, gamma=1.0, n_qubits=1)
    ground = np.array([[1, 0], [0, 0]], dtype=complex)
    assert_close(rho_damped, ground, tol=1e-10, msg="Full damping ≠ |0⟩⟨0|")


# ============================================================
# QRC INTEGRATION TESTS
# ============================================================

def test_qrc_feature_dimension():
    """Verify feature dimension = n + n(n-1)/2."""
    for n in [3, 5, 7]:
        qrc = QuantumReservoir(n_qubits=n, tau=1.0, seed=42)
        expected = n + n * (n - 1) // 2
        assert qrc.feature_dim == expected, \
            f"n={n}: expected {expected}, got {qrc.feature_dim}"

def test_qrc_deterministic():
    """Same input + same seed → same features."""
    qrc1 = QuantumReservoir(n_qubits=3, tau=2.0, seed=42)
    qrc2 = QuantumReservoir(n_qubits=3, tau=2.0, seed=42)
    
    inp = np.array([0.3, 0.7, 0.5])
    f1 = qrc1.step(inp)
    f2 = qrc2.step(inp)
    assert_close(f1, f2, tol=1e-12, msg="QRC not deterministic with same seed")

def test_qrc_different_inputs_different_features():
    """Different inputs should produce different features."""
    qrc = QuantumReservoir(n_qubits=3, tau=2.0, seed=42)
    f1 = qrc.step(np.array([0.1, 0.2, 0.3]))
    f2 = qrc.step(np.array([0.9, 0.8, 0.7]))
    assert np.max(np.abs(f1 - f2)) > 0.01, "Different inputs → same features"

def test_multiscale_feature_concat():
    """Multi-scale QRC feature dim = K × single feature dim."""
    ms = MultiScaleQRC(n_qubits=3, K=3, tau_base=1.0, seed=42)
    single_dim = 3 + 3 * 2 // 2  # n + n(n-1)/2 = 3 + 3 = 6
    assert ms.feature_dim == 3 * single_dim, \
        f"Expected {3*single_dim}, got {ms.feature_dim}"


def test_skill_manifest_sync():
    """qbraid_skill.yaml (the agent-facing index) stays in lockstep with cli.py:
    every yaml action id resolves in cli.py ACTIONS; every yaml group member is a
    defined yaml action; yaml headline/reproduce groups equal cli.py's."""
    import os
    import yaml
    import cli
    here = os.path.dirname(os.path.abspath(__file__))
    man = yaml.safe_load(open(os.path.join(here, "qbraid_skill.yaml")))
    yaml_ids = {a["id"] for a in man["actions"]}
    unknown = yaml_ids - set(cli.ACTIONS)
    assert not unknown, f"yaml actions missing from cli.py: {unknown}"
    for gname, members in man["groups"].items():
        dangling = set(members) - yaml_ids
        assert not dangling, f"group '{gname}' references undefined actions: {dangling}"
    for gname in ("headline", "reproduce"):
        assert list(man["groups"][gname]) == list(cli.GROUPS[gname]), \
            f"group '{gname}' drifted from cli.py"


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  CHIMERA-QRC Unit Tests")
    print("=" * 60)
    
    print("\n  Pauli Algebra:")
    test("Pauli σ² = I and commutation", test_pauli_algebra)
    test("Pauli traceless", test_pauli_trace)
    test("Pauli Hermitian", test_pauli_hermitian)
    
    print("\n  Rotation Gates:")
    test("R_Y(0) = I", test_ry_zero)
    test("R_Y(π)|0⟩ = |1⟩", test_ry_pi)
    test("R_Y(π/2)|0⟩ → ⟨Z⟩ = 0", test_ry_half_pi)
    test("R_Z(θ) unitary", test_rz_unitary)
    
    print("\n  Tensor Products:")
    test("I⊗I = I₄", test_tensor_identity)
    test("Z⊗I on |00⟩", test_tensor_z_on_first)
    test("I⊗Z on |01⟩", test_tensor_z_on_second)
    
    print("\n  Hamiltonians:")
    test("Ising & Heisenberg Hermitian", test_hamiltonian_hermitian)
    test("Time evolution unitary", test_evolution_unitary)
    
    print("\n  Measurements:")
    test("⟨Z⟩ = +1 for |000⟩", test_measure_z_ground_state)
    test("⟨Z₀⟩ = -1 for |100⟩", test_measure_z_excited)
    test("Bell state correlations", test_bell_state_correlations)
    
    print("\n  Noise Channels:")
    test("Amplitude damping trace-preserving", test_amplitude_damping_trace_preserving)
    test("Amplitude damping NON-unital", test_amplitude_damping_non_unital)
    test("Depolarizing IS unital", test_depolarizing_unital)
    test("Full damping → |0⟩", test_full_damping_goes_to_ground)
    
    print("\n  QRC Integration:")
    test("Feature dimension formula", test_qrc_feature_dimension)
    test("Deterministic with same seed", test_qrc_deterministic)
    test("Different inputs → different features", test_qrc_different_inputs_different_features)
    test("Multi-scale feature concatenation", test_multiscale_feature_concat)

    print("\n  Packaging / Skill:")
    test("qbraid_skill.yaml in sync with cli.py", test_skill_manifest_sync)

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    sys.exit(1 if failed > 0 else 0)
