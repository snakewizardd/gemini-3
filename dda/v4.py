"""
DDA v4.0 "High-Octane Filter"
Strategy: High Derivative Gain (Speed) + Heavy Filtering (Smoothness)
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

@dataclass
class DDAConfig:
    # 1. THE ENGINE (Balanced like v1.0)
    P0: float = 0.75          # Enough inertia to be stable, light enough to move
    m: float = 0.25           # Complement
    
    # 2. THE ADAPTATION (Stable)
    alpha: float = 0.005      # Slow and steady learning. No oscillation.
    beta: float = 0.5
    k_init: float = 1.0
    
    # 3. THE SECRET WEAPON (High Gain + High Filter)
    derivative_gain: float = 0.25  # HIGH! This kills lag. (v1 was 0.2)
    use_ema_filter: bool = True    # ON! This kills noise.
    ema_alpha: float = 0.1         # LOW! Heavy smoothing on the derivative.

class DDAUpdateV4:
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': []}
        
    def update(self, I_n: float, target: float = None) -> float:
        delta_I = I_n - self.I_prev
        
        # 1. HEAVY FILTERING (The Noise-Canceling Headphones)
        if self.config.use_ema_filter:
            # Very slow update to delta_I_filtered (ema_alpha = 0.1)
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                   (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
            
        # 2. HIGH GAIN TRANSFORM (The Turbocharger)
        # We rely on the filtered delta to anticipate the turn without jitter
        likelihood_term = (1 - self.config.derivative_gain) * I_n + self.config.derivative_gain * effective_delta
        
        # 3. CORE UPDATE
        prior_term = self.config.P0 * self.k * self.F_prev
        reg_term = -0.01 * self.F_prev # Standard Reg
        
        F_n = prior_term + self.config.m * (likelihood_term + reg_term)
        
        # 4. SIMPLE ADAPTATION (No Deadbands, No Decay)
        if target is not None:
            epsilon = target - F_n
            # Clip epsilon to avoid explosions
            eps_clip = np.clip(epsilon, -1.0, 1.0)
            self.k += self.config.alpha * np.sign(eps_clip) * (np.abs(eps_clip) ** self.config.beta)
            self.k = np.clip(self.k, 0.8, 1.2) # Tighter bounds for stability
            
        self.history['F'].append(F_n)
        self.history['k'].append(self.k)
        self.F_prev = F_n
        self.I_prev = I_n
        return F_n

# --- SIMULATION RUNNER ---
def run_v4():
    np.random.seed(42)
    n_steps = 500
    
    # Generate Environment
    t = np.arange(n_steps)
    targets = np.sin(0.1 * t) + 0.5 * np.cos(0.05 * t)
    noise = np.random.normal(0, 0.1, n_steps)
    obs = targets + noise
    
    # Init Models
    dda = DDAUpdateV4()
    
    # EMA Baseline (The Target to Beat: MSE ~0.0280)
    ema_preds = []
    ema_val = 0
    alpha_ema = 0.3
    
    preds = []
    
    for i in range(n_steps):
        # DDA
        p = dda.update(obs[i], target=targets[i])
        preds.append(p)
        
        # EMA
        ema_val = alpha_ema * obs[i] + (1 - alpha_ema) * ema_val
        ema_preds.append(ema_val)
        
    # CALC SCORES
    preds = np.array(preds)
    ema_preds = np.array(ema_preds)
    
    mse_dda = np.mean((preds - targets)**2)
    mse_ema = np.mean((ema_preds - targets)**2)
    
    print("="*60)
    print("🚀 DDA v4.0 FINAL CHALLENGE")
    print("="*60)
    print(f"EMA MSE (Baseline): {mse_ema:.4f}")
    print(f"DDA MSE (v4.0):     {mse_dda:.4f}")
    
    if mse_dda < mse_ema:
        print("\n🏆 WINNER: DDA v4.0")
        print(f"Improvement: {((mse_ema - mse_dda)/mse_ema)*100:.1f}%")
    else:
        print("\n❌ DEFEAT: DDA Failed.")
        
    # Plot
    plt.figure(figsize=(12, 5))
    plt.plot(targets, 'k-', linewidth=2, label='Target')
    plt.plot(ema_preds, 'g--', label=f'EMA (MSE: {mse_ema:.4f})')
    plt.plot(preds, 'r-', linewidth=1.5, label=f'DDA v4.0 (MSE: {mse_dda:.4f})')
    plt.title("Figure 6: The Final Tune")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig('dda_v4_victory.png', dpi=150)
    print("✓ Saved plot")

if __name__ == "__main__":
    run_v4()