
"""
Dynamic Decision Algorithm (DDA) - v2.1 "Goldilocks" Configuration
==================================================================
The sweet spot between v1.0 (jittery but fast) and v2.0 (smooth but sluggish)

Key insight: EMA filter handles noise rejection, so we can be aggressive again!
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# THE GOLDILOCKS CONFIG
# =============================================================================

@dataclass
class DDAConfig:
    """
    v2.1 "GOLDILOCKS" Configuration
    
    Evolution:
      v1.0: Fast but jittery (derivative noise)
      v2.0: Smooth but sluggish (over-damped)
      v2.1: Fast AND smooth (EMA filter + aggressive k)
    """
    # --- THE GOLDILOCKS VALUES ---
    P0: float = 0.75              # v1:0.70 → v2:0.85 → v2.1:0.75 (balanced inertia)
    m: float = 0.25               # v1:0.30 → v2:0.15 → v2.1:0.25 (respect new data)
    alpha: float = 0.02           # v1:0.01 → v2:0.005 → v2.1:0.02 (FAST k adaptation!)
    beta: float = 0.5             # unchanged
    k_init: float = 1.0           # unchanged
    derivative_gain: float = 0.10 # v1:0.20 → v2:0.05 → v2.1:0.10 (moderate)
    use_ema_filter: bool = True   # THE SECRET SAUCE - keeps us smooth
    ema_alpha: float = 0.3        # unchanged


class DDAUpdateV21:
    """
    DDA v2.1 - Goldilocks Implementation
    
    Philosophy: Let the EMA filter handle noise, let k handle adaptation
    """
    
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': [], 'errors': [], 'delta_I': []}
        
    def prior_influence(self, F_prev: float) -> float:
        return self.k * F_prev
    
    def likelihood_transform(self, I_n: float, delta_I: float) -> float:
        """EMA-filtered derivative for smooth but responsive tracking."""
        if self.config.use_ema_filter:
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                     (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
        
        return (1 - self.config.derivative_gain) * I_n + self.config.derivative_gain * effective_delta
    
    def regularization(self, D_n: float = 0.0, Phi: dict = None) -> float:
        Phi = Phi or {'lambda': 0.01}
        return -Phi['lambda'] * self.F_prev
    
    def update(self, I_n: float, target: float = None) -> float:
        delta_I = I_n - self.I_prev
        self.history['delta_I'].append(delta_I)
        
        prior_term = self.config.P0 * self.prior_influence(self.F_prev)
        likelihood_term = self.likelihood_transform(I_n, delta_I)
        reg_term = self.regularization()
        
        F_n = prior_term + self.config.m * (likelihood_term + reg_term)
        
        if target is not None:
            epsilon = target - F_n
            # FAST adaptation with reasonable bounds
            epsilon_clipped = np.clip(epsilon, -1.5, 1.5)
            self.k += self.config.alpha * np.sign(epsilon_clipped) * (np.abs(epsilon_clipped) ** self.config.beta)
            self.k = np.clip(self.k, 0.3, 2.5)  # Wider bounds for more freedom
            self.history['errors'].append(epsilon)
        
        self.history['F'].append(F_n)
        self.history['k'].append(self.k)
        
        self.F_prev = F_n
        self.I_prev = I_n
        
        return F_n
    
    def reset(self):
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': [], 'errors': [], 'delta_I': []}


# =============================================================================
# BASELINES (unchanged)
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
# ENVIRONMENTS
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
# METRICS
# =============================================================================

def calculate_mse(predictions: np.ndarray, targets: np.ndarray) -> float:
    return np.mean((predictions - targets) ** 2)

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
# THE FINAL SHOWDOWN
# =============================================================================

def run_final_simulation(n_steps: int = 500, n_trials: int = 50, seed: int = 42) -> dict:
    """
    Run the FINAL comparison: v1.0 vs v2.0 vs v2.1 vs Baselines
    """
    np.random.seed(seed)
    
    results = {
        'stationary': {'DDA_v2.1': [], 'DDA_v2.0': [], 'DDA_v1.0': [], 'StaticBayes': [], 'EMA': []},
        'nonstationary': {'DDA_v2.1': [], 'DDA_v2.0': [], 'DDA_v1.0': [], 'StaticBayes': [], 'EMA': []},
        'convergence': {'DDA_v2.1': [], 'DDA_v2.0': [], 'DDA_v1.0': [], 'StaticBayes': [], 'EMA': []},
        'adaptation_lag': {'DDA_v2.1': [], 'DDA_v2.0': [], 'DDA_v1.0': [], 'StaticBayes': [], 'EMA': []}
    }
    
    # All configs
    config_v1 = DDAConfig(P0=0.7, m=0.3, alpha=0.01, beta=0.5, 
                          derivative_gain=0.2, use_ema_filter=False)
    config_v2 = DDAConfig(P0=0.85, m=0.15, alpha=0.005, beta=0.5,
                          derivative_gain=0.05, use_ema_filter=True, ema_alpha=0.3)
    config_v21 = DDAConfig(P0=0.75, m=0.25, alpha=0.02, beta=0.5,
                           derivative_gain=0.10, use_ema_filter=True, ema_alpha=0.3)  # GOLDILOCKS!
    
    for trial in range(n_trials):
        dda_v21 = DDAUpdateV21(config_v21)  # THE CONTENDER
        dda_v2 = DDAUpdateV21(config_v2)
        dda_v1 = DDAUpdateV21(config_v1)
        static_bayes = StaticBayesEstimator(prior_weight=0.7)
        ema = ExponentialMovingAverage(alpha=0.3)
        
        # ===== STATIONARY =====
        targets_stat, obs_stat = generate_stationary_environment(n_steps)
        
        preds = {k: [] for k in ['v21', 'v2', 'v1', 'sb', 'ema']}
        for i in range(n_steps):
            preds['v21'].append(dda_v21.update(obs_stat[i], target=targets_stat[i]))
            preds['v2'].append(dda_v2.update(obs_stat[i], target=targets_stat[i]))
            preds['v1'].append(dda_v1.update(obs_stat[i], target=targets_stat[i]))
            preds['sb'].append(static_bayes.update(obs_stat[i]))
            preds['ema'].append(ema.update(obs_stat[i]))
        
        results['stationary']['DDA_v2.1'].append(calculate_mse(np.array(preds['v21']), targets_stat))
        results['stationary']['DDA_v2.0'].append(calculate_mse(np.array(preds['v2']), targets_stat))
        results['stationary']['DDA_v1.0'].append(calculate_mse(np.array(preds['v1']), targets_stat))
        results['stationary']['StaticBayes'].append(calculate_mse(np.array(preds['sb']), targets_stat))
        results['stationary']['EMA'].append(calculate_mse(np.array(preds['ema']), targets_stat))
        
        # Convergence
        for name, pred_list in [('DDA_v2.1', 'v21'), ('DDA_v2.0', 'v2'), ('DDA_v1.0', 'v1'), 
                                 ('StaticBayes', 'sb'), ('EMA', 'ema')]:
            errors = np.array(preds[pred_list]) - targets_stat
            results['convergence'][name].append(calculate_convergence_iteration(errors))
        
        # Reset
        for algo in [dda_v21, dda_v2, dda_v1, static_bayes, ema]:
            algo.reset()
        
        # ===== NON-STATIONARY =====
        targets_ns, obs_ns = generate_nonstationary_environment(n_steps)
        
        preds = {k: [] for k in ['v21', 'v2', 'v1', 'sb', 'ema']}
        for i in range(n_steps):
            preds['v21'].append(dda_v21.update(obs_ns[i], target=targets_ns[i]))
            preds['v2'].append(dda_v2.update(obs_ns[i], target=targets_ns[i]))
            preds['v1'].append(dda_v1.update(obs_ns[i], target=targets_ns[i]))
            preds['sb'].append(static_bayes.update(obs_ns[i]))
            preds['ema'].append(ema.update(obs_ns[i]))
        
        results['nonstationary']['DDA_v2.1'].append(calculate_mse(np.array(preds['v21']), targets_ns))
        results['nonstationary']['DDA_v2.0'].append(calculate_mse(np.array(preds['v2']), targets_ns))
        results['nonstationary']['DDA_v1.0'].append(calculate_mse(np.array(preds['v1']), targets_ns))
        results['nonstationary']['StaticBayes'].append(calculate_mse(np.array(preds['sb']), targets_ns))
        results['nonstationary']['EMA'].append(calculate_mse(np.array(preds['ema']), targets_ns))
        
        # Adaptation lag
        peaks = [i for i in range(1, n_steps-1) 
                 if targets_ns[i] > targets_ns[i-1] and targets_ns[i] > targets_ns[i+1]][:10]
        
        for name, pred_list in [('DDA_v2.1', 'v21'), ('DDA_v2.0', 'v2'), ('DDA_v1.0', 'v1'),
                                 ('StaticBayes', 'sb'), ('EMA', 'ema')]:
            results['adaptation_lag'][name].append(
                calculate_adaptation_lag(np.array(preds[pred_list]), targets_ns, peaks))
    
    # Aggregate
    final = {}
    for metric in results:
        final[metric] = {}
        for algo in results[metric]:
            vals = results[metric][algo]
            final[metric][algo] = {'mean': np.mean(vals), 'std': np.std(vals)}
    
    return final


def print_final_results(results: dict):
    """Print the FINAL championship table."""
    print("\n" + "="*100)
    print("🏆 TABLE 1: FINAL RESULTS - DDA v2.1 'Goldilocks' vs All Competitors")
    print("="*100)
    print(f"{'Metric':<22} {'DDA v2.1':<16} {'DDA v2.0':<16} {'DDA v1.0':<16} {'StaticBayes':<14} {'EMA':<14}")
    print(f"{'':22} {'(GOLDILOCKS)':<16} {'(over-damped)':<16} {'(jittery)':<16} {'':14} {'':14}")
    print("-"*100)
    
    for metric_name, display_name in [
        ('stationary', 'MSE (stationary)'),
        ('nonstationary', 'MSE (non-stat)'),
        ('convergence', 'Convergence'),
        ('adaptation_lag', 'Adapt. lag')
    ]:
        row_data = []
        for algo in ['DDA_v2.1', 'DDA_v2.0', 'DDA_v1.0', 'StaticBayes', 'EMA']:
            row_data.append(results[metric_name][algo])
        
        means = [d['mean'] for d in row_data]
        winner_idx = np.argmin(means)
        
        row = f"{display_name:<22}"
        for idx, d in enumerate(row_data):
            marker = "✓" if idx == winner_idx else " "
            row += f"{d['mean']:.4f}±{d['std']:.3f}{marker}  "
        print(row)
    
    print("="*100)
    print("✓ = Best performance | Target: Beat EMA's non-stationary MSE of ~0.028")
    print("="*100)


def plot_final_comparison(n_steps: int = 500):
    """Generate the FINAL comparison figure."""
    np.random.seed(42)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    config_v1 = DDAConfig(P0=0.7, m=0.3, alpha=0.01, derivative_gain=0.2, use_ema_filter=False)
    config_v2 = DDAConfig(P0=0.85, m=0.15, alpha=0.005, derivative_gain=0.05, use_ema_filter=True)
    config_v21 = DDAConfig(P0=0.75, m=0.25, alpha=0.02, derivative_gain=0.10, use_ema_filter=True)
    
    dda_v1 = DDAUpdateV21(config_v1)
    dda_v2 = DDAUpdateV21(config_v2)
    dda_v21 = DDAUpdateV21(config_v21)
    ema = ExponentialMovingAverage(alpha=0.3)
    sb = StaticBayesEstimator(prior_weight=0.7)
    
    targets, observations = generate_nonstationary_environment(n_steps)
    
    preds = {'v1': [], 'v2': [], 'v21': [], 'ema': [], 'sb': []}
    for i in range(n_steps):
        preds['v1'].append(dda_v1.update(observations[i], target=targets[i]))
        preds['v2'].append(dda_v2.update(observations[i], target=targets[i]))
        preds['v21'].append(dda_v21.update(observations[i], target=targets[i]))
        preds['ema'].append(ema.update(observations[i]))
        preds['sb'].append(sb.update(observations[i]))
    
    for k in preds:
        preds[k] = np.array(preds[k])
    
    # Plot 1: All versions tracking
    ax1 = axes[0, 0]
    ax1.plot(targets, 'k-', linewidth=2.5, label='Target $F^*$')
    ax1.plot(preds['v1'], 'r-', alpha=0.5, linewidth=1, label='v1.0 (jittery)')
    ax1.plot(preds['v2'], 'orange', alpha=0.5, linewidth=1, label='v2.0 (sluggish)')
    ax1.plot(preds['v21'], 'b-', linewidth=1.5, label='v2.1 (Goldilocks) ⭐')
    ax1.set_xlabel('Time step')
    ax1.set_ylabel('Value')
    ax1.set_title('(a) DDA Evolution: v1.0 → v2.0 → v2.1')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: v2.1 vs baselines
    ax2 = axes[0, 1]
    ax2.plot(targets, 'k-', linewidth=2.5, label='Target')
    ax2.plot(preds['v21'], 'b-', linewidth=1.5, label=f"DDA v2.1 (MSE:{calculate_mse(preds['v21'], targets):.4f})")
    ax2.plot(preds['ema'], 'g--', linewidth=1.5, label=f"EMA (MSE:{calculate_mse(preds['ema'], targets):.4f})")
    ax2.plot(preds['sb'], 'm:', linewidth=1.5, label=f"Static Bayes (MSE:{calculate_mse(preds['sb'], targets):.4f})")
    ax2.set_xlabel('Time step')
    ax2.set_ylabel('Value')
    ax2.set_title('(b) v2.1 vs Baselines')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling MSE
    ax3 = axes[1, 0]
    window = 20
    for name, pred, color, style in [('v1.0', preds['v1'], 'red', '-'),
                                      ('v2.0', preds['v2'], 'orange', '-'),
                                      ('v2.1', preds['v21'], 'blue', '-'),
                                      ('EMA', preds['ema'], 'green', '--'),
                                      ('SB', preds['sb'], 'magenta', ':')]:
        mse = np.convolve((pred - targets)**2, np.ones(window)/window, mode='valid')
        ax3.plot(mse, color=color, linestyle=style, linewidth=1.5, label=f'{name} (avg:{np.mean(mse):.4f})')
    
    ax3.set_xlabel('Time step')
    ax3.set_ylabel('Rolling MSE (window=20)')
    ax3.set_title('(c) Rolling MSE Comparison')
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: k evolution
    ax4 = axes[1, 1]
    ax4.plot(dda_v1.history['k'], 'r-', alpha=0.5, label='v1.0')
    ax4.plot(dda_v2.history['k'], 'orange', alpha=0.5, label='v2.0')
    ax4.plot(dda_v21.history['k'], 'b-', linewidth=1.5, label='v2.1 ⭐')
    ax4.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    ax4.set_xlabel('Time step')
    ax4.set_ylabel('Scaling factor $k_n$')
    ax4.set_title('(d) Adaptive k: Fast but Stable in v2.1')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('Figure 5: DDA v2.1 "Goldilocks" - Final Results', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('dda_final_v21.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.show()
    print("✓ Saved: dda_final_v21.png")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("="*100)
    print("🏆 DYNAMIC DECISION ALGORITHM (DDA) - v2.1 'GOLDILOCKS' FINAL RUN")
    print("="*100)
    print("\nVersion Evolution:")
    print("  v1.0: P0=0.70, α=0.010, deriv=0.20, filter=OFF  → Fast but JITTERY")
    print("  v2.0: P0=0.85, α=0.005, deriv=0.05, filter=ON   → Smooth but SLUGGISH")
    print("  v2.1: P0=0.75, α=0.020, deriv=0.10, filter=ON   → GOLDILOCKS! 🎯")
    
    print("\n[1/2] Running FINAL Monte Carlo simulations (50 trials)...")
    results = run_final_simulation(n_steps=500, n_trials=50, seed=42)
    print_final_results(results)
    
    print("\n[2/2] Generating FINAL comparison plots...")
    plot_final_comparison()
    
    print("\n" + "="*100)
    print("🏁 FINAL RUN COMPLETE!")
    print("="*100)
