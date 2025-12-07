"""
DDA v6.0 Validation Suite
Proof of Strength: Step Response, High Noise, and Error Distribution
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# --- REUSE DDA v6.0 CLASS (The Winner) ---
@dataclass
class DDAConfig:
    P0: float = 0.70
    m: float = 0.30
    alpha: float = 0.001
    beta: float = 0.5
    k_init: float = 1.0
    derivative_boost: float = 0.6  
    use_ema_filter: bool = True
    ema_alpha: float = 0.1

class DDAUpdateV6:
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': []}
        
    def update(self, I_n: float, target: float = None) -> float:
        delta_I = I_n - self.I_prev
        if self.config.use_ema_filter:
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                   (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
            
        likelihood_term = I_n + (self.config.derivative_boost * effective_delta)
        prior_term = self.config.P0 * self.k * self.F_prev
        F_n = prior_term + self.config.m * likelihood_term
        
        if target is not None:
            epsilon = target - F_n
            self.k += self.config.alpha * np.sign(epsilon) * (np.abs(epsilon) ** self.config.beta)
            self.k = np.clip(self.k, 0.9, 1.1)
            
        self.history['F'].append(F_n)
        self.history['k'].append(self.k)
        self.F_prev = F_n
        self.I_prev = I_n
        return F_n

# --- STRESS TEST RUNNER ---
def run_stress_tests():
    np.random.seed(42)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # TEST 1: STEP RESPONSE (The "Shock" Test)
    # Target goes from 0 to 1 instantly at step 50
    steps = 200
    targets_step = np.zeros(steps)
    targets_step[50:] = 1.0
    obs_step = targets_step + np.random.normal(0, 0.05, steps) # Low noise to see dynamics
    
    dda_step = DDAUpdateV6()
    ema_val = 0
    preds_step = []
    ema_preds_step = []
    
    for i in range(steps):
        preds_step.append(dda_step.update(obs_step[i], targets_step[i]))
        ema_val = 0.3 * obs_step[i] + 0.7 * ema_val
        ema_preds_step.append(ema_val)
        
    axes[0].plot(targets_step, 'k-', label='Target')
    axes[0].plot(ema_preds_step, 'g--', label='EMA (Slow)')
    axes[0].plot(preds_step, 'r-', linewidth=2, label='DDA v6.0 (Fast)')
    axes[0].set_title("Proof 1: Step Response (Agility)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    
    # TEST 2: HIGH NOISE (The "Robustness" Test)
    # Sine wave with 3x Noise (std=0.3 instead of 0.1)
    steps = 300
    t = np.arange(steps)
    targets_noise = np.sin(0.1 * t)
    noise_heavy = np.random.normal(0, 0.3, steps) # HEAVY NOISE
    obs_noise = targets_noise + noise_heavy
    
    dda_noise = DDAUpdateV6()
    preds_noise = []
    
    for i in range(steps):
        preds_noise.append(dda_noise.update(obs_noise[i], targets_noise[i]))
        
    axes[1].plot(targets_noise, 'k-', linewidth=2, label='Target')
    axes[1].plot(obs_noise, 'b.', alpha=0.1, label='Noisy Input')
    axes[1].plot(preds_noise, 'r-', linewidth=1.5, label='DDA v6.0')
    axes[1].set_title("Proof 2: High Noise Rejection")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    
    # TEST 3: RESIDUALS (The "Honesty" Test)
    # Are errors normally distributed?
    errors = np.array(preds_noise) - targets_noise
    axes[2].hist(errors, bins=30, color='red', alpha=0.7, density=True, label='DDA Errors')
    
    # Plot normal curve for comparison
    mu, std = 0, 0.1 # theoretical ideal
    x = np.linspace(-1, 1, 100)
    p = (1/(std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu)/std)**2)
    axes[2].plot(x, p, 'k--', linewidth=1, label='Ideal Gaussian')
    
    axes[2].set_title("Proof 3: Error Distribution")
    axes[2].set_xlabel("Error Magnitude")
    axes[2].legend()
    axes[2].grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_proofs_v7.png', dpi=150)
    print("✓ Stress Tests Complete. Plot saved.")

if __name__ == "__main__":
    run_stress_tests()