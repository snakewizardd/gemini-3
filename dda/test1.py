"""
DDA vs NEURAL CHAOS
-------------------
Can DDA v7.0 track the "Lorenz Attractor" (Chaos Theory) 
better than a Recurrent Neural Network?

Contestants:
1. DDA v7.0 (The Algorithm) - 0 Parameters to learn
2. Echo State Network (Reservoir RNN) - 500 Neurons, Trained via Ridge Regression
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# --- 1. THE LORENZ ATTRACTOR (The Chaos Generator) ---
def lorenz(x, y, z, s=10, r=28, b=2.667):
    x_dot = s*(y - x)
    y_dot = r*x - y - x*z
    z_dot = x*y - b*z
    return x_dot, y_dot, z_dot

def generate_chaos(steps=2000, dt=0.01):
    xs, ys, zs = [], [], []
    x, y, z = 0.0, 1.0, 1.05
    for i in range(steps):
        dx, dy, dz = lorenz(x, y, z)
        x += dx * dt
        y += dy * dt
        z += dz * dt
        xs.append(x)
        ys.append(y)
        zs.append(z)
    
    # Normalize X to reasonable range and add noise
    signal = np.array(xs)
    signal = (signal - np.mean(signal)) / np.std(signal)
    noise = np.random.normal(0, 0.1, steps)
    return signal + noise, signal

# --- 2. THE CHAMPION: DDA v7.0 ---
@dataclass
class DDAConfig:
    P0: float = 0.70
    m: float = 0.30
    alpha: float = 0.001
    beta: float = 0.5
    derivative_boost: float = 0.6
    use_ema_filter: bool = True
    ema_alpha: float = 0.1
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
        if self.c.use_ema_filter:
            self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
        else: self.dF = delta
            
        # Pre-Cognition
        boost = self.c.boost_cap * np.tanh((self.c.derivative_boost * self.dF) / self.c.boost_cap)
        L = I_n + boost
        
        # Update
        F = (self.c.P0 * self.k * self.F_prev) + (self.c.m * L)
        
        # Meta-Learning
        err = I_n - F
        self.k += self.c.alpha * np.sign(err) * (np.abs(err)**self.c.beta)
        self.k = np.clip(self.k, 0.9, 1.1)
        
        self.F_prev = F; self.I_prev = I_n
        return F

# --- 3. THE CHALLENGER: ECHO STATE NETWORK (RNN) ---
class ESN:
    def __init__(self, n_reservoir=500, spectral_radius=0.9):
        self.n_reservoir = n_reservoir
        # Random fixed weights (The "Reservoir")
        np.random.seed(42)
        self.W = np.random.randn(n_reservoir, n_reservoir)
        # Scale spectral radius
        eigenvalues = np.linalg.eigvals(self.W)
        self.W *= spectral_radius / np.max(np.abs(eigenvalues))
        
        self.Win = np.random.randn(n_reservoir, 1) * 0.5
        self.state = np.zeros(n_reservoir)
        self.Wout = None # Learned later
        
    def fit_and_predict(self, signal):
        # Collect states
        states = []
        for x in signal:
            self.state = np.tanh(np.dot(self.W, self.state) + np.dot(self.Win, [x]))
            states.append(self.state.copy())
        
        states = np.array(states)
        # Ridge Regression to train Readout (Offline training advantage!)
        # We try to reconstruct the CLEAN signal from the noisy input states
        # Ideally, ESN acts as a chaotic filter
        
        # Simple task: Next-step prediction or Denoising?
        # Let's do Denoising (fair comparison to DDA)
        train_len = int(len(signal) * 0.5)
        
        X = states[:train_len]
        Y = signal[:train_len] # Target is the input itself (Auto-associative)
        
        # Train Wout
        reg = 1e-8
        self.Wout = np.dot(np.dot(Y.T, X), np.linalg.inv(np.dot(X.T, X) + reg * np.eye(self.n_reservoir)))
        
        # Predict full sequence
        preds = np.dot(states, self.Wout)
        return preds

# --- 4. THE ARENA ---
def run_chaos_test():
    print("🌀 GENERATING LORENZ ATTRACTOR (CHAOS)...")
    noisy_signal, clean_signal = generate_chaos()
    
    # Run DDA (Online, No Training)
    print("🤖 RUNNING DDA v7.0 (0-Shot)...")
    dda = DDA()
    dda_preds = [dda.update(x) for x in noisy_signal]
    
    # Run ESN (Offline, Trained on 50% of data)
    print("🧠 RUNNING ECHO STATE NETWORK (500 Neurons)...")
    esn = ESN()
    esn_preds = esn.fit_and_predict(noisy_signal)
    
    # Eval
    mse_dda = np.mean((clean_signal - dda_preds)**2)
    mse_esn = np.mean((clean_signal - esn_preds)**2)
    
    print("\n" + "="*50)
    print("THE CHAOS CHALLENGE RESULTS")
    print("="*50)
    print(f"Neural Net (ESN) MSE: {mse_esn:.5f} (Training Required)")
    print(f"DDA v7.0 MSE:       {mse_dda:.5f} (Instant)")
    
    winner = "DDA" if mse_dda < mse_esn else "NEURAL"
    print(f"\n🏆 WINNER: {winner}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    # Zoom in on a chaotic turn
    zoom = slice(1000, 1300)
    plt.plot(clean_signal[zoom], 'k-', lw=3, alpha=0.3, label='Chaos Truth')
    plt.plot(esn_preds[zoom], 'b--', lw=1, label='Neural Net (ESN)')
    plt.plot(dda_preds[zoom], 'r-', lw=1.5, label='DDA v7.0')
    plt.title(f"DDA vs NEURAL NET on Lorenz Attractor\nDDA: {mse_dda:.4f} | ESN: {mse_esn:.4f}")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig('dda_vs_chaos.png', dpi=150)
    print("✓ Plot saved to dda_vs_chaos.png")

if __name__ == "__main__":
    run_chaos_test()