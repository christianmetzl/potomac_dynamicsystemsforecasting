"""
CHIMERA-QRC Core Engine
=======================
Pure NumPy/SciPy quantum reservoir computing engine.
No Qiskit or PennyLane required — runs anywhere Python runs.

Team EIGENNEXUS | GIC 2026
"""

import numpy as np
from scipy.linalg import expm
from typing import Optional, Tuple, List

# ============================================================
# PAULI MATRICES AND TENSOR PRODUCTS
# ============================================================

# Single-qubit Pauli matrices
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

# Rotation gates
def Ry(theta: float) -> np.ndarray:
    """Single-qubit Y-rotation gate."""
    return np.array([
        [np.cos(theta / 2), -np.sin(theta / 2)],
        [np.sin(theta / 2),  np.cos(theta / 2)]
    ], dtype=complex)

def Rz(theta: float) -> np.ndarray:
    """Single-qubit Z-rotation gate."""
    return np.array([
        [np.exp(-1j * theta / 2), 0],
        [0, np.exp(1j * theta / 2)]
    ], dtype=complex)


def tensor_op(op: np.ndarray, qubit: int, n_qubits: int) -> np.ndarray:
    """
    Embed a single-qubit operator into the full n-qubit Hilbert space.
    op acts on qubit `qubit` (0-indexed), identity on all others.
    """
    matrices = [I2] * n_qubits
    matrices[qubit] = op
    result = matrices[0]
    for m in matrices[1:]:
        result = np.kron(result, m)
    return result


def two_qubit_op(op_a: np.ndarray, op_b: np.ndarray,
                 qubit_a: int, qubit_b: int, n_qubits: int) -> np.ndarray:
    """
    Embed a two-qubit interaction op_a ⊗ op_b into the full Hilbert space.
    """
    matrices = [I2] * n_qubits
    matrices[qubit_a] = op_a
    matrices[qubit_b] = op_b
    result = matrices[0]
    for m in matrices[1:]:
        result = np.kron(result, m)
    return result


# ============================================================
# HAMILTONIAN CONSTRUCTION
# ============================================================

def build_ising_hamiltonian(n_qubits: int, J_matrix: np.ndarray,
                            hx: float = 1.0, hz: float = 0.0) -> np.ndarray:
    """
    Transverse-field Ising Hamiltonian:
    H = Σ_{i<j} J_{ij} Z_i Z_j + hx Σ_i X_i + hz Σ_i Z_i
    """
    dim = 2 ** n_qubits
    H = np.zeros((dim, dim), dtype=complex)
    
    # ZZ interactions
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            if abs(J_matrix[i, j]) > 1e-12:
                H += J_matrix[i, j] * two_qubit_op(Z, Z, i, j, n_qubits)
    
    # Transverse field (X) and longitudinal field (Z)
    for i in range(n_qubits):
        if abs(hx) > 1e-12:
            H += hx * tensor_op(X, i, n_qubits)
        if abs(hz) > 1e-12:
            H += hz * tensor_op(Z, i, n_qubits)
    
    return H


def build_heisenberg_hamiltonian(n_qubits: int, J_matrix: np.ndarray,
                                  delta: float = 1.0, h: float = 0.0) -> np.ndarray:
    """
    Heisenberg XXZ Hamiltonian:
    H = Σ_{i<j} J_{ij} (X_i X_j + Y_i Y_j + Δ Z_i Z_j) + h Σ_i Z_i
    """
    dim = 2 ** n_qubits
    H = np.zeros((dim, dim), dtype=complex)
    
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            if abs(J_matrix[i, j]) > 1e-12:
                H += J_matrix[i, j] * two_qubit_op(X, X, i, j, n_qubits)
                H += J_matrix[i, j] * two_qubit_op(Y, Y, i, j, n_qubits)
                H += J_matrix[i, j] * delta * two_qubit_op(Z, Z, i, j, n_qubits)
    
    for i in range(n_qubits):
        if abs(h) > 1e-12:
            H += h * tensor_op(Z, i, n_qubits)
    
    return H


def generate_coupling_matrix(n_qubits: int, connectivity: float = 0.6,
                              J_range: Tuple[float, float] = (0.5, 1.5),
                              seed: Optional[int] = None) -> np.ndarray:
    """
    Generate a random coupling matrix for a random graph topology.
    connectivity: probability that any two qubits are coupled.
    J_range: (min, max) for coupling strengths.
    """
    rng = np.random.RandomState(seed)
    J = np.zeros((n_qubits, n_qubits))
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            if rng.random() < connectivity:
                J[i, j] = rng.uniform(*J_range)
                J[j, i] = J[i, j]
    return J


# ============================================================
# TIME EVOLUTION
# ============================================================

def time_evolve(H: np.ndarray, tau: float) -> np.ndarray:
    """
    Compute the unitary time evolution operator U(τ) = exp(-i H τ).
    Uses scipy.linalg.expm for matrix exponential.
    """
    return expm(-1j * H * tau)


# ============================================================
# INPUT ENCODING
# ============================================================

def apply_single_qubit_gate(state: np.ndarray, gate: np.ndarray,
                            qubit: int, n_qubits: int) -> np.ndarray:
    """
    Apply a single-qubit 2x2 gate to `qubit` (big-endian, qubit 0 = MSB)
    via tensor reshaping. O(2^n) instead of O(4^n) full-matrix multiply.
    """
    psi = state.reshape([2] * n_qubits)
    # Contract gate with the target axis
    psi = np.tensordot(gate, psi, axes=([1], [qubit]))
    # tensordot puts the new axis first; move it back to position `qubit`
    psi = np.moveaxis(psi, 0, qubit)
    return psi.reshape(-1)


def encode_input(state: np.ndarray, input_values: np.ndarray,
                 input_qubits: List[int], n_qubits: int) -> np.ndarray:
    """
    Encode classical input values into the quantum state via R_Y rotations.
    input_values[k] is encoded into input_qubits[k] as R_Y(π * value).
    Values should be normalized to [0, 1]. Uses fast reshape application.
    """
    for k, qubit in enumerate(input_qubits):
        if k < len(input_values):
            angle = np.pi * np.clip(input_values[k], 0, 1)
            state = apply_single_qubit_gate(state, Ry(angle), qubit, n_qubits)
    return state


def encode_feedback(state: np.ndarray, feedback_values: np.ndarray,
                    a_fb: float, n_qubits: int) -> np.ndarray:
    """
    Inject feedback via R_Z rotations on all qubits. Fast reshape application.
    """
    for qubit in range(n_qubits):
        if qubit < len(feedback_values):
            angle = a_fb * np.tanh(feedback_values[qubit])
            state = apply_single_qubit_gate(state, Rz(angle), qubit, n_qubits)
    return state


# ============================================================
# MEASUREMENT
# ============================================================

def measure_pauli_z(state: np.ndarray, n_qubits: int) -> np.ndarray:
    """
    Measure all single-qubit Z expectation values.
    Returns array of ⟨Z_i⟩ for i = 0, ..., n-1.
    """
    expectations = np.zeros(n_qubits)
    rho = np.outer(state, state.conj())
    for i in range(n_qubits):
        Zi = tensor_op(Z, i, n_qubits)
        expectations[i] = np.real(np.trace(rho @ Zi))
    return expectations


def measure_pauli_zz(state: np.ndarray, n_qubits: int) -> np.ndarray:
    """
    Measure all pairwise Z⊗Z expectation values.
    Returns array of ⟨Z_i Z_j⟩ for i < j.
    """
    rho = np.outer(state, state.conj())
    pairs = []
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            ZiZj = two_qubit_op(Z, Z, i, j, n_qubits)
            pairs.append(np.real(np.trace(rho @ ZiZj)))
    return np.array(pairs)


def measure_full_features(state: np.ndarray, n_qubits: int) -> np.ndarray:
    """
    Extract the full feature vector: [⟨Z_1⟩, ..., ⟨Z_n⟩, ⟨Z_1Z_2⟩, ..., ⟨Z_{n-1}Z_n⟩].
    Total dimension: n + n(n-1)/2.

    FAST PATH: Pauli-Z operators are diagonal in the computational basis, so
    ⟨Z_i⟩ = Σ_b (-1)^{bit_i(b)} |ψ_b|^2 and ⟨Z_i Z_j⟩ = Σ_b (-1)^{bit_i+bit_j} |ψ_b|^2.
    This is O(2^n) per observable instead of O(4^n) matrix-trace, a large speedup.
    """
    probs = np.abs(state) ** 2                      # (2^n,)
    dim = len(probs)
    idx = np.arange(dim)
    # bit value of qubit q (big-endian) for every basis state
    # qubit 0 is the most significant bit
    bits = np.array([((idx >> (n_qubits - 1 - q)) & 1) for q in range(n_qubits)])  # (n, 2^n)
    signs = 1 - 2 * bits                              # (-1)^bit, shape (n, 2^n)

    # single-qubit ⟨Z_i⟩
    z_single = signs @ probs                         # (n,)

    # pairwise ⟨Z_i Z_j⟩
    pairs = []
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            pairs.append(np.dot(signs[i] * signs[j], probs))
    z_pairs = np.array(pairs) if pairs else np.array([])
    return np.concatenate([z_single, z_pairs])


# ============================================================
# NOISE CHANNELS (Density Matrix)
# ============================================================

def state_to_density(state: np.ndarray) -> np.ndarray:
    """Convert a pure state vector to a density matrix."""
    return np.outer(state, state.conj())


def _apply_single_qubit_kraus(rho: np.ndarray, kraus_ops: list,
                              qubit: int, n_qubits: int) -> np.ndarray:
    """
    Apply a single-qubit channel (list of 2x2 Kraus operators) to `qubit`
    of an n-qubit density matrix via tensor reshaping.
    O(4^n) per Kraus instead of O(8^n) full matrix multiply.
    rho indices: (row_0..row_{n-1}, col_0..col_{n-1}).
    """
    rho_t = rho.astype(complex).reshape([2] * (2 * n_qubits))
    out = np.zeros_like(rho_t)
    row_axis = qubit
    col_axis = n_qubits + qubit
    for K in kraus_ops:
        Kc = K.conj()
        # apply K on the row index
        tmp = np.tensordot(K, rho_t, axes=([1], [row_axis]))
        tmp = np.moveaxis(tmp, 0, row_axis)
        # apply K* on the col index
        tmp = np.tensordot(Kc, tmp, axes=([1], [col_axis]))
        tmp = np.moveaxis(tmp, 0, col_axis)
        out += tmp
    return out.reshape(2 ** n_qubits, 2 ** n_qubits)


def apply_amplitude_damping(rho: np.ndarray, gamma: float,
                             n_qubits: int) -> np.ndarray:
    """
    Apply single-qubit amplitude damping to each qubit (non-unital channel).
    Fast tensor-reshape implementation.
    """
    A0 = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=complex)
    A1 = np.array([[0, np.sqrt(gamma)], [0, 0]], dtype=complex)
    for q in range(n_qubits):
        rho = _apply_single_qubit_kraus(rho, [A0, A1], q, n_qubits)
    return rho


def apply_depolarizing(rho: np.ndarray, p: float,
                        n_qubits: int) -> np.ndarray:
    """
    Apply single-qubit depolarizing to each qubit (unital channel).
    Fast tensor-reshape implementation.
    """
    k = np.sqrt(p / 3)
    K0 = np.sqrt(1 - p) * np.eye(2, dtype=complex)
    K1 = k * X.astype(complex)
    K2 = k * Y.astype(complex)
    K3 = k * Z.astype(complex)
    for q in range(n_qubits):
        rho = _apply_single_qubit_kraus(rho, [K0, K1, K2, K3], q, n_qubits)
    return rho


def measure_features_density(rho: np.ndarray, n_qubits: int) -> np.ndarray:
    """
    Extract features from a density matrix (for noisy simulation).
    FAST PATH: Pauli-Z observables depend only on the diagonal of rho.
    ⟨Z_i⟩ = Σ_b rho[b,b] (-1)^{bit_i(b)},  ⟨Z_iZ_j⟩ = Σ_b rho[b,b] (-1)^{bit_i+bit_j}.
    O(2^n) per observable instead of O(4^n) matrix trace.
    """
    diag = np.real(np.diag(rho))                     # (2^n,)
    dim = len(diag)
    idx = np.arange(dim)
    bits = np.array([((idx >> (n_qubits - 1 - q)) & 1) for q in range(n_qubits)])
    signs = 1 - 2 * bits                              # (n, 2^n)

    z_single = signs @ diag                           # (n,)
    pairs = []
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            pairs.append(np.dot(signs[i] * signs[j], diag))
    z_pairs = np.array(pairs) if pairs else np.array([])
    return np.concatenate([z_single, z_pairs])


# ============================================================
# READOUT TRAINING (Ridge Regression)
# ============================================================

def train_readout(features: np.ndarray, targets: np.ndarray,
                  alpha: float = 1e-4) -> np.ndarray:
    """
    Train linear readout weights via ridge regression.
    features: (T, d) matrix of reservoir features
    targets: (T,) or (T, k) target values
    alpha: Tikhonov regularization parameter
    Returns: weight matrix W_out
    """
    # W_out = targets^T @ features @ (features^T @ features + αI)^{-1}
    F = features  # (T, d)
    Y = targets   # (T,) or (T, k)
    
    FTF = F.T @ F  # (d, d)
    FTY = F.T @ Y  # (d,) or (d, k)
    
    W = np.linalg.solve(FTF + alpha * np.eye(FTF.shape[0]), FTY)
    return W


def predict_readout(features: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Apply trained readout weights to produce predictions."""
    return features @ W


# ============================================================
# QUANTUM RESERVOIR COMPUTER — MAIN CLASS
# ============================================================

class QuantumReservoir:
    """
    A single quantum reservoir computer.
    
    Parameters
    ----------
    n_qubits : int
        Number of qubits in the reservoir.
    tau : float
        Hamiltonian evolution time.
    hamiltonian_type : str
        'ising' or 'heisenberg'
    input_qubits : list of int
        Which qubits receive input encoding.
    J_matrix : np.ndarray, optional
        Coupling matrix. If None, generated randomly.
    hx : float
        Transverse field strength (Ising) or longitudinal field (Heisenberg).
    delta : float
        Anisotropy parameter (Heisenberg only).
    connectivity : float
        Random graph connectivity for J_matrix generation.
    noise_type : str or None
        'amplitude_damping', 'depolarizing', or None.
    noise_rate : float
        Noise channel parameter (γ for AD, p for depolarizing).
    feedback : bool
        Whether to use measurement feedback.
    a_fb : float
        Feedback strength.
    seed : int or None
        Random seed for reproducibility.
    """
    
    def __init__(self, n_qubits: int = 5, tau: float = 2.0,
                 hamiltonian_type: str = 'ising',
                 input_qubits: Optional[List[int]] = None,
                 J_matrix: Optional[np.ndarray] = None,
                 hx: float = 1.0, hz: float = 0.0,
                 delta: float = 1.0,
                 connectivity: float = 0.6,
                 noise_type: Optional[str] = None,
                 noise_rate: float = 0.0,
                 feedback: bool = False,
                 a_fb: float = 0.0,
                 seed: Optional[int] = None):
        
        self.n_qubits = n_qubits
        self.tau = tau
        self.dim = 2 ** n_qubits
        self.hamiltonian_type = hamiltonian_type
        self.input_qubits = input_qubits or list(range(min(n_qubits, 7)))
        self.noise_type = noise_type
        self.noise_rate = noise_rate
        self.feedback = feedback
        self.a_fb = a_fb
        self.seed = seed
        
        # Generate coupling matrix
        if J_matrix is None:
            self.J_matrix = generate_coupling_matrix(
                n_qubits, connectivity, seed=seed
            )
        else:
            self.J_matrix = J_matrix
        
        # Build Hamiltonian
        if hamiltonian_type == 'ising':
            self.H = build_ising_hamiltonian(n_qubits, self.J_matrix, hx, hz)
        elif hamiltonian_type == 'heisenberg':
            self.H = build_heisenberg_hamiltonian(
                n_qubits, self.J_matrix, delta, h=hx
            )
        else:
            raise ValueError(f"Unknown Hamiltonian type: {hamiltonian_type}")
        
        # Precompute evolution operator
        self.U = time_evolve(self.H, tau)
        
        # Feature dimension
        self.feature_dim = n_qubits + n_qubits * (n_qubits - 1) // 2
        
        # State
        self._reset_state()
        self._prev_measurements = np.zeros(n_qubits)
    
    def _reset_state(self):
        """Reset to |0...0⟩ state."""
        self.state = np.zeros(self.dim, dtype=complex)
        self.state[0] = 1.0
        self._prev_measurements = np.zeros(self.n_qubits)
    
    def set_hamiltonian(self, H: np.ndarray):
        """Switch to a new Hamiltonian (for regime-adaptive switching)."""
        self.H = H
        self.U = time_evolve(H, self.tau)
    
    def step(self, input_values: np.ndarray) -> np.ndarray:
        """
        Process one time step:
        1. Reset state (recurrence-free QRC for ESP guarantee)
        2. Encode input via R_Y rotations
        3. Optionally encode feedback via R_Z rotations
        4. Evolve under Hamiltonian
        5. Optionally apply noise channel
        6. Measure features
        
        Returns feature vector of dimension self.feature_dim.
        """
        # Reset state (recurrence-free for ESP)
        self._reset_state()
        
        # Encode input
        self.state = encode_input(
            self.state, input_values, self.input_qubits, self.n_qubits
        )
        
        # Encode feedback from previous step
        if self.feedback and self.a_fb > 0:
            self.state = encode_feedback(
                self.state, self._prev_measurements,
                self.a_fb, self.n_qubits
            )
        
        # Time evolution
        self.state = self.U @ self.state
        
        # Apply noise if specified
        if self.noise_type and self.noise_rate > 0:
            rho = state_to_density(self.state)
            if self.noise_type == 'amplitude_damping':
                rho = apply_amplitude_damping(rho, self.noise_rate, self.n_qubits)
            elif self.noise_type == 'depolarizing':
                rho = apply_depolarizing(rho, self.noise_rate, self.n_qubits)
            features = measure_features_density(rho, self.n_qubits)
            # Update prev measurements (single-qubit Z only)
            self._prev_measurements = features[:self.n_qubits]
        else:
            features = measure_full_features(self.state, self.n_qubits)
            self._prev_measurements = features[:self.n_qubits]
        
        return features
    
    def process_sequence(self, input_sequence: np.ndarray) -> np.ndarray:
        """
        Process an entire input sequence.
        input_sequence: (T, d) where T is time steps and d is input dimension.
        Returns: (T, feature_dim) feature matrix.
        """
        T = len(input_sequence)
        features = np.zeros((T, self.feature_dim))
        
        self._reset_state()
        self._prev_measurements = np.zeros(self.n_qubits)
        
        for t in range(T):
            features[t] = self.step(input_sequence[t])
        
        return features


# ============================================================
# MULTI-SCALE QUANTUM RESERVOIR (CHIMERA Layer 1)
# ============================================================

class MultiScaleQRC:
    """
    Multi-scale parallel quantum reservoir bank.
    Deploys K reservoirs at geometrically separated evolution times.
    
    Parameters
    ----------
    n_qubits : int
        Qubits per reservoir.
    K : int
        Number of parallel reservoirs (scales).
    tau_base : float
        Base evolution time for the fastest reservoir.
    dilation_ratio : float
        Geometric ratio between consecutive scales.
    **kwargs
        Additional arguments passed to each QuantumReservoir.
    """
    
    def __init__(self, n_qubits: int = 5, K: int = 2,
                 tau_base: float = 2.0, dilation_ratio: float = 5.0,
                 **kwargs):
        
        self.K = K
        self.reservoirs = []
        
        for k in range(K):
            tau_k = tau_base * (dilation_ratio ** k)
            res = QuantumReservoir(
                n_qubits=n_qubits, tau=tau_k, **kwargs
            )
            self.reservoirs.append(res)
        
        self.feature_dim = sum(r.feature_dim for r in self.reservoirs)
    
    def process_sequence(self, input_sequence: np.ndarray) -> np.ndarray:
        """
        Process input through all K reservoirs and concatenate features.
        Returns: (T, K * feature_dim_per_reservoir) feature matrix.
        """
        all_features = []
        for res in self.reservoirs:
            features = res.process_sequence(input_sequence)
            all_features.append(features)
        
        return np.hstack(all_features)
    
    def set_all_hamiltonians(self, H: np.ndarray):
        """Switch all reservoirs to a new Hamiltonian (regime switching)."""
        for res in self.reservoirs:
            # Recompute U with the reservoir's own tau
            res.H = H
            res.U = time_evolve(H, res.tau)


if __name__ == "__main__":
    print("CHIMERA-QRC Core Engine loaded successfully.")
    print(f"Testing 3-qubit Ising reservoir...")
    
    qrc = QuantumReservoir(n_qubits=3, tau=2.0, seed=42)
    print(f"  Feature dimension: {qrc.feature_dim}")
    
    # Test single step
    test_input = np.array([0.5, 0.3, 0.7])
    features = qrc.step(test_input)
    print(f"  Features (step 1): {features[:3].round(4)}...")
    
    # Test sequence
    test_seq = np.random.rand(10, 3)
    feat_matrix = qrc.process_sequence(test_seq)
    print(f"  Sequence features shape: {feat_matrix.shape}")
    
    # Test multi-scale
    ms = MultiScaleQRC(n_qubits=3, K=2, tau_base=2.0, dilation_ratio=5.0, seed=42)
    ms_features = ms.process_sequence(test_seq)
    print(f"  Multi-scale features shape: {ms_features.shape}")
    
    print("✅ All core engine tests passed.")
