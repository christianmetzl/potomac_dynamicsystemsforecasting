"""
Classical Baselines — Echo State Network & Deep ESN
====================================================
Fair comparison baselines for CHIMERA-QRC benchmarking.

Team EIGENNEXUS | GIC 2026
"""

import numpy as np
from typing import Optional, Tuple


class EchoStateNetwork:
    """
    Classical Echo State Network (Jaeger, 2001).
    
    Parameters
    ----------
    n_reservoir : int
        Number of reservoir neurons.
    spectral_radius : float
        Spectral radius of the recurrent weight matrix.
    input_scaling : float
        Scaling factor for input weights.
    leaking_rate : float
        Leaking rate α ∈ (0, 1]. Controls dynamics speed.
    connectivity : float
        Fraction of non-zero weights in W.
    ridge_alpha : float
        Ridge regression regularization parameter.
    seed : int or None
        Random seed for reproducibility.
    """
    
    def __init__(self, n_reservoir: int = 300,
                 spectral_radius: float = 0.95,
                 input_scaling: float = 0.1,
                 leaking_rate: float = 0.3,
                 connectivity: float = 0.1,
                 ridge_alpha: float = 1e-4,
                 seed: Optional[int] = None):
        
        self.n_reservoir = n_reservoir
        self.spectral_radius = spectral_radius
        self.input_scaling = input_scaling
        self.leaking_rate = leaking_rate
        self.ridge_alpha = ridge_alpha
        self.seed = seed
        
        rng = np.random.RandomState(seed)
        
        # Input weight matrix (dense, random)
        self.W_in = rng.uniform(-input_scaling, input_scaling,
                                (n_reservoir, 1))  # Will be resized on first use
        self._input_dim_set = False
        
        # Reservoir weight matrix (sparse, scaled to spectral_radius)
        W = rng.randn(n_reservoir, n_reservoir)
        # Make sparse
        mask = rng.random((n_reservoir, n_reservoir)) < connectivity
        W *= mask
        # Scale to desired spectral radius
        current_sr = np.max(np.abs(np.linalg.eigvals(W)))
        if current_sr > 0:
            W = W * (spectral_radius / current_sr)
        self.W = W
        
        # Bias
        self.bias = rng.uniform(-0.1, 0.1, n_reservoir)
        
        # State
        self.state = np.zeros(n_reservoir)
        
        # Trained readout
        self.W_out = None
        self.rng = rng
    
    def _init_input_weights(self, input_dim: int):
        """Initialize input weights for the given input dimension."""
        self.W_in = self.rng.uniform(
            -self.input_scaling, self.input_scaling,
            (self.n_reservoir, input_dim)
        )
        self._input_dim_set = True
    
    def reset(self):
        """Reset reservoir state."""
        self.state = np.zeros(self.n_reservoir)
    
    def step(self, u: np.ndarray) -> np.ndarray:
        """
        Process one input step.
        u: input vector of shape (input_dim,)
        Returns: reservoir state of shape (n_reservoir,)
        """
        if not self._input_dim_set:
            self._init_input_weights(len(u))
        
        # ESN state update: h(t) = (1-α)h(t-1) + α·tanh(W_in·u + W·h(t-1) + b)
        pre_activation = self.W_in @ u + self.W @ self.state + self.bias
        self.state = (1 - self.leaking_rate) * self.state + \
                     self.leaking_rate * np.tanh(pre_activation)
        
        return self.state.copy()
    
    def process_sequence(self, input_sequence: np.ndarray,
                         washout: int = 0) -> np.ndarray:
        """
        Process entire input sequence through the reservoir.
        input_sequence: (T, input_dim)
        washout: number of initial steps to discard (reservoir warm-up)
        Returns: (T - washout, n_reservoir) feature matrix
        """
        self.reset()
        T = len(input_sequence)
        
        if not self._input_dim_set:
            self._init_input_weights(input_sequence.shape[1])
        
        states = np.zeros((T, self.n_reservoir))
        for t in range(T):
            states[t] = self.step(input_sequence[t])
        
        return states[washout:]
    
    def train(self, features: np.ndarray, targets: np.ndarray):
        """Train readout via ridge regression."""
        FTF = features.T @ features
        FTY = features.T @ targets
        self.W_out = np.linalg.solve(
            FTF + self.ridge_alpha * np.eye(FTF.shape[0]), FTY
        )
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Apply trained readout."""
        if self.W_out is None:
            raise ValueError("Model not trained. Call train() first.")
        return features @ self.W_out


class DeepEchoStateNetwork:
    """
    Deep Echo State Network (Gallicchio et al., 2017).
    Stacked ESN layers where higher layers develop progressively slower dynamics.
    
    Parameters
    ----------
    n_layers : int
        Number of stacked reservoir layers.
    n_reservoir_per_layer : int
        Neurons per layer.
    spectral_radii : list of float
        Spectral radius per layer. If None, all set to 0.95.
    leaking_rates : list of float
        Leaking rate per layer. If None, progressively slower: [0.5, 0.3, 0.1].
    """
    
    def __init__(self, n_layers: int = 3,
                 n_reservoir_per_layer: int = 100,
                 spectral_radii: Optional[list] = None,
                 leaking_rates: Optional[list] = None,
                 ridge_alpha: float = 1e-4,
                 seed: Optional[int] = None):
        
        self.n_layers = n_layers
        
        if spectral_radii is None:
            spectral_radii = [0.95] * n_layers
        if leaking_rates is None:
            # Progressively slower dynamics in higher layers
            leaking_rates = [0.5 / (k + 1) for k in range(n_layers)]
        
        self.layers = []
        for k in range(n_layers):
            layer = EchoStateNetwork(
                n_reservoir=n_reservoir_per_layer,
                spectral_radius=spectral_radii[k],
                leaking_rate=leaking_rates[k],
                ridge_alpha=ridge_alpha,
                seed=(seed + k) if seed is not None else None
            )
            self.layers.append(layer)
        
        self.ridge_alpha = ridge_alpha
        self.W_out = None
        self.total_features = n_layers * n_reservoir_per_layer
    
    def process_sequence(self, input_sequence: np.ndarray,
                         washout: int = 50) -> np.ndarray:
        """
        Process input through all layers.
        Layer 1 receives external input.
        Layer k>1 receives the state of layer k-1.
        All layer states are concatenated as features.
        """
        T = len(input_sequence)
        all_states = []
        
        # Layer 1: processes external input
        states_1 = self.layers[0].process_sequence(input_sequence, washout=0)
        all_states.append(states_1)
        
        # Layers 2+: process output of previous layer
        for k in range(1, self.n_layers):
            states_k = self.layers[k].process_sequence(
                all_states[-1], washout=0
            )
            all_states.append(states_k)
        
        # Concatenate all layer states and apply washout
        combined = np.hstack(all_states)
        return combined[washout:]
    
    def train(self, features: np.ndarray, targets: np.ndarray):
        """Train readout via ridge regression."""
        FTF = features.T @ features
        FTY = features.T @ targets
        self.W_out = np.linalg.solve(
            FTF + self.ridge_alpha * np.eye(FTF.shape[0]), FTY
        )
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Apply trained readout."""
        return features @ self.W_out


if __name__ == "__main__":
    print("Classical Baselines loaded successfully.")
    
    # Test ESN
    esn = EchoStateNetwork(n_reservoir=100, seed=42)
    test_seq = np.random.rand(200, 3)
    features = esn.process_sequence(test_seq, washout=50)
    print(f"  ESN features shape: {features.shape}")
    
    # Test DeepESN
    desn = DeepEchoStateNetwork(n_layers=3, n_reservoir_per_layer=50, seed=42)
    features_deep = desn.process_sequence(test_seq, washout=50)
    print(f"  DeepESN features shape: {features_deep.shape}")
    
    print("✅ All baseline tests passed.")
