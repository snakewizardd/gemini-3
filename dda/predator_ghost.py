"""
DDA v9.2 "GHOST HUNTER" (Dead Reckoning + Saccades)
---------------------------------------------------
The Final Evolution.
Adds "Object Permanence" to the Predator.

1. Dead Reckoning: If signal freezes, coast on last known velocity.
2. Saccadic Gating: If signal jumps, snap instantly.
3. Pre-Cognition: If signal is live, boost to kill lag.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

@dataclass
class DDAConfig:
    P0_pursuit: float = 0.95
    P0_saccade: float = 0.0
    saccade_thresh: float = 4.0
    derivative_boost: float = 0.55
    use_ema_filter: bool = True
    ema_alpha: float = 0.2

class DDA_GhostHunter:
    def __init__(self):
        self.c = DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.dF = 0.0         # Filtered Derivative
        self.last_valid_dF = 0.0 # Memory for Dead Reckoning
        self.init = False
        
    def update(self, I_n):
        if not self.init:
            self.F_prev = I_n; self.I_prev = I_n; self.init = True
            return I_n, 0

        # --- 1. DETECT SIGNAL FREEZE (PACKET LOSS) ---
        # If input is EXACTLY same as last frame, it's a digital freeze
        is_frozen = (I_n == self.I_prev)
        
        if is_frozen:
            # MODE: DEAD RECKONING (Coast)
            # Ignore the frozen input. Add the last known momentum.
            F = self.F_prev + self.last_valid_dF
            
            # We treat this as a "Simulated Pursuit" mode
            self.F_prev = F
            # Do NOT update I_prev (keep it for delta calc when signal returns)
            return F, 2 # Mode 2 = Coasting
            
        # --- SIGNAL IS LIVE ---
        
        # 1. Calc Derivative
        # Note: I_prev is the last *different* value, so delta is the jump
        delta = I_n - self.I_prev
        
        if self.c.use_ema_filter:
            self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
        else: self.dF = delta
        
        # Update memory for future coasts
        self.last_valid_dF = self.dF

        # 2. Retinal Slip
        # How far is the new signal from where we coasted to?
        error = np.abs(I_n - self.F_prev)
        
        # 3. Saccadic Gate
        if error > self.c.saccade_thresh:
            # SNAP RECOVERY
            effective_P0 = self.c.P0_saccade
            effective_m = 1.0
            mode = 1 # Saccade
            self.dF = 0.0 # Reset momentum
            self.last_valid_dF = 0.0
        else:
            # SMOOTH PURSUIT
            effective_P0 = self.c.P0_pursuit
            effective_m = 1.0 - effective_P0
            mode = 0 # Pursuit

        # 4. Update Law
        if mode == 0:
            L = I_n + (self.c.derivative_boost * self.dF)
        else:
            L = I_n
            
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (effective_m * L)
        
        # 5. Adapt
        if mode == 0:
            err = I_n - F
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0
            
        self.F_prev = F
        self.I_prev = I_n
        return F, mode

# --- COMPETITOR ---
class KalmanFilter:
    def __init__(self, dt=1.0, std_meas=2.0):
        self.x = np.zeros((2, 1))
        self.F = np.array([[1, dt], [0, 1]])
        self.H = np.array([[1, 0]])
        self.P = np.eye(2)
        self.R = np.eye(1) * std_meas**2
        self.Q = np.eye(2) * 0.1

    def update(self, z):
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(2) - np.dot(K, self.H)), self.P)
        return self.x[0,0]

# --- SIMULATION ---
def run_ghost_hunter():
    print("👻 GHOST HUNTER v9.2: ENGAGING...")
    np.random.seed(999)
    steps = 500
    
    # 1. True Path
    t = np.linspace(0, 20, steps)
    true_path = 10 * np.sin(t) + 5 * np.cos(2*t)
    
    # 2. Laggy Feed
    obs = []
    current_val = true_path[0]
    lag_timer = 0
    in_lag = False
    
    for i in range(steps):
        # 10% chance of 20-frame lag
        if not in_lag and np.random.random() > 0.95:
            in_lag = True; lag_timer = 20
            
        if in_lag:
            obs.append(current_val) # Freeze
            lag_timer -= 1
            if lag_timer <= 0: in_lag = False
        else:
            current_val = true_path[i] + np.random.normal(0, 0.5)
            obs.append(current_val)
            
    obs = np.array(obs)
    
    # 3. Track
    dda = DDA_GhostHunter()
    kf = KalmanFilter(std_meas=2.0)
    
    path_dda, modes, path_kf = [], [], []
    
    for i in range(steps):
        d, m = dda.update(obs[i])
        k = kf.update(np.array([[obs[i]]]))
        path_dda.append(d)
        modes.append(m)
        path_kf.append(k)
        
    path_dda = np.array(path_dda)
    path_kf = np.array(path_kf)
    
    # 4. Score
    mse_dda = np.mean((true_path - path_dda)**2)
    mse_kf = np.mean((true_path - path_kf)**2)
    
    print("\n" + "="*60)
    print("RESULTS: DEAD RECKONING BATTLE")
    print("="*60)
    print(f"Kalman MSE: {mse_kf:.4f}")
    print(f"DDA v9.2:   {mse_dda:.4f}")
    
    if mse_dda < mse_kf:
        imp = (mse_kf - mse_dda)/mse_kf * 100
        print(f"\n🏆 WINNER: DDA v9.2 (+{imp:.1f}%)")
    else:
        print("\n🏆 WINNER: KALMAN")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax1.plot(true_path, 'k-', lw=3, alpha=0.3, label='TRUTH')
    ax1.plot(obs, 'k.', ms=2, alpha=0.2, label='Frozen Feed')
    ax1.plot(path_kf, 'g--', lw=1.5, label='Kalman')
    ax1.plot(path_dda, 'r-', lw=2, label='DDA v9.2')
    ax1.set_title("DDA Ghost Hunter vs Kalman")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Mode Plot
    ax2.plot(modes, 'b-', lw=1, alpha=0.8, label='State')
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(['Pursuit', 'Saccade', 'Coasting'])
    ax2.set_title("DDA Internal Brain State")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_ghost_hunter.png', dpi=150)
    print("✓ Evidence saved.")

if __name__ == "__main__":
    run_ghost_hunter()