"""
DDA v9.1 "GHOST DRONE" (Context-Aware Pre-Cognition)
----------------------------------------------------
Scenario: FPV Drone Tracking with 50% Packet Loss (Lag Switching).
Challenge: Target has MOMENTUM (needs Boost) but connection has GAPS (needs Saccades).

Configuration:
  - Pursuit Mode: P0=0.95, Boost=0.5 (High Stability + Pre-Cognition)
  - Saccade Mode: P0=0.00 (Instant Snap)
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE PREDATOR (DDA v9.1)
# =============================================================================
@dataclass
class DDAConfig:
    P0_pursuit: float = 0.95   # Lock on tight
    P0_saccade: float = 0.0    # Snap instantly
    saccade_thresh: float = 4.0 # Trigger snap on massive jumps
    alpha: float = 0.001       
    beta: float = 0.5
    derivative_boost: float = 0.5 # ENABLED: Drone has momentum!
    use_ema_filter: bool = True
    ema_alpha: float = 0.2     # Moderate filter for motor vibration

class DDA_Predator:
    def __init__(self):
        self.c = DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.dF = 0.0
        self.init = False

    def update(self, I_n):
        if not self.init:
            self.F_prev = I_n; self.I_prev = I_n; self.init = True
            return I_n, 0 # Return tuple to match loop expectations
            
        # 1. Filtered Derivative (Track Velocity)
        delta = I_n - self.I_prev
        if self.c.use_ema_filter:
            self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
        else: self.dF = delta

        # 2. Retinal Slip (Did the target teleport?)
        raw_error = np.abs(I_n - self.F_prev)
        
        # 3. SACCADIC GATING (The Biomimetic Switch)
        if raw_error > self.c.saccade_thresh:
            # MODE: SACCADE (Snap)
            effective_P0 = self.c.P0_saccade
            effective_m = 1.0 
            mode = 1 
            self.dF = 0.0 # Reset momentum on teleport
        else:
            # MODE: PURSUIT (Lock + Boost)
            effective_P0 = self.c.P0_pursuit
            effective_m = 1.0 - effective_P0
            mode = 0 
            
        # 4. Update Law
        # Hybrid: Use Boost in Pursuit, Raw in Saccade
        if mode == 0:
            L = I_n + (self.c.derivative_boost * self.dF)
        else:
            L = I_n 
            
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (effective_m * L)
        
        # 5. Meta-Learning
        if mode == 0:
            err = I_n - F
            self.k += self.c.alpha * np.sign(err) * (np.abs(err)**self.c.beta)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0 # Reset gain on teleport
            
        self.F_prev = F; self.I_prev = I_n
        return F, mode

# =============================================================================
# 2. THE COMPETITOR: KALMAN FILTER
# =============================================================================
class KalmanFilter:
    def __init__(self, dt=1.0, std_meas=2.0):
        self.x = np.zeros((2, 1))
        self.F = np.array([[1, dt], [0, 1]])
        self.H = np.array([[1, 0]])
        self.P = np.eye(2)
        self.R = np.eye(1) * std_meas**2
        self.Q = np.eye(2) * 0.1 # Trust physics model

    def update(self, z):
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(2) - np.dot(K, self.H)), self.P)
        return self.x[0,0]

# =============================================================================
# 3. SCENARIO: NETWORKED WARFARE (LAG SWITCHING)
# =============================================================================
def run_ghost_simulation():
    print("👻 SIMULATING PACKET LOSS WARFARE...")
    np.random.seed(999)
    steps = 500
    
    # A. True Path (Agile Drone)
    t = np.linspace(0, 20, steps)
    true_path = 10 * np.sin(t) + 5 * np.cos(2*t)
    
    # B. Generate Bad Connection
    obs = []
    packet_loss_zones = []
    current_val = true_path[0]
    lag_timer = 0
    in_lag = False
    
    for i in range(steps):
        # Random Lag Spikes (5% chance start, last 20 frames)
        if not in_lag and np.random.random() > 0.95:
            in_lag = True
            lag_timer = 20
            
        if in_lag:
            obs.append(current_val) # FREEZE (Hold last value)
            packet_loss_zones.append(1)
            lag_timer -= 1
            if lag_timer <= 0: in_lag = False
        else:
            # Update + Noise
            current_val = true_path[i] + np.random.normal(0, 0.5)
            obs.append(current_val)
            packet_loss_zones.append(0)
            
    obs = np.array(obs)
    
    # C. Run Trackers
    dda = DDA_Predator()
    kf = KalmanFilter(std_meas=2.0)
    
    path_dda, modes = [], []
    path_kf = []
    
    print("⚔️  TRACKING GHOST TARGET...")
    for i in range(steps):
        d, m = dda.update(obs[i])
        path_dda.append(d)
        modes.append(m)
        path_kf.append(kf.update(np.array([[obs[i]]])))
        
    path_dda = np.array(path_dda)
    path_kf = np.array(path_kf)
    
    # D. Evaluation
    mse_dda = np.mean((true_path - path_dda)**2)
    mse_kf = np.mean((true_path - path_kf)**2)
    
    print("\n" + "="*60)
    print("RESULTS: TRACKING THROUGH PACKET LOSS")
    print("="*60)
    print(f"Kalman MSE: {mse_kf:.4f} (Confused by freezes)")
    print(f"DDA MSE:    {mse_dda:.4f} (Saccadic Recovery)")
    
    if mse_dda < mse_kf:
        imp = (mse_kf - mse_dda)/mse_kf * 100
        print(f"\n🏆 WINNER: DDA v9.1 (+{imp:.1f}%)")
    else:
        print("\n🏆 WINNER: KALMAN")

    # E. Visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    ax1.plot(true_path, 'k-', lw=3, alpha=0.3, label='TRUE POSITION')
    ax1.plot(obs, 'k.', ms=2, alpha=0.2, label='Laggy Feed')
    ax1.plot(path_kf, 'g--', lw=1.5, label='Kalman (Drift)')
    ax1.plot(path_dda, 'r-', lw=2, label='DDA Predator (Snap)')
    
    # Highlight Lag Zones
    for i in range(len(packet_loss_zones)):
        if packet_loss_zones[i]:
            ax1.axvline(i, color='gray', alpha=0.1)
            
    ax1.set_title("DDA vs Kalman: Handling Network Lag & Teleportation")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(modes, 'b-', lw=1, alpha=0.8, label='Saccade Trigger')
    ax2.fill_between(range(steps), modes, color='blue', alpha=0.2)
    ax2.set_title("DDA Internal State: Switching Logic")
    ax2.set_ylabel("Mode (1=Snap)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_ghost_proof.png', dpi=150)
    print("✓ Evidence saved to dda_ghost_proof.png")

if __name__ == "__main__":
    run_ghost_simulation()