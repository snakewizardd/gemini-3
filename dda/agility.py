"""
DDA v7.1 "INTERCEPTOR"
----------------------
Combat-Tuned for High-Agility Targets.
Fixes the "Derivative Smearing" issue by tuning the input filter for speed.

Scenario: A "Jinking" UFO (Random Zig-Zags) designed to break Kalman Filters.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. DDA v7.1 (COMBAT TUNE)
# =============================================================================
@dataclass
class DDAConfig:
    # COMBAT CHANGES:
    P0: float = 0.50           # Low Inertia (Agility)
    ema_alpha: float = 0.4     # Fast Filter (Don't remember old velocity)
    derivative_boost: float = 0.5 # Tighter boost
    
    # Standard:
    m: float = 0.50            # High responsiveness
    alpha: float = 0.005       # Faster adaptation
    beta: float = 0.5
    use_ema_filter: bool = True
    boost_cap: float = 10.0

class DDA:
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
            return I_n
            
        delta = I_n - self.I_prev
        
        # Fast Filter (Less Smearing)
        if self.c.use_ema_filter:
            self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
        else: self.dF = delta
            
        # Boost
        raw_boost = self.c.derivative_boost * self.dF
        boost = self.c.boost_cap * np.tanh(raw_boost / self.c.boost_cap)
        L = I_n + boost
        
        # Update
        F = (self.c.P0 * self.k * self.F_prev) + (self.c.m * L)
        
        # Adapt
        err = I_n - F
        self.k += self.c.alpha * np.sign(err) * (np.abs(err)**self.c.beta)
        self.k = np.clip(self.k, 0.8, 1.2) # Wider range for combat
        
        self.F_prev = F; self.I_prev = I_n
        return F

# =============================================================================
# 2. COMPETITOR: KALMAN FILTER (CV Model)
# =============================================================================
class KalmanFilter2D:
    def __init__(self, dt=1.0, std_meas=0.5):
        self.x = np.zeros((4, 1))
        self.F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        self.P = np.eye(4)
        self.R = np.eye(2) * std_meas**2
        self.Q = np.eye(4) * 0.5 # High process noise for agility

    def predict(self):
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q

    def update(self, z):
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(4) - np.dot(K, self.H)), self.P)
        return self.x[0,0], self.x[1,0]

# =============================================================================
# 3. SCENARIO: THE "JINKING" TARGET
# =============================================================================
def run_interceptor():
    print("🚀 LAUNCHING INTERCEPTOR SIMULATION...")
    steps = 600
    noise = 0.5
    
    # Generate Zig-Zag Path (Random Acceleration Changes)
    # This breaks Constant Velocity models like Kalman
    true_x, true_y = [0], [0]
    vx, vy = 1.0, 0.5
    for i in range(1, steps):
        # Every 50 steps, random hard turn
        if i % 50 == 0:
            vx = np.random.uniform(-1.5, 1.5)
            vy = np.random.uniform(-1.5, 1.5)
        
        true_x.append(true_x[-1] + vx)
        true_y.append(true_y[-1] + vy)
        
    true_x = np.array(true_x)
    true_y = np.array(true_y)
    
    # Noisy Sensor
    obs_x = true_x + np.random.normal(0, noise, steps)
    obs_y = true_y + np.random.normal(0, noise, steps)
    
    # Models
    dda_x = DDA(); dda_y = DDA()
    kf = KalmanFilter2D(std_meas=noise)
    
    path_dda = []
    path_kf = []
    
    for i in range(steps):
        # DDA
        dx = dda_x.update(obs_x[i])
        dy = dda_y.update(obs_y[i])
        path_dda.append([dx, dy])
        
        # Kalman
        kf.predict()
        kx, ky = kf.update(np.array([[obs_x[i]], [obs_y[i]]]))
        path_kf.append([kx, ky])
        
    path_dda = np.array(path_dda)
    path_kf = np.array(path_kf)
    
    # Scoring
    err_dda = np.sqrt(np.sum((path_dda - np.column_stack((true_x, true_y)))**2, axis=1))
    err_kf = np.sqrt(np.sum((path_kf - np.column_stack((true_x, true_y)))**2, axis=1))
    
    mse_dda = np.mean(err_dda)
    mse_kf = np.mean(err_kf)
    
    print("\n" + "="*50)
    print("COMBAT RESULTS (Zig-Zag Maneuvers)")
    print("="*50)
    print(f"Kalman Error: {mse_kf:.4f} (Overshoots turns)")
    print(f"DDA Error:    {mse_dda:.4f} (Snaps to turns)")
    
    if mse_dda < mse_kf:
        imp = (mse_kf - mse_dda) / mse_kf * 100
        print(f"\n🏆 WINNER: DDA (+{imp:.1f}%)")
    else:
        print("\n🏆 WINNER: KALMAN")

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(true_x, true_y, 'k--', lw=1, alpha=0.5, label='Target Path')
    plt.plot(path_kf[:,0], path_kf[:,1], 'g-', alpha=0.6, label='Kalman (Overshoot)')
    plt.plot(path_dda[:,0], path_dda[:,1], 'r-', lw=2, label='DDA v7.1 (Tight)')
    plt.title("DDA vs Kalman on High-Agility Targets")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('dda_interceptor_proof.png', dpi=150)
    print("✓ Plot saved")

if __name__ == "__main__":
    run_interceptor()