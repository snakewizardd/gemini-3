"""
DDA v5.0 "Unity Gain"
The Fix: Additive Derivative Term (Preserves Amplitude) + EMA Smoothing
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class DDAConfig:
    P0: float = 0.80           # High Inertia (Smoothness)
    m: float = 0.20            # Standard update weight
    alpha: float = 0.01        # Moderate adaptation
    beta: float = 0.5
    k_init: float = 1.0
    
    # THE FIX:
    # We will NOT use a mix ratio. We will use a raw multiplier for delta.
    derivative_boost: float = 1.5  # Aggressive kick to kill lag
    use_ema_filter: bool = True
    ema_alpha: float = 0.15        # Good noise filtering

class DDAUpdateV5:
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': []}
        
    def update(self, I_n: float, target: float = None) -> float:
        delta_I = I_n - self.I_prev
        
        # 1. FILTER THE DERIVATIVE (Noise control)
        if self.config.use_ema_filter:
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                   (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
            
        # 2. UNITY GAIN LIKELIHOOD (The Fix)
        # We take 100% of I_n, and ADD the boost.
        # Structure: I_n + (Boost * Delta)
        likelihood_term = I_n + (self.config.derivative_boost * effective_delta)
        
        # 3. UPDATE LAW
        # F_n = P0 * k * F_prev + m * Likelihood
        prior_term = self.config.P0 * self.k * self.F_prev
        
        # No Regularization (It hurts tracking)
        F_n = prior_term + self.config.m * likelihood_term
        
        # 4. ADAPTATION
        if target is not None:
            epsilon = target - F_n
            # Standard adaptation
            self.k += self.config.alpha * np.sign(epsilon) * (np.abs(epsilon) ** self.config.beta)
            self.k = np.clip(self.k, 0.9, 1.1) # Tight bounds are fine now that math is fixed
            
        self.history['F'].append(F_n)
        self.history['k'].append(self.k)
        self.F_prev = F_n
        self.I_prev = I_n
        return F_n

def run_v5():
    np.random.seed(42) # Consistent seed
    n_steps = 500
    t = np.arange(n_steps)
    targets = np.sin(0.1 * t) + 0.5 * np.cos(0.05 * t)
    noise = np.random.normal(0, 0.1, n_steps)
    obs = targets + noise
    
    dda = DDAUpdateV5()
    
    # EMA Baseline
    ema_preds = []
    ema_val = 0
    alpha_ema = 0.3
    preds = []
    
    for i in range(n_steps):
        p = dda.update(obs[i], target=targets[i])
        preds.append(p)
        ema_val = alpha_ema * obs[i] + (1 - alpha_ema) * ema_val
        ema_preds.append(ema_val)
        
    preds = np.array(preds)
    ema_preds = np.array(ema_preds)
    
    mse_dda = np.mean((preds - targets)**2)
    mse_ema = np.mean((ema_preds - targets)**2)
    
    print("="*60)
    print("🌟 DDA v5.0 UNITY GAIN")
    print("="*60)
    print(f"EMA MSE: {mse_ema:.4f}")
    print(f"DDA MSE: {mse_dda:.4f}")
    
    if mse_dda < mse_ema:
        print("\n🏆 WINNER: DDA v5.0")
        print(f"Improvement: {((mse_ema - mse_dda)/mse_ema)*100:.1f}%")
    else:
        print("\n❌ DEFEAT")

    plt.figure(figsize=(12, 5))
    plt.plot(targets, 'k-', linewidth=2, label='Target')
    plt.plot(ema_preds, 'g--', label=f'EMA ({mse_ema:.4f})')
    plt.plot(preds, 'r-', linewidth=1.5, label=f'DDA v5.0 ({mse_dda:.4f})')
    plt.title("Figure 7: Unity Gain Restoration")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig('dda_v5_unity.png', dpi=150)
    print("✓ Plot saved")

if __name__ == "__main__":
    run_v5()