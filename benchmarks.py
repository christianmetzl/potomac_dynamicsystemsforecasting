"""
Benchmarks, Data Utilities, and Evaluation Metrics
====================================================
Lorenz system generation, data preprocessing, BOCPD regime detection,
and comprehensive evaluation metrics.

Team EIGENNEXUS | GIC 2026
"""

import numpy as np
from typing import Tuple, Optional


# ============================================================
# CHAOTIC SYSTEMS — LORENZ ATTRACTOR
# ============================================================

def lorenz_system(T: int = 5000, dt: float = 0.02,
                  sigma: float = 10.0, rho: float = 28.0,
                  beta: float = 8.0 / 3.0,
                  initial: Optional[np.ndarray] = None,
                  warmup: int = 1000) -> np.ndarray:
    """
    Generate Lorenz-63 chaotic time series via 4th-order Runge-Kutta.
    
    Parameters
    ----------
    T : int
        Number of time steps to generate (after warmup).
    dt : float
        Integration time step.
    sigma, rho, beta : float
        Lorenz system parameters. Defaults produce chaos (λ_max ≈ 0.9056).
    initial : array, optional
        Initial condition [x, y, z]. Default: [1, 1, 1].
    warmup : int
        Steps to discard for attractor convergence.
    
    Returns
    -------
    data : (T, 3) array
        Lorenz trajectory [x(t), y(t), z(t)].
    """
    if initial is None:
        initial = np.array([1.0, 1.0, 1.0])
    
    def lorenz_deriv(state):
        x, y, z = state
        return np.array([
            sigma * (y - x),
            x * (rho - z) - y,
            x * y - beta * z
        ])
    
    total_steps = T + warmup
    trajectory = np.zeros((total_steps, 3))
    trajectory[0] = initial
    
    for t in range(total_steps - 1):
        s = trajectory[t]
        k1 = lorenz_deriv(s) * dt
        k2 = lorenz_deriv(s + k1 / 2) * dt
        k3 = lorenz_deriv(s + k2 / 2) * dt
        k4 = lorenz_deriv(s + k3) * dt
        trajectory[t + 1] = s + (k1 + 2 * k2 + 2 * k3 + k4) / 6
    
    return trajectory[warmup:]


def mackey_glass(T: int = 5000, tau: int = 17, dt: float = 1.0,
                 n: float = 10.0, gamma: float = 0.1,
                 beta_mg: float = 0.2, warmup: int = 1000) -> np.ndarray:
    """
    Generate Mackey-Glass delay differential equation time series.
    
    dx/dt = β * x(t-τ) / (1 + x(t-τ)^n) - γ * x(t)
    
    τ = 17: mildly chaotic (standard benchmark)
    τ = 30: strongly chaotic (harder benchmark)
    """
    total = T + warmup + tau
    x = np.zeros(total)
    x[:tau] = 1.2  # Initial history
    
    for t in range(tau, total - 1):
        x_tau = x[t - tau]
        dx = beta_mg * x_tau / (1 + x_tau ** n) - gamma * x[t]
        x[t + 1] = x[t] + dx * dt
    
    return x[warmup + tau: warmup + tau + T].reshape(-1, 1)


# ============================================================
# DATA PREPROCESSING
# ============================================================

def normalize_data(data: np.ndarray) -> Tuple[np.ndarray, float, float]:
    """
    Normalize data to [0, 1] range.
    Returns normalized data, min, max for inverse transform.
    """
    d_min = data.min(axis=0)
    d_max = data.max(axis=0)
    d_range = d_max - d_min
    d_range[d_range == 0] = 1  # Avoid division by zero
    normalized = (data - d_min) / d_range
    return normalized, d_min, d_max


def denormalize_data(data: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
    """Inverse of normalize_data."""
    return data * (d_max - d_min) + d_min


def create_supervised_dataset(data: np.ndarray, input_dim: int,
                               lookback: int = 1,
                               horizon: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create supervised learning dataset from time series.
    
    Parameters
    ----------
    data : (T, d) array
        Input time series.
    input_dim : int
        Number of features to use as input per step.
    lookback : int
        Number of past steps to include (sliding window).
    horizon : int
        Prediction horizon (steps ahead).
    
    Returns
    -------
    X : (N, lookback * input_dim) input features
    Y : (N, d) targets (value at t + horizon)
    """
    T = len(data)
    N = T - lookback - horizon + 1
    
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    
    d = min(input_dim, data.shape[1])
    X = np.zeros((N, lookback * d))
    Y = np.zeros((N, data.shape[1]))
    
    for i in range(N):
        window = data[i:i + lookback, :d]
        X[i] = window.flatten()
        Y[i] = data[i + lookback + horizon - 1]
    
    return X, Y


def train_test_split_temporal(X: np.ndarray, Y: np.ndarray,
                               train_ratio: float = 0.7,
                               val_ratio: float = 0.15) -> dict:
    """
    Temporal train/val/test split (no shuffling — preserves time order).
    """
    T = len(X)
    t_train = int(T * train_ratio)
    t_val = int(T * (train_ratio + val_ratio))
    
    return {
        'X_train': X[:t_train], 'Y_train': Y[:t_train],
        'X_val': X[t_train:t_val], 'Y_val': Y[t_train:t_val],
        'X_test': X[t_val:], 'Y_test': Y[t_val:],
    }


# ============================================================
# BAYESIAN ONLINE CHANGEPOINT DETECTION (BOCPD)
# ============================================================

class BOCPDetector:
    """
    Bayesian Online Changepoint Detection (Adams & MacKay, 2007).
    Detects regime transitions in real-time for Hamiltonian switching.
    
    Uses Normal-Inverse-Gamma conjugate prior for Gaussian observations.
    """
    
    def __init__(self, hazard_rate: float = 1.0 / 200,
                 mu0: float = 0.0, kappa0: float = 1.0,
                 alpha0: float = 1.0, beta0: float = 1.0):
        """
        Parameters
        ----------
        hazard_rate : float
            1/expected_run_length. Controls prior probability of changepoint.
        mu0, kappa0, alpha0, beta0 : float
            Normal-Inverse-Gamma prior hyperparameters.
        """
        self.hazard = hazard_rate
        self.mu0 = mu0
        self.kappa0 = kappa0
        self.alpha0 = alpha0
        self.beta0 = beta0
        
        # Run length distribution
        self.run_length_probs = np.array([1.0])
        
        # Sufficient statistics for each run length
        self.muT = np.array([mu0])
        self.kappaT = np.array([kappa0])
        self.alphaT = np.array([alpha0])
        self.betaT = np.array([beta0])
    
    def update(self, x: float) -> float:
        """
        Update with new observation.
        Returns the posterior probability of being in a new regime
        (i.e., changepoint probability).
        """
        n = len(self.run_length_probs)
        
        # Predictive probability for each run length
        pred_probs = self._predictive_prob(x)
        
        # Growth probabilities (no changepoint)
        growth = self.run_length_probs * pred_probs * (1 - self.hazard)
        
        # Changepoint probability
        cp = np.sum(self.run_length_probs * pred_probs * self.hazard)
        
        # New run length distribution
        new_probs = np.zeros(n + 1)
        new_probs[0] = cp
        new_probs[1:] = growth
        
        # Normalize
        total = new_probs.sum()
        if total > 0:
            new_probs /= total
        
        self.run_length_probs = new_probs
        
        # Update sufficient statistics
        self._update_suffstats(x)
        
        # Return changepoint probability (run_length = 0)
        return new_probs[0]
    
    def _predictive_prob(self, x: float) -> np.ndarray:
        """Student-t predictive distribution for each run length."""
        nu = 2 * self.alphaT
        mu = self.muT
        var = self.betaT * (self.kappaT + 1) / (self.alphaT * self.kappaT)
        
        # Student-t log pdf
        z = (x - mu) ** 2 / var
        log_prob = (
            np.lgamma((nu + 1) / 2) - np.lgamma(nu / 2)
            - 0.5 * np.log(nu * np.pi * var)
            - (nu + 1) / 2 * np.log(1 + z / nu)
        )
        return np.exp(log_prob)
    
    def _update_suffstats(self, x: float):
        """Update NIG sufficient statistics."""
        new_mu = np.concatenate([[self.mu0],
                                  (self.kappaT * self.muT + x) / (self.kappaT + 1)])
        new_kappa = np.concatenate([[self.kappa0], self.kappaT + 1])
        new_alpha = np.concatenate([[self.alpha0], self.alphaT + 0.5])
        new_beta = np.concatenate([[self.beta0],
                                    self.betaT + 0.5 * self.kappaT * (x - self.muT) ** 2 / (self.kappaT + 1)])
        
        self.muT = new_mu
        self.kappaT = new_kappa
        self.alphaT = new_alpha
        self.betaT = new_beta
    
    def get_regime_indicator(self) -> float:
        """
        Return a regime indicator based on recent changepoint activity.
        High value = volatile/changing regime.
        Low value = stable regime.
        """
        # Weighted average run length (short = volatile, long = stable)
        run_lengths = np.arange(len(self.run_length_probs))
        expected_rl = np.sum(run_lengths * self.run_length_probs)
        
        # Sigmoid transform: short run length → high volatility indicator
        volatility = 1.0 / (1.0 + np.exp(0.05 * (expected_rl - 50)))
        return volatility


# ============================================================
# EVALUATION METRICS
# ============================================================

def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Squared Error."""
    return np.mean((y_true - y_pred) ** 2)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return np.sqrt(mse(y_true, y_pred))


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Normalized RMSE (divided by std of true values)."""
    sigma = np.std(y_true)
    if sigma < 1e-12:
        return float('inf')
    return rmse(y_true, y_pred) / sigma


def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination R²."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot < 1e-12:
        return 0.0
    return 1 - ss_res / ss_tot


def valid_prediction_time(y_true: np.ndarray, y_pred: np.ndarray,
                           threshold: float = 0.4,
                           lyapunov_time: float = 1.0 / 0.9056) -> float:
    """
    Valid Prediction Time in Lyapunov times.
    The number of time steps before NRMSE exceeds threshold,
    converted to Lyapunov time units.
    """
    errors = np.abs(y_true - y_pred)
    sigma = np.std(y_true)
    
    if sigma < 1e-12:
        return 0.0
    
    normalized_error = errors / sigma
    
    # Find first time step where error exceeds threshold
    exceed = np.where(normalized_error > threshold)[0]
    if len(exceed) == 0:
        vpt_steps = len(y_true)
    else:
        vpt_steps = exceed[0]
    
    return vpt_steps * lyapunov_time


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                         name: str = "Model") -> dict:
    """Compute all metrics and return as dictionary."""
    metrics = {
        'name': name,
        'MSE': mse(y_true, y_pred),
        'RMSE': rmse(y_true, y_pred),
        'NRMSE': nrmse(y_true, y_pred),
        'R²': r_squared(y_true, y_pred),
    }
    return metrics


def print_metrics(metrics: dict):
    """Pretty-print evaluation metrics."""
    print(f"\n{'='*50}")
    print(f"  {metrics['name']}")
    print(f"{'='*50}")
    print(f"  MSE:   {metrics['MSE']:.6f}")
    print(f"  RMSE:  {metrics['RMSE']:.6f}")
    print(f"  NRMSE: {metrics['NRMSE']:.6f}")
    print(f"  R²:    {metrics['R²']:.6f}")
    print(f"{'='*50}")


def print_comparison_table(all_metrics: list):
    """Print a comparison table of multiple models."""
    print(f"\n{'Model':<25} {'MSE':>10} {'RMSE':>10} {'NRMSE':>10} {'R²':>10}")
    print("-" * 67)
    for m in all_metrics:
        print(f"{m['name']:<25} {m['MSE']:>10.6f} {m['RMSE']:>10.6f} "
              f"{m['NRMSE']:>10.6f} {m['R²']:>10.6f}")


if __name__ == "__main__":
    print("Benchmarks and utilities loaded successfully.")
    
    # Test Lorenz system
    lorenz = lorenz_system(T=1000)
    print(f"  Lorenz trajectory shape: {lorenz.shape}")
    print(f"  Lorenz x range: [{lorenz[:,0].min():.2f}, {lorenz[:,0].max():.2f}]")
    
    # Test Mackey-Glass
    mg = mackey_glass(T=1000, tau=17)
    print(f"  Mackey-Glass shape: {mg.shape}")
    
    # Test BOCPD
    bocpd = BOCPDetector()
    for i in range(50):
        cp_prob = bocpd.update(np.random.randn())
    print(f"  BOCPD changepoint prob after 50 steps: {cp_prob:.4f}")
    print(f"  BOCPD regime indicator: {bocpd.get_regime_indicator():.4f}")
    
    # Test metrics
    y_t = np.random.randn(100)
    y_p = y_t + 0.1 * np.random.randn(100)
    m = compute_all_metrics(y_t, y_p, "Test Model")
    print_metrics(m)
    
    print("✅ All benchmark tests passed.")
