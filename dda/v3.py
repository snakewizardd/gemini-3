
"""DDA v3.0 - The Sniper Strategy: Deadband + Decay"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class DDAConfigV3:
    P0: float = 0.90           # MAX inertia
    m: float = 0.10            # Low input sensitivity
    alpha: float = 0.05        # HIGH aggression (only when needed)
    beta: float = 0.5
    k_init: float = 1.0
    derivative_gain: float = 0.05
    use_ema_filter: bool = True
    ema_alpha: float = 0.2
    noise_threshold: float = 0.15  # DEADBAND
    decay_rate: float = 0.01       # k → 1.0 decay

class DDASniper:
    """v3.0: Ignore noise, strike on shifts."""
    def __init__(self, config=None):
        self.config = config or DDAConfigV3()
        self.k = self.config.k_init
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_I_filtered = 0.0
        self.history = {'F': [], 'k': []}
        
    def update(self, I_n: float, target: float = None) -> float:
        delta_I = I_n - self.I_prev
        
        # EMA filter on delta
        if self.config.use_ema_filter:
            self.delta_I_filtered = (self.config.ema_alpha * delta_I + 
                                     (1 - self.config.ema_alpha) * self.delta_I_filtered)
            effective_delta = self.delta_I_filtered
        else:
            effective_delta = delta_I
        
        # Likelihood transform
        T = (1 - self.config.derivative_gain) * I_n + self.config.derivative_gain * effective_delta
        R = -0.01 * self.F_prev
        
        # DDA core
        F_n = self.config.P0 * self.k * self.F_prev + self.config.m * (T + R)
        
        # 🎯 THE SNIPER LOGIC
        if target is not None:
            epsilon = target - F_n
            
            if np.abs(epsilon) > self.config.noise_threshold:
                # STRUCTURAL SHIFT: Strike hard!
                epsilon_clipped = np.clip(epsilon, -1.0, 1.0)
                self.k += self.config.alpha * np.sign(epsilon_clipped) * (np.abs(epsilon_clipped) ** self.config.beta)
            else:
                # STABLE: Decay k → 1.0
                self.k += self.config.decay_rate * (1.0 - self.k)
            
            self.k = np.clip(self.k, 0.5, 2.0)
        
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
        self.history = {'F': [], 'k': []}

class EMA:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.F_prev = None
    def update(self, I_n):
        self.F_prev = I_n if self.F_prev is None else self.alpha * I_n + (1-self.alpha) * self.F_prev
        return self.F_prev
    def reset(self):
        self.F_prev = None

class StaticBayes:
    def __init__(self, w=0.7):
        self.w = w
        self.F_prev = 0.0
    def update(self, I_n):
        self.F_prev = self.w * self.F_prev + (1-self.w) * I_n
        return self.F_prev
    def reset(self):
        self.F_prev = 0.0

def gen_nonstat(n, noise=0.1):
    t = np.arange(n)
    targets = np.sin(0.1*t) + 0.5*np.cos(0.05*t)
    return targets, targets + np.random.normal(0, noise, n)

def gen_stat(n, noise=0.1):
    targets = np.ones(n)
    return targets, targets + np.random.normal(0, noise, n)

def mse(p, t): return np.mean((p-t)**2)

def run_final(n_steps=500, n_trials=50):
    np.random.seed(42)
    results = {'stat': {'DDA_v3': [], 'EMA': [], 'SB': []},
               'nonstat': {'DDA_v3': [], 'EMA': [], 'SB': []}}
    
    for _ in range(n_trials):
        dda = DDASniper()
        ema = EMA(0.3)
        sb = StaticBayes(0.7)
        
        # Stationary
        t_s, o_s = gen_stat(n_steps)
        p_dda = [dda.update(o_s[i], t_s[i]) for i in range(n_steps)]
        p_ema = [ema.update(o_s[i]) for i in range(n_steps)]
        p_sb = [sb.update(o_s[i]) for i in range(n_steps)]
        
        results['stat']['DDA_v3'].append(mse(np.array(p_dda), t_s))
        results['stat']['EMA'].append(mse(np.array(p_ema), t_s))
        results['stat']['SB'].append(mse(np.array(p_sb), t_s))
        
        dda.reset(); ema.reset(); sb.reset()
        
        # Non-stationary
        t_ns, o_ns = gen_nonstat(n_steps)
        p_dda = [dda.update(o_ns[i], t_ns[i]) for i in range(n_steps)]
        p_ema = [ema.update(o_ns[i]) for i in range(n_steps)]
        p_sb = [sb.update(o_ns[i]) for i in range(n_steps)]
        
        results['nonstat']['DDA_v3'].append(mse(np.array(p_dda), t_ns))
        results['nonstat']['EMA'].append(mse(np.array(p_ema), t_ns))
        results['nonstat']['SB'].append(mse(np.array(p_sb), t_ns))
    
    return results

if __name__ == "__main__":
    print("="*70)
    print("🎯 DDA v3.0 'THE SNIPER' - FINAL RUN")
    print("="*70)
    print("\nStrategy: DEADBAND (ignore noise) + DECAY (k→1) + HIGH α (strike hard)")
    print("Config: P0=0.90, α=0.05, threshold=0.15, decay=0.01\n")
    
    results = run_final()
    
    print("="*70)
    print("🏆 FINAL RESULTS")
    print("="*70)
    print(f"{'Metric':<20} {'DDA v3.0':<18} {'EMA':<18} {'Static Bayes':<18}")
    print("-"*70)
    
    for env, name in [('stat', 'MSE (stationary)'), ('nonstat', 'MSE (non-stat)')]:
        d = np.mean(results[env]['DDA_v3'])
        e = np.mean(results[env]['EMA'])
        s = np.mean(results[env]['SB'])
        winner = '✓' if d == min(d,e,s) else ' '
        print(f"{name:<20} {d:.4f} {winner:<10} {e:.4f}          {s:.4f}")
    
    print("="*70)
    
    # Quick plot
    np.random.seed(42)
    dda = DDASniper()
    ema = EMA(0.3)
    t, o = gen_nonstat(500)
    p_dda = np.array([dda.update(o[i], t[i]) for i in range(500)])
    p_ema = np.array([ema.update(o[i]) for i in range(500)])
    
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].plot(t, 'k-', lw=2, label='Target')
    ax[0].plot(p_dda, 'b-', lw=1.5, label=f'DDA v3.0 (MSE:{mse(p_dda,t):.4f})')
    ax[0].plot(p_ema, 'g--', lw=1.5, label=f'EMA (MSE:{mse(p_ema,t):.4f})')
    ax[0].legend(); ax[0].set_title('🎯 THE SNIPER vs EMA'); ax[0].grid(True, alpha=0.3)
    
    ax[1].plot(dda.history['k'], 'b-', lw=1.5)
    ax[1].axhline(1.0, color='gray', ls='--')
    ax[1].set_title('Adaptive k: Stable with Surgical Strikes'); ax[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_v3_sniper.png', dpi=150)
    print("✓ Saved: dda_v3_sniper.png")
    print("\n🏁 THE SNIPER HAS SPOKEN.")
