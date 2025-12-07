"""
DDA v8.0 "THE HUNTER"
---------------------
Scenario: "The Drunken Firefly" (Lévy Flight Simulation).
Target: A drone that moves randomly with zero momentum conservation.
Challenger: Kalman Filter (Physics-based).

THE INNOVATION: "Dynamic Inertia Dumping"
When DDA detects a hard turn (Derivative Sign Flip), it instantly drops 
Inertia (P0) to zero, snapping to the target, then restores P0 for stability.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE HUNTER ENGINE (DDA v8.0)
# =============================================================================
@dataclass
class DDAConfig:
    base_P0: float = 0.80      # High stability by default
    m: float = 0.20
    alpha: float = 0.005
    beta: float = 0.5
    derivative_boost: float = 0.5
    
    # THE KILL SWITCH
    # If the derivative flips sign (hard turn), how much do we dump P0?
    inertia_dump: float = 0.9  # Reduce P0 by 90% during turns

class DDA_Hunter:
    def __init__(self):
        self.c = DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_prev = 0.0 # Track previous direction
        self.init = False

    def update(self, I_n):
        if not self.init:
            self.F_prev = I_n; self.I_prev = I_n; self.init = True
            return I_n
            
        # 1. Calculate Current Direction
        delta = I_n - self.I_prev
        
        # 2. DETECT JINK (Direction Change)
        # If current delta and prev delta have different signs, we are turning.
        is_turn = np.sign(delta) != np.sign(self.delta_prev)
        
        # 3. DYNAMIC INERTIA SCHEDULING
        if is_turn:
            # DUMP INERTIA! Snap to new reality.
            effective_P0 = self.c.base_P0 * (1.0 - self.c.inertia_dump)
        else:
            # Stable flight, keep high inertia
            effective_P0 = self.c.base_P0
            
        # 4. Standard Update with Dynamic P0
        boost = self.c.derivative_boost * delta
        L = I_n + boost
        
        # Note: If P0 drops, m must rise to maintain unity gain roughly
        m_dynamic = 1.0 - effective_P0
        
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (m_dynamic * L)
        
        # 5. Adapt k
        err = I_n - F
        self.k += self.c.alpha * np.sign(err) * (np.abs(err)**self.c.beta)
        self.k = np.clip(self.k, 0.9, 1.1)
        
        self.F_prev = F
        self.I_prev = I_n
        self.delta_prev = delta # Update direction memory
        return F

# =============================================================================
# 2. THE COMPETITOR: KALMAN FILTER (Constant Velocity)
# =============================================================================
class KalmanFilter:
    def __init__(self, dt=1.0, std_meas=0.5):
        self.x = np.zeros((2, 1)) # Pos, Vel
        self.F = np.array([[1, dt], [0, 1]]) # Physics Model
        self.H = np.array([[1, 0]]) # Measurement
        self.P = np.eye(2)
        self.R = np.eye(1) * std_meas**2
        self.Q = np.eye(2) * 0.1 

    def update(self, z):
        # Predict
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        # Update
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(2) - np.dot(K, self.H)), self.P)
        return self.x[0,0]

# =============================================================================
# 3. THE SCENARIO: DRUNKEN FIREFLY (Lévy Flight)
# =============================================================================
def run_hunter_simulation():
    print("🦟 RELEASING 'THE DRUNKEN FIREFLY'...")
    np.random.seed(101) # Hard seed
    steps = 500
    
    # Generate Lévy Flight (Random Walk with massive jumps)
    true_path = [0]
    for _ in range(steps-1):
        # 90% small moves, 10% massive jumps
        if np.random.random() > 0.9:
            jump = np.random.normal(0, 5.0) 
        else:
            jump = np.random.normal(0, 0.5)
        true_path.append(true_path[-1] + jump)
    
    true_path = np.array(true_path)
    
    # Add Sensor Noise
    noise_level = 1.0
    obs = true_path + np.random.normal(0, noise_level, steps)
    
    # Initialize Agents
    dda = DDA_Hunter()
    kf = KalmanFilter(std_meas=noise_level)
    
    path_dda = []
    path_kf = []
    
    print("⚔️  TRACKING ENGAGED...")
    for i in range(steps):
        # DDA
        d = dda.update(obs[i])
        path_dda.append(d)
        
        # Kalman
        k = kf.update(np.array([[obs[i]]]))
        path_kf.append(k)
        
    path_dda = np.array(path_dda)
    path_kf = np.array(path_kf)
    
    # SCORECARD
    mse_dda = np.mean((true_path - path_dda)**2)
    mse_kf = np.mean((true_path - path_kf)**2)
    
    print("\n" + "="*50)
    print("FINAL RESULTS (Lévy Flight Tracking)")
    print("="*50)
    print(f"Kalman Filter MSE: {mse_kf:.4f}")
    print(f"DDA v8.0 MSE:      {mse_dda:.4f}")
    
    if mse_dda < mse_kf:
        imp = (mse_kf - mse_dda)/mse_kf * 100
        print(f"\n🏆 WINNER: DDA v8.0 (+{imp:.1f}%)")
        print("Reason: Inertia Dumping allowed instant turns.")
    else:
        print("\n🏆 WINNER: KALMAN")

    # Plot
    plt.figure(figsize=(12, 6))
    
    # Plot only a slice to see the turns clearly
    zoom = slice(100, 250)
    
    plt.plot(true_path[zoom], 'k-', lw=3, alpha=0.3, label='Firefly Path')
    plt.plot(path_kf[zoom], 'g--', lw=2, label='Kalman (Momentum Lag)')
    plt.plot(path_dda[zoom], 'r-', lw=2, label='DDA v8.0 (Snap Turn)')
    
    plt.title("DDA vs Kalman on Stochastic Motion (Lévy Flight)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('dda_hunter_proof.png', dpi=150)
    print("✓ Evidence saved to dda_hunter_proof.png")

if __name__ == "__main__":
    run_hunter_simulation()