"""
DDA v7.0 "PRODUCTION READY"
Fixes: Warm-Start (Initialization) + Derivative Clamping (Safety)
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class DDAConfig:
    P0: float = 0.70
    m: float = 0.30
    alpha: float = 0.001
    beta: float = 0.5
    derivative_boost: float = 0.6  
    use_ema_filter: bool = True
    ema_alpha: float = 0.1
    # NEW SAFETY PARAM
    boost_cap: float = 10.0 # Max absolute boost allowed per step

class DDAUpdate:
    def __init__(self, config: DDAConfig = None):
        self.config = config or DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_filtered = 0.0
        self.initialized = False  # WARM START FLAG
        
    def update(self, I_n):
        # 1. WARM START (Fixes the MSE bug)
        if not self.initialized:
            self.F_prev = I_n
            self.I_prev = I_n
            self.initialized = True
            return I_n
            
        delta_raw = I_n - self.I_prev
        
        # 2. Input Filter
        self.delta_filtered = (self.config.ema_alpha * delta_raw + 
                             (1 - self.config.ema_alpha) * self.delta_filtered)
        
        # 3. Pre-Cognitive Boost with SAFETY CLAMP
        raw_boost = self.config.derivative_boost * self.delta_filtered
        # Soft saturation (tanh) prevents infinite spikes during flash crashes
        clamped_boost = self.config.boost_cap * np.tanh(raw_boost / self.config.boost_cap)
        
        likelihood = I_n + clamped_boost
        
        # 4. Update
        prior = self.config.P0 * self.k * self.F_prev
        F_n = prior + self.config.m * likelihood
        
        # 5. Adaptation
        self.k += 0.001 * np.sign(I_n - F_n) * (np.abs(I_n - F_n)**0.5)
        self.k = np.clip(self.k, 0.9, 1.1)
        
        self.F_prev = F_n
        self.I_prev = I_n
        return F_n

# --- THE GAUNTLET RELOADED ---
def run_final_proof():
    np.random.seed(999) 
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))
    
    # SCENARIOS
    steps = 400
    market = np.linspace(100, 150, 200)
    crash = np.linspace(150, 80, 10) 
    recovery = np.linspace(80, 120, 190) + np.random.normal(0, 2, 190)
    data_crash = np.concatenate([market, crash, recovery])
    
    data_pulse = np.zeros(steps)
    idx = np.random.choice(range(steps), 10, replace=False)
    data_pulse[idx] = 5.0
    data_pulse += np.random.normal(0, 0.1, steps)
    
    data_walk = np.cumsum(np.random.normal(0, 0.5, steps))
    
    scenarios = [
        ("The Flash Crash (Fixed)", data_crash, axes[0]),
        ("The Heartbeat", data_pulse, axes[1]),
        ("The Drunk Bird", data_walk, axes[2])
    ]
    
    print(f"{'SCENARIO':<30} | {'EMA MSE':<10} | {'DDA MSE':<10} | {'WINNER'}")
    print("-" * 65)

    for name, data, ax in scenarios:
        dda = DDAUpdate()
        dda_out = []
        ema_out = []
        # Fix EMA start too for fairness
        ema_val = data[0] 
        
        for x in data:
            dda_out.append(dda.update(x))
            ema_val = 0.3 * x + 0.7 * ema_val
            ema_out.append(ema_val)
            
        mse_dda = np.mean((data - dda_out)**2)
        mse_ema = np.mean((data - ema_out)**2)
        
        if mse_dda < mse_ema:
            res_str = f"🏆 DDA (+{((mse_ema - mse_dda)/mse_ema)*100:.1f}%)"
        else:
            res_str = "❌ EMA"
            
        print(f"{name:<30} | {mse_ema:<10.4f} | {mse_dda:<10.4f} | {res_str}")
        
        ax.plot(data, 'k-', alpha=0.5, linewidth=3, label='Truth')
        ax.plot(ema_out, 'g--', linewidth=1.5, label='EMA')
        ax.plot(dda_out, 'r-', linewidth=1.5, label='DDA v7.0')
        ax.set_title(f"{name}")
        ax.legend()
        ax.grid(alpha=0.3)
        
    plt.tight_layout()
    plt.savefig('dda_final_victory.png', dpi=150)
    print("\n✓ Truth revealed in dda_final_victory.png")

if __name__ == "__main__":
    run_final_proof()