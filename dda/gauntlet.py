"""
DDA v6.0 "THE GAUNTLET"
Proof of Generalization: Flash Crashes, Heartbeats, and Random Walks.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# --- THE CHAMPION: DDA v6.0 ---
@dataclass
class DDAConfig:
    P0: float = 0.70
    m: float = 0.30
    alpha: float = 0.001
    beta: float = 0.5
    derivative_boost: float = 0.6  
    use_ema_filter: bool = True
    ema_alpha: float = 0.1

class DDAUpdate:
    def __init__(self):
        self.config = DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_filtered = 0.0
        
    def update(self, I_n):
        delta_raw = I_n - self.I_prev
        
        # 1. Input Filter
        self.delta_filtered = (self.config.ema_alpha * delta_raw + 
                             (1 - self.config.ema_alpha) * self.delta_filtered)
        
        # 2. Pre-Cognitive Boost
        likelihood = I_n + (self.config.derivative_boost * self.delta_filtered)
        
        # 3. Update
        prior = self.config.P0 * self.k * self.F_prev
        F_n = prior + self.config.m * likelihood
        
        # 4. Simple Adaptation (Background Learning)
        self.k += 0.001 * np.sign(I_n - F_n) * (np.abs(I_n - F_n)**0.5)
        self.k = np.clip(self.k, 0.9, 1.1)
        
        self.F_prev = F_n
        self.I_prev = I_n
        return F_n

# --- THE CHALLENGERS ---
def run_gauntlet():
    np.random.seed(999) # New seed, new chaos
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))
    
    # === SCENARIO 1: THE FLASH CRASH ===
    steps = 400
    # Slow climb then DROP
    market = np.linspace(100, 150, 200)
    crash = np.linspace(150, 80, 10) # Instant drop
    recovery = np.linspace(80, 120, 190) + np.random.normal(0, 2, 190) # Volatile recovery
    data_crash = np.concatenate([market, crash, recovery])
    
    # === SCENARIO 2: THE HEARTBEAT ===
    data_pulse = np.zeros(steps)
    # Random spikes
    idx = np.random.choice(range(steps), 10, replace=False)
    data_pulse[idx] = 5.0 # Massive spikes
    data_pulse += np.random.normal(0, 0.1, steps)
    
    # === SCENARIO 3: THE DRUNK BIRD (Random Walk) ===
    data_walk = np.cumsum(np.random.normal(0, 0.5, steps))
    
    scenarios = [
        ("The Flash Crash", data_crash, axes[0]),
        ("The Heartbeat (Spike Rejection)", data_pulse, axes[1]),
        ("The Drunk Bird (Random Walk)", data_walk, axes[2])
    ]
    
    print(f"{'SCENARIO':<30} | {'EMA MSE':<10} | {'DDA MSE':<10} | {'WINNER'}")
    print("-" * 65)

    for name, data, ax in scenarios:
        # Run Models
        dda = DDAUpdate()
        dda_out = []
        ema_out = []
        ema_val = data[0]
        
        for x in data:
            # DDA
            dda_out.append(dda.update(x))
            # EMA (Standard 0.3 alpha)
            ema_val = 0.3 * x + 0.7 * ema_val
            ema_out.append(ema_val)
            
        # Calc Errors
        mse_dda = np.mean((data - dda_out)**2)
        mse_ema = np.mean((data - ema_out)**2)
        
        # Determine Winner
        if mse_dda < mse_ema:
            winner = "🏆 DDA"
            improvement = (mse_ema - mse_dda) / mse_ema * 100
            res_str = f"{winner} (+{improvement:.1f}%)"
        else:
            res_str = "❌ EMA"
            
        print(f"{name:<30} | {mse_ema:<10.4f} | {mse_dda:<10.4f} | {res_str}")
        
        # Plot
        ax.plot(data, 'k-', alpha=0.5, linewidth=3, label='Truth')
        ax.plot(ema_out, 'g--', linewidth=1.5, label=f'EMA (Laggy)')
        ax.plot(dda_out, 'r-', linewidth=1.5, label=f'DDA v6.0')
        ax.set_title(f"{name} - {res_str}")
        ax.legend()
        ax.grid(alpha=0.3)
        
    plt.tight_layout()
    plt.savefig('dda_gauntlet.png', dpi=150)
    print("\n✓ Visualization saved to dda_gauntlet.png")

if __name__ == "__main__":
    run_gauntlet()