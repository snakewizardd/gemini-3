
"""
Dynamic Decision Algorithm (DDA) - OPTIMIZED Simulation Suite v2.0
==================================================================
Tuned hyperparameters based on noise analysis.
Key changes:
  - Reduced derivative gain (0.05 vs 0.2)
  - Increased inertia (P0=0.85 vs 0.7)
  - Dampened adaptive scaling (alpha=0.005 vs 0.01)
  - Added optional low-pass filtering on delta_I
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# SECTION 1: OPTIMIZED DDA IMPLEMENTATION
# =============================================================================

@dataclass
class DDAConfig:
    """
    OPTIMIZED configuration for Dynamic Decision Algorithm.
    
    Changes from v1.0:
      - P0: 0.7 -> 0.85 (more inertia to smooth noise)
      - m:  0.3 -> 0.15 (less reactive to noisy observations)
      - alpha: 0.01 -> 0.005 (slower k adaptation, less oscillation)
      - derivative_gain: 0.2 -> 0.05 (reduced noise amplification)
    """
    P0: float = 0.85              # Prior weight (INCREASED)
    m: float = 0.15               # Likelihood weight (DECREASED)
    alpha: float = 0.005          # Adaptive scaling learning rate (HALVED)
    beta: float = 0.5             # Error sensitivity exponent
    k_init: float = 1.0           # Initial scaling factor
    derivative_gain: float = 0.05 # Weight for delta_I term (REDUCED from 0.2)
    use_ema_filter: bool = True   # Apply EMA smoothing to delta_I
    ema_alpha: float = 0.3        # EMA smoothing factor for delta_I


class DDAUpdateV2:
    """
    Dynamic Decision Algorithm v2.0 - Noise-Optimized Implementation
    
    F_n = P0 * k(F_{n-1}) + m * [T(I_n, ΔI) + R(D_n, Φ)]
    
    Key improvements:
      - Low-pass filtered derivative term
      - Dampened adaptive scaling
      - Configurable noise rejection
    """
    
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0  # EMA-filtered delta
        self.history = {
            'F': [], 'k': [], 'errors': [], 'delta_I': []
        }
        
    def prior_influence(self, F_prev: float) -> float:
        """k(F_{n-1}): Prior influence function."""
        return self.k * F_prev
    
    def likelihood_transform(self, I_n: float, delta_I: float) -> float:
        """
        T(I_n, ΔI): OPTIMIZED Likelihood-driven transformation.
        
        v2.0 Changes:
          - Reduced derivative gain (0.05 vs 0.2)
          - Optional EMA filtering on delta_I to reduce noise
        """
        # Apply EMA filter to delta_I if enabled
        if self.config.use_ema_filter:
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                     (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
        
        # Reduced derivative gain to minimize noise amplification
        return (1 - self.config.derivative_gain) * I_n + self.config.derivative_gain * effective_delta
    
    def regularization(self, D_n: float = 0.0, Phi: dict = None) -> float:
        """R(D_n, Φ): Contextual regularization."""
        Phi = Phi or {'lambda': 0.01}
        return -Phi['lambda'] * self.F_prev
    
    def update(self, I_n: float, target: float = None) -> float:
        """
        Perform one DDA update step.
        """
        delta_I = I_n - self.I_prev
        
        # Store raw delta for analysis
        self.history['delta_I'].append(delta_I)
        
        # DDA Formula with optimized components
        prior_term = self.config.P0 * self.prior_influence(self.F_prev)
        likelihood_term = self.likelihood_transform(I_n, delta_I)
        reg_term = self.regularization()
        
        F_n = prior_term + self.config.m * (likelihood_term + reg_term)
        
        # DAMPENED adaptive scaling update
        if target is not None:
            epsilon = target - F_n
            # Clip epsilon to prevent extreme k adjustments
            epsilon_clipped = np.clip(epsilon, -1.0, 1.0)
            self.k += self.config.alpha * np.sign(epsilon_clipped) * (np.abs(epsilon_clipped) ** self.config.beta)
            # Keep k in reasonable bounds
            self.k = np.clip(self.k, 0.5, 2.0)
            self.history['errors'].append(epsilon)
        
        # Store history
        self.history['F'].append(F_n)
        self.history['k'].append(self.k)
        
        # Update state
        self.F_prev = F_n
        self.I_prev = I_n
        
        return F_n
    
    def reset(self):
        """Reset the algorithm state."""
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': [], 'errors': [], 'delta_I': []}


# =============================================================================
# SECTION 2: BASELINE ALGORITHMS (unchanged)
# =============================================================================

class StaticBayesEstimator:
    def __init__(self, prior_weight: float = 0.7):
        self.prior_weight = prior_weight
        self.F_prev = 0.0
        self.history = []
        
    def update(self, I_n: float) -> float:
        F_n = self.prior_weight * self.F_prev + (1 - self.prior_weight) * I_n
        self.F_prev = F_n
        self.history.append(F_n)
        return F_n
    
    def reset(self):
        self.F_prev = 0.0
        self.history = []


class ExponentialMovingAverage:
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.F_prev = None
        self.history = []
        
    def update(self, I_n: float) -> float:
        if self.F_prev is None:
            F_n = I_n
        else:
            F_n = self.alpha * I_n + (1 - self.alpha) * self.F_prev
        self.F_prev = F_n
        self.history.append(F_n)
        return F_n
    
    def reset(self):
        self.F_prev = None
        self.history = []


# =============================================================================
# SECTION 3: ENVIRONMENT GENERATORS (unchanged)
# =============================================================================

def generate_stationary_environment(n_steps: int, noise_std: float = 0.1, 
                                    true_value: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    targets = np.ones(n_steps) * true_value
    observations = targets + np.random.normal(0, noise_std, n_steps)
    return targets, observations


def generate_nonstationary_environment(n_steps: int, noise_std: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
    t = np.arange(n_steps)
    targets = np.sin(0.1 * t) + 0.5 * np.cos(0.05 * t)
    observations = targets + np.random.normal(0, noise_std, n_steps)
    return targets, observations


# =============================================================================
# SECTION 4: EVALUATION METRICS (unchanged)
# =============================================================================

def calculate_mse(predictions: np.ndarray, targets: np.ndarray) -> float:
    return np.mean((predictions - targets) ** 2)

def calculate_mae(predictions: np.ndarray, targets: np.ndarray) -> float:
    return np.mean(np.abs(predictions - targets))

def calculate_convergence_iteration(errors: np.ndarray, threshold: float = 0.05) -> int:
    below_threshold = np.where(np.abs(errors) < threshold)[0]
    return below_threshold[0] if len(below_threshold) > 0 else len(errors)

def calculate_adaptation_lag(predictions: np.ndarray, targets: np.ndarray, 
                             change_points: List[int], window: int = 20) -> float:
    lags = []
    for cp in change_points:
        if cp + window < len(predictions):
            for i in range(cp, min(cp + window, len(predictions))):
                if np.abs(predictions[i] - targets[i]) < 0.1 * np.abs(targets[cp] - targets[cp-1] if cp > 0 else targets[cp]):
                    lags.append(i - cp)
                    break
    return np.mean(lags) if lags else window


# =============================================================================
# SECTION 5: OPTIMIZED SIMULATION
# =============================================================================

def run_optimized_simulation(n_steps: int = 500, n_trials: int = 50, seed: int = 42) -> dict:
    """
    Run simulation with OPTIMIZED DDA parameters.
    """
    np.random.seed(seed)
    
    results = {
        'stationary': {'DDA_v2': [], 'DDA_v1': [], 'StaticBayes': [], 'EMA': []},
        'nonstationary': {'DDA_v2': [], 'DDA_v1': [], 'StaticBayes': [], 'EMA': []},
        'convergence': {'DDA_v2': [], 'DDA_v1': [], 'StaticBayes': [], 'EMA': []},
        'adaptation_lag': {'DDA_v2': [], 'DDA_v1': [], 'StaticBayes': [], 'EMA': []}
    }
    
    # Config comparison
    config_v1 = DDAConfig(P0=0.7, m=0.3, alpha=0.01, beta=0.5, 
                          derivative_gain=0.2, use_ema_filter=False)
    config_v2 = DDAConfig(P0=0.85, m=0.15, alpha=0.005, beta=0.5,
                          derivative_gain=0.05, use_ema_filter=True, ema_alpha=0.3)
    
    for trial in range(n_trials):
        # Initialize all algorithms
        dda_v2 = DDAUpdateV2(config_v2)  # OPTIMIZED
        dda_v1 = DDAUpdateV2(config_v1)  # Original for comparison
        static_bayes = StaticBayesEstimator(prior_weight=0.7)
        ema = ExponentialMovingAverage(alpha=0.3)
        
        # ===== STATIONARY ENVIRONMENT =====
        targets_stat, obs_stat = generate_stationary_environment(n_steps)
        
        preds_v2, preds_v1, preds_sb, preds_ema = [], [], [], []
        for i in range(n_steps):
            preds_v2.append(dda_v2.update(obs_stat[i], target=targets_stat[i]))
            preds_v1.append(dda_v1.update(obs_stat[i], target=targets_stat[i]))
            preds_sb.append(static_bayes.update(obs_stat[i]))
            preds_ema.append(ema.update(obs_stat[i]))
        
        results['stationary']['DDA_v2'].append(calculate_mse(np.array(preds_v2), targets_stat))
        results['stationary']['DDA_v1'].append(calculate_mse(np.array(preds_v1), targets_stat))
        results['stationary']['StaticBayes'].append(calculate_mse(np.array(preds_sb), targets_stat))
        results['stationary']['EMA'].append(calculate_mse(np.array(preds_ema), targets_stat))
        
        # Convergence
        errors_v2 = np.array(preds_v2) - targets_stat
        errors_v1 = np.array(preds_v1) - targets_stat
        errors_sb = np.array(preds_sb) - targets_stat
        errors_ema = np.array(preds_ema) - targets_stat
        
        results['convergence']['DDA_v2'].append(calculate_convergence_iteration(errors_v2))
        results['convergence']['DDA_v1'].append(calculate_convergence_iteration(errors_v1))
        results['convergence']['StaticBayes'].append(calculate_convergence_iteration(errors_sb))
        results['convergence']['EMA'].append(calculate_convergence_iteration(errors_ema))
        
        # Reset for non-stationary
        dda_v2.reset(); dda_v1.reset(); static_bayes.reset(); ema.reset()
        
        # ===== NON-STATIONARY ENVIRONMENT =====
        targets_nonstat, obs_nonstat = generate_nonstationary_environment(n_steps)
        
        preds_v2, preds_v1, preds_sb, preds_ema = [], [], [], []
        for i in range(n_steps):
            preds_v2.append(dda_v2.update(obs_nonstat[i], target=targets_nonstat[i]))
            preds_v1.append(dda_v1.update(obs_nonstat[i], target=targets_nonstat[i]))
            preds_sb.append(static_bayes.update(obs_nonstat[i]))
            preds_ema.append(ema.update(obs_nonstat[i]))
        
        results['nonstationary']['DDA_v2'].append(calculate_mse(np.array(preds_v2), targets_nonstat))
        results['nonstationary']['DDA_v1'].append(calculate_mse(np.array(preds_v1), targets_nonstat))
        results['nonstationary']['StaticBayes'].append(calculate_mse(np.array(preds_sb), targets_nonstat))
        results['nonstationary']['EMA'].append(calculate_mse(np.array(preds_ema), targets_nonstat))
        
        # Adaptation lag
        peaks = [i for i in range(1, n_steps-1) 
                 if targets_nonstat[i] > targets_nonstat[i-1] and targets_nonstat[i] > targets_nonstat[i+1]][:10]
        
        results['adaptation_lag']['DDA_v2'].append(
            calculate_adaptation_lag(np.array(preds_v2), targets_nonstat, peaks))
        results['adaptation_lag']['DDA_v1'].append(
            calculate_adaptation_lag(np.array(preds_v1), targets_nonstat, peaks))
        results['adaptation_lag']['StaticBayes'].append(
            calculate_adaptation_lag(np.array(preds_sb), targets_nonstat, peaks))
        results['adaptation_lag']['EMA'].append(
            calculate_adaptation_lag(np.array(preds_ema), targets_nonstat, peaks))
    
    # Aggregate
    final_results = {}
    for metric in results:
        final_results[metric] = {}
        for algo in results[metric]:
            vals = results[metric][algo]
            final_results[metric][algo] = {'mean': np.mean(vals), 'std': np.std(vals)}
    
    return final_results


def print_optimized_results(results: dict):
    """Print comparison table with v1 vs v2."""
    print("\n" + "="*85)
    print("TABLE 1: OPTIMIZED Simulation Results (500 steps, 50 trials)")
    print("="*85)
    print(f"{'Metric':<22} {'DDA v2.0':<15} {'DDA v1.0':<15} {'Static Bayes':<15} {'EMA':<15}")
    print(f"{'':22} {'(OPTIMIZED)':<15} {'(Original)':<15} {'':15} {'':15}")
    print("-"*85)
    
    for metric_name, display_name in [
        ('stationary', 'MSE (stationary)'),
        ('nonstationary', 'MSE (non-stationary)'),
        ('convergence', 'Convergence (iters)'),
        ('adaptation_lag', 'Adaptation lag')
    ]:
        v2 = results[metric_name]['DDA_v2']
        v1 = results[metric_name]['DDA_v1']
        sb = results[metric_name]['StaticBayes']
        ema = results[metric_name]['EMA']
        
        # Find winner
        means = [v2['mean'], v1['mean'], sb['mean'], ema['mean']]
        winner_idx = np.argmin(means)
        
        row = f"{display_name:<22}"
        for idx, (m, s) in enumerate([(v2['mean'], v2['std']), (v1['mean'], v1['std']), 
                                       (sb['mean'], sb['std']), (ema['mean'], ema['std'])]):
            marker = " ✓" if idx == winner_idx else ""
            if metric_name == 'convergence':
                row += f"{m:>5.1f}±{s:<4.1f}{marker:<4}"
            else:
                row += f"{m:>6.4f}±{s:<5.3f}{marker:<2}"
        print(row)
    
    print("="*85)
    print("✓ = Best performance for metric")
    print("="*85)


def plot_v1_vs_v2_comparison(n_steps: int = 500):
    """Generate comparison plot showing v1 jitter vs v2 smoothness."""
    np.random.seed(42)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    config_v1 = DDAConfig(P0=0.7, m=0.3, alpha=0.01, derivative_gain=0.2, use_ema_filter=False)
    config_v2 = DDAConfig(P0=0.85, m=0.15, alpha=0.005, derivative_gain=0.05, use_ema_filter=True)
    
    dda_v1 = DDAUpdateV2(config_v1)
    dda_v2 = DDAUpdateV2(config_v2)
    ema = ExponentialMovingAverage(alpha=0.3)
    
    targets, observations = generate_nonstationary_environment(n_steps)
    
    preds_v1, preds_v2, preds_ema = [], [], []
    for i in range(n_steps):
        preds_v1.append(dda_v1.update(observations[i], target=targets[i]))
        preds_v2.append(dda_v2.update(observations[i], target=targets[i]))
        preds_ema.append(ema.update(observations[i]))
    
    preds_v1, preds_v2, preds_ema = np.array(preds_v1), np.array(preds_v2), np.array(preds_ema)
    
    # Plot 1: Tracking comparison
    ax1 = axes[0, 0]
    ax1.plot(targets, 'k-', linewidth=2, label='Target $F^*$')
    ax1.plot(preds_v1, 'r-', alpha=0.7, linewidth=1, label='DDA v1.0 (jittery)')
    ax1.plot(preds_v2, 'b-', linewidth=1.5, label='DDA v2.0 (smooth)')
    ax1.set_xlabel('Time step')
    ax1.set_ylabel('Value')
    ax1.set_title('(a) DDA v1.0 vs v2.0 Tracking')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Zoomed section
    ax2 = axes[0, 1]
    zoom_start, zoom_end = 200, 300
    ax2.plot(range(zoom_start, zoom_end), targets[zoom_start:zoom_end], 'k-', linewidth=2, label='Target')
    ax2.plot(range(zoom_start, zoom_end), preds_v1[zoom_start:zoom_end], 'r-', alpha=0.7, label='v1.0')
    ax2.plot(range(zoom_start, zoom_end), preds_v2[zoom_start:zoom_end], 'b-', linewidth=1.5, label='v2.0')
    ax2.plot(range(zoom_start, zoom_end), preds_ema[zoom_start:zoom_end], 'g--', alpha=0.7, label='EMA')
    ax2.set_xlabel('Time step')
    ax2.set_ylabel('Value')
    ax2.set_title('(b) Zoomed: Noise Reduction in v2.0')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling MSE comparison
    ax3 = axes[1, 0]
    window = 20
    mse_v1 = np.convolve((preds_v1 - targets)**2, np.ones(window)/window, mode='valid')
    mse_v2 = np.convolve((preds_v2 - targets)**2, np.ones(window)/window, mode='valid')
    mse_ema = np.convolve((preds_ema - targets)**2, np.ones(window)/window, mode='valid')
    
    ax3.plot(mse_v1, 'r-', alpha=0.7, label=f'DDA v1.0 (avg: {np.mean(mse_v1):.4f})')
    ax3.plot(mse_v2, 'b-', linewidth=1.5, label=f'DDA v2.0 (avg: {np.mean(mse_v2):.4f})')
    ax3.plot(mse_ema, 'g--', alpha=0.7, label=f'EMA (avg: {np.mean(mse_ema):.4f})')
    ax3.set_xlabel('Time step')
    ax3.set_ylabel('Rolling MSE')
    ax3.set_title('(c) Rolling MSE Comparison')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: k evolution comparison
    ax4 = axes[1, 1]
    ax4.plot(dda_v1.history['k'], 'r-', alpha=0.7, label='v1.0 (oscillating)')
    ax4.plot(dda_v2.history['k'], 'b-', linewidth=1.5, label='v2.0 (stable)')
    ax4.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    ax4.set_xlabel('Time step')
    ax4.set_ylabel('Scaling factor $k_n$')
    ax4.set_title('(d) Adaptive Scaling: Dampened in v2.0')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('Figure 4: DDA v1.0 vs v2.0 - Noise Optimization Results', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('dda_v1_vs_v2.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.show()
    print("✓ Saved: dda_v1_vs_v2.png")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("="*85)
    print("DYNAMIC DECISION ALGORITHM (DDA) - OPTIMIZED SIMULATION v2.0")
    print("="*85)
    print("\nHyperparameter Changes:")
    print("  P0:              0.70 -> 0.85 (more inertia)")
    print("  m:               0.30 -> 0.15 (less noise reactivity)")
    print("  alpha:           0.01 -> 0.005 (dampened k adaptation)")
    print("  derivative_gain: 0.20 -> 0.05 (reduced noise amplification)")
    print("  EMA filter:      OFF  -> ON (smoothed delta_I)")
    
    print("\n[1/2] Running optimized Monte Carlo simulations...")
    results = run_optimized_simulation(n_steps=500, n_trials=50, seed=42)
    print_optimized_results(results)
    
    print("\n[2/2] Generating v1 vs v2 comparison plot...")
    plot_v1_vs_v2_comparison()
    
    print("\n" + "="*85)
    print("OPTIMIZATION COMPLETE!")
    print("="*85)
