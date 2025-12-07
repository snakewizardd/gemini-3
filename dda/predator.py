"""
DDA v9.0 "THE PREDATOR" (Biomimetic Saccades)
---------------------------------------------
FIXED VERSION: Corrected tuple unpacking error on initialization.

Scenario: Lévy Flight (Random Teleportation).
Theory:   Human eyes track via "Smooth Pursuit" (High Inertia) 
          mixed with "Saccades" (Zero Inertia jumps).
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE PREDATOR (DDA v9.0)
# =============================================================================
@dataclass
class DDAConfig:
    # BIOMIMETIC SETTINGS
    P0_pursuit: float = 0.95   # Extreme stability during drift
    P0_saccade: float = 0.0    # Instant snap during jumps
    
    # SACCADE TRIGGER
    # If error exceeds this multiples of noise, trigger Saccade.
    saccade_thresh: float = 3.0 
    
    # Standard Config
    m: float = 0.05            # During pursuit, trust priors (High Stability)
    alpha: float = 0.001       
    beta: float = 0.5
    derivative_boost: float = 0.0 # No boost needed for random walks
    use_ema_filter: bool = True
    ema_alpha: float = 0.1

class DDA_Predator:
    def __init__(self, noise_profile=1.0):
        self.c = DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.dF = 0.0
        self.init = False
        self.noise_sigma = noise_profile

    def update(self, I_n):
        if not self.init:
            self.F_prev = I_n; self.I_prev = I_n; self.init = True
            # FIX: Return a tuple so the main loop doesn't crash!
            return I_n, 0 
            
        # 1. Calculate Raw Error (The "Retinal Slip")
        slip = np.abs(I_n - self.F_prev)
        
        # 2. SACCADIC GATING (The Decision)
        if slip > (self.c.saccade_thresh * self.noise_sigma):
            # TARGET TELEPORTED -> SACCADE (Snap)
            effective_P0 = self.c.P0_saccade
            effective_m = 1.0 # Trust new data 100%
            mode = 1 # for visualization
        else:
            # TARGET DRIFTING -> SMOOTH PURSUIT (Lock)
            effective_P0 = self.c.P0_pursuit
            # Maintain unity gain logic: m = 1 - (P0*k) approx
            effective_m = 1.0 - effective_P0 
            mode = 0
            
        # 3. Update Law
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (effective_m * I_n)
        
        # 4. Background Adaptation
        if mode == 0:
            err = I_n - F
            self.k += self.c.alpha * np.sign(err) * (np.abs(err)**self.c.beta)
            self.k = np.clip(self.k, 0.95, 1.05)
        else:
            self.k = 1.0
            
        self.F_prev = F
        self.I_prev = I_n
        return F, mode

# =============================================================================
# 2. THE COMPETITOR: KALMAN FILTER (Constant Velocity)
# =============================================================================
class KalmanFilter:
    def __init__(self, dt=1.0, std_meas=1.0):
        self.x = np.zeros((2, 1)) 
        self.F = np.array([[1, dt], [0, 1]])
        self.H = np.array([[1, 0]])
        self.P = np.eye(2)
        self.R = np.eye(1) * std_meas**2
        self.Q = np.eye(2) * 0.5 

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
# 3. THE SIMULATION: LÉVY FLIGHT
# =============================================================================
def run_predator_simulation():
    print("🦟 RELEASING 'THE DRUNKEN FIREFLY' (LÉVY FLIGHT)...")
    np.random.seed(101) 
    steps = 400
    noise_level = 1.0
    
    # Generate Lévy Flight
    true_path = [0]
    for _ in range(steps-1):
        if np.random.random() > 0.95:
            jump = np.random.normal(0, 10.0) # Massive Teleport
        else:
            jump = np.random.normal(0, 0.2)  # Tiny Drift
        true_path.append(true_path[-1] + jump)
    
    true_path = np.array(true_path)
    obs = true_path + np.random.normal(0, noise_level, steps)
    
    # Agents
    dda = DDA_Predator(noise_profile=noise_level)
    kf = KalmanFilter(std_meas=noise_level)
    
    path_dda = []
    modes = []
    path_kf = []
    
    print("⚔️  TRACKING ENGAGED...")
    for i in range(steps):
        d, mode = dda.update(obs[i])
        path_dda.append(d)
        modes.append(mode)
        
        k = kf.update(np.array([[obs[i]]]))
        path_kf.append(k)
        
    path_dda = np.array(path_dda)
    path_kf = np.array(path_kf)
    
    # Scoring
    mse_dda = np.mean((true_path - path_dda)**2)
    mse_kf = np.mean((true_path - path_kf)**2)
    
    print("\n" + "="*50)
    print("FINAL RESULTS (Lévy Flight)")
    print("="*50)
    print(f"Kalman Filter MSE: {mse_kf:.4f}")
    print(f"DDA v9.0 MSE:      {mse_dda:.4f}")
    
    if mse_dda < mse_kf:
        imp = (mse_kf - mse_dda)/mse_kf * 100
        print(f"\n🏆 WINNER: DDA v9.0 (+{imp:.1f}%)")
    else:
        print("\n🏆 WINNER: KALMAN")

    # Plot
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(true_path, 'k-', lw=3, alpha=0.3, label='Firefly Path')
    plt.plot(path_kf, 'g--', lw=1.5, label='Kalman (Laggy)')
    plt.plot(path_dda, 'r-', lw=1.5, label='DDA v9.0 (Biomimetic)')
    plt.title("DDA 'Predator' vs Kalman on Teleporting Target")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot Saccades
    plt.subplot(2, 1, 2)
    plt.plot(modes, 'b-', alpha=0.6, label='Saccade Activation (1=Snap, 0=Lock)')
    plt.fill_between(range(steps), modes, color='blue', alpha=0.1)
    plt.title("DDA Internal State: Switching between Smooth Pursuit & Saccades")
    plt.xlabel("Time Step")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_predator_proof.png', dpi=150)
    print("✓ Evidence saved to dda_predator_proof.png")

if __name__ == "__main__":
    run_predator_simulation()