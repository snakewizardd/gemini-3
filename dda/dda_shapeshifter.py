"""
DDA v11.0 "THE SHAPESHIFTER" (Meta-Adaptive Regime Detection)
--------------------------------------------------------------
The Apex Predator: A DDA that BECOMES what the target needs.

INNOVATION: Real-time regime classification + personality morphing.

REGIMES:
  🟢 STABLE    - High inertia, low boost (smooth flight)
  🟡 VOLATILE  - Medium inertia, high boost (momentum with jitter)
  🔴 CHAOTIC   - Saccadic mode (Lévy flight / teleportation)
  ⚫ FROZEN    - Dead reckoning (signal loss)

The Shapeshifter analyzes a sliding window of signal statistics
and dynamically adjusts P0, derivative boost, and filter settings.

Scenario: "Chaos Theory" — A target that switches regimes unpredictably.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List
from enum import IntEnum
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. REGIME DEFINITIONS
# =============================================================================
class Regime(IntEnum):
    STABLE = 0   # Low variance, consistent direction
    VOLATILE = 1 # High variance, but momentum preserved
    CHAOTIC = 2  # Erratic, no momentum (Lévy-like)
    FROZEN = 3   # Signal stuck (packet loss)


@dataclass
class PersonalityProfile:
    """Configuration preset for each regime."""
    P0: float              # Inertia weight
    derivative_boost: float # Pre-cognitive multiplier
    ema_alpha: float       # Derivative filter strength
    saccade_thresh: float  # Teleport detection threshold
    description: str


# THE FOUR PERSONALITIES
PERSONALITIES = {
    Regime.STABLE: PersonalityProfile(
        P0=0.92, 
        derivative_boost=0.2, 
        ema_alpha=0.1,
        saccade_thresh=5.0,
        description="🟢 STABLE: High lock, minimal boost"
    ),
    Regime.VOLATILE: PersonalityProfile(
        P0=0.70, 
        derivative_boost=0.7, 
        ema_alpha=0.25,
        saccade_thresh=4.0,
        description="🟡 VOLATILE: Balanced, aggressive boost"
    ),
    Regime.CHAOTIC: PersonalityProfile(
        P0=0.30, 
        derivative_boost=0.1, 
        ema_alpha=0.5,
        saccade_thresh=2.5,
        description="🔴 CHAOTIC: Low inertia, snap-ready"
    ),
    Regime.FROZEN: PersonalityProfile(
        P0=1.0, 
        derivative_boost=0.0, 
        ema_alpha=0.0,
        saccade_thresh=999.0,
        description="⚫ FROZEN: Coast on last velocity"
    )
}


# =============================================================================
# 2. THE SHAPESHIFTER ENGINE
# =============================================================================
@dataclass
class ShapeshifterConfig:
    window_size: int = 15           # Samples for regime detection
    variance_thresh_low: float = 0.5  # Below = STABLE
    variance_thresh_high: float = 3.0 # Above = CHAOTIC
    momentum_thresh: float = 0.6      # Autocorrelation for momentum
    freeze_thresh: float = 0.001      # Delta below = FROZEN
    
    # Adaptation
    alpha: float = 0.001
    beta: float = 0.5


class DDA_Shapeshifter:
    """
    The Shapeshifter: Meta-adaptive predator that morphs to match signal regimes.
    
    Uses sliding window statistics to classify the current regime and
    dynamically switches between personality profiles.
    """
    
    def __init__(self, noise_profile: float = 1.0):
        self.c = ShapeshifterConfig()
        self.noise_sigma = noise_profile
        
        # Core state
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.dF = 0.0
        self.last_valid_dF = 0.0
        
        # Regime detection
        self.history: List[float] = []
        self.delta_history: List[float] = []
        self.current_regime = Regime.STABLE
        self.regime_history: List[int] = []
        
        self.init = False
        
    def _detect_regime(self) -> Regime:
        """
        Classify current signal regime using sliding window statistics.
        
        Features analyzed:
        1. Variance — Is the signal jumpy or smooth?
        2. Autocorrelation — Does it have momentum?
        3. Delta magnitude — Is the signal frozen?
        """
        if len(self.delta_history) < 3:
            return Regime.STABLE
        
        deltas = np.array(self.delta_history[-self.c.window_size:])
        
        # Feature 1: Variance of deltas
        variance = np.var(deltas)
        
        # Feature 2: Autocorrelation at lag 1 (momentum indicator)
        if len(deltas) >= 2:
            autocorr = np.corrcoef(deltas[:-1], deltas[1:])[0, 1]
            if np.isnan(autocorr):
                autocorr = 0.0
        else:
            autocorr = 0.0
        
        # Feature 3: Recent delta magnitude (freeze detection)
        avg_abs_delta = np.mean(np.abs(deltas[-3:]))
        
        # DECISION TREE
        if avg_abs_delta < self.c.freeze_thresh:
            return Regime.FROZEN
        elif variance < self.c.variance_thresh_low:
            return Regime.STABLE
        elif variance > self.c.variance_thresh_high:
            if autocorr > self.c.momentum_thresh:
                return Regime.VOLATILE  # High variance but momentum
            else:
                return Regime.CHAOTIC   # High variance, no momentum
        else:
            # Medium variance
            if autocorr > self.c.momentum_thresh:
                return Regime.VOLATILE
            else:
                return Regime.STABLE
    
    def update(self, I_n: float) -> Tuple[float, dict]:
        """
        Process observation with regime-adaptive behavior.
        Returns estimate and diagnostic info.
        """
        if not self.init:
            self.F_prev = I_n
            self.I_prev = I_n
            self.history = [I_n]
            self.init = True
            return I_n, {
                'regime': Regime.STABLE,
                'personality': PERSONALITIES[Regime.STABLE].description
            }
        
        # Calculate delta
        delta = I_n - self.I_prev
        self.delta_history.append(delta)
        self.history.append(I_n)
        
        # Trim histories
        if len(self.delta_history) > self.c.window_size * 2:
            self.delta_history.pop(0)
            self.history.pop(0)
        
        # --- REGIME DETECTION ---
        new_regime = self._detect_regime()
        self.current_regime = new_regime
        self.regime_history.append(new_regime)
        
        # --- GET PERSONALITY ---
        p = PERSONALITIES[new_regime]
        
        # --- HANDLE FROZEN (Dead Reckoning) ---
        if new_regime == Regime.FROZEN:
            F = self.F_prev + self.last_valid_dF
            self.F_prev = F
            return F, {
                'regime': new_regime,
                'personality': p.description,
                'P0': p.P0,
                'boost': p.derivative_boost
            }
        
        # --- STANDARD UPDATE WITH MORPHED PERSONALITY ---
        
        # Filtered derivative
        self.dF = (p.ema_alpha * delta) + ((1 - p.ema_alpha) * self.dF)
        self.last_valid_dF = self.dF
        
        # Saccade check
        raw_error = np.abs(I_n - self.F_prev)
        
        if raw_error > (p.saccade_thresh * self.noise_sigma):
            # SACCADE: Snap to target
            effective_P0 = 0.0
            effective_m = 1.0
            L = I_n
            self.dF = 0.0  # Reset momentum
            is_saccade = True
        else:
            # PURSUIT: Use personality
            effective_P0 = p.P0
            effective_m = 1.0 - effective_P0
            L = I_n + (p.derivative_boost * self.dF)
            is_saccade = False
        
        # Update law
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (effective_m * L)
        
        # Adapt gain
        if not is_saccade:
            err = I_n - F
            self.k += self.c.alpha * np.sign(err) * (np.abs(err) ** self.c.beta)
            self.k = np.clip(self.k, 0.85, 1.15)
        else:
            self.k = 1.0
        
        self.F_prev = F
        self.I_prev = I_n
        
        return F, {
            'regime': new_regime,
            'personality': p.description,
            'P0': p.P0,
            'boost': p.derivative_boost,
            'saccade': is_saccade
        }


# =============================================================================
# 3. STATIC COMPETITORS
# =============================================================================
class DDA_Static:
    """Standard DDA with fixed personality (no adaptation)."""
    
    def __init__(self, P0=0.70, boost=0.5):
        self.P0 = P0
        self.boost = boost
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
        self.dF = 0.2 * delta + 0.8 * self.dF
        
        L = I_n + self.boost * self.dF
        F = (self.P0 * self.k * self.F_prev) + ((1 - self.P0) * L)
        
        err = I_n - F
        self.k += 0.001 * np.sign(err) * (np.abs(err) ** 0.5)
        self.k = np.clip(self.k, 0.85, 1.15)
        
        self.F_prev = F; self.I_prev = I_n
        return F


class KalmanFilter:
    """Standard Kalman filter baseline."""
    
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
        return self.x[0, 0]


# =============================================================================
# 4. SCENARIO: "CHAOS THEORY"
# =============================================================================
def run_shapeshifter_simulation():
    print("🦎 INITIALIZING 'CHAOS THEORY' SCENARIO...")
    np.random.seed(777)
    
    steps = 600
    noise_level = 0.8
    
    # --- BUILD MULTI-REGIME PATH ---
    true_path = []
    ground_truth_regimes = []
    
    # Segment 1: STABLE (smooth sine)
    t1 = np.linspace(0, 4, 100)
    seg1 = 10 * np.sin(0.5 * t1)
    true_path.extend(seg1)
    ground_truth_regimes.extend([Regime.STABLE] * 100)
    
    # Segment 2: VOLATILE (sine with growing amplitude + momentum)
    t2 = np.linspace(0, 4, 100)
    seg2 = seg1[-1] + np.cumsum(np.sin(t2) * 2 + np.random.normal(0, 0.5, 100))
    true_path.extend(seg2)
    ground_truth_regimes.extend([Regime.VOLATILE] * 100)
    
    # Segment 3: CHAOTIC (Lévy flight - random jumps)
    seg3 = [seg2[-1]]
    for _ in range(99):
        if np.random.random() > 0.85:
            jump = np.random.normal(0, 5)  # Big jump
        else:
            jump = np.random.normal(0, 0.3)
        seg3.append(seg3[-1] + jump)
    true_path.extend(seg3)
    ground_truth_regimes.extend([Regime.CHAOTIC] * 100)
    
    # Segment 4: FROZEN (signal stuck)
    seg4 = [seg3[-1]] * 80
    true_path.extend(seg4)
    ground_truth_regimes.extend([Regime.FROZEN] * 80)
    
    # Segment 5: VOLATILE (recovery with momentum)
    t5 = np.linspace(0, 3, 80)
    seg5 = seg4[-1] + np.cumsum(np.cos(t5) * 1.5 + np.random.normal(0, 0.3, 80))
    true_path.extend(seg5)
    ground_truth_regimes.extend([Regime.VOLATILE] * 80)
    
    # Segment 6: STABLE (settle back)
    t6 = np.linspace(0, 4, 140)
    seg6 = seg5[-1] + 5 * np.sin(0.3 * t6)
    true_path.extend(seg6)
    ground_truth_regimes.extend([Regime.STABLE] * 140)
    
    true_path = np.array(true_path[:steps])
    ground_truth_regimes = ground_truth_regimes[:steps]
    
    # Noisy observations
    obs = true_path + np.random.normal(0, noise_level, steps)
    
    # Make frozen segment actually frozen in observations
    obs[300:380] = obs[299]
    
    # --- TRACKERS ---
    shapeshifter = DDA_Shapeshifter(noise_profile=noise_level)
    static_balanced = DDA_Static(P0=0.70, boost=0.5)
    static_stable = DDA_Static(P0=0.92, boost=0.2)
    static_aggressive = DDA_Static(P0=0.50, boost=0.8)
    kalman = KalmanFilter(std_meas=noise_level)
    
    # Storage
    path_shape = []
    detected_regimes = []
    path_balanced = []
    path_stable = []
    path_aggressive = []
    path_kalman = []
    
    print("⚔️  MORPHING THROUGH CHAOS...")
    
    for i in range(steps):
        # Shapeshifter
        est, info = shapeshifter.update(obs[i])
        path_shape.append(est)
        detected_regimes.append(info['regime'])
        
        # Static competitors
        path_balanced.append(static_balanced.update(obs[i]))
        path_stable.append(static_stable.update(obs[i]))
        path_aggressive.append(static_aggressive.update(obs[i]))
        path_kalman.append(kalman.update(obs[i]))
    
    # Convert
    path_shape = np.array(path_shape)
    path_balanced = np.array(path_balanced)
    path_stable = np.array(path_stable)
    path_aggressive = np.array(path_aggressive)
    path_kalman = np.array(path_kalman)
    detected_regimes = np.array(detected_regimes)
    
    # --- EVALUATION ---
    mse_shape = np.mean((true_path - path_shape) ** 2)
    mse_balanced = np.mean((true_path - path_balanced) ** 2)
    mse_stable = np.mean((true_path - path_stable) ** 2)
    mse_aggressive = np.mean((true_path - path_aggressive) ** 2)
    mse_kalman = np.mean((true_path - path_kalman) ** 2)
    
    # Regime detection accuracy
    regime_accuracy = np.mean(np.array(detected_regimes) == np.array(ground_truth_regimes)) * 100
    
    print("\n" + "=" * 70)
    print("🏆 CHAOS THEORY RESULTS")
    print("=" * 70)
    print(f"{'Tracker':<25} {'MSE':<12} {'Status':<15}")
    print("-" * 70)
    
    results = [
        ("Shapeshifter (v11.0)", mse_shape),
        ("Static Balanced", mse_balanced),
        ("Static Stable-Tuned", mse_stable),
        ("Static Aggressive", mse_aggressive),
        ("Kalman Filter", mse_kalman)
    ]
    
    best_mse = min(r[1] for r in results)
    
    for name, mse in results:
        status = "🏆 WINNER" if mse == best_mse else ""
        print(f"{name:<25} {mse:<12.4f} {status:<15}")
    
    print("-" * 70)
    print(f"Regime Detection Accuracy: {regime_accuracy:.1f}%")
    print("=" * 70)
    
    # Best static competitor
    static_best = min(mse_balanced, mse_stable, mse_aggressive, mse_kalman)
    improvement = ((static_best - mse_shape) / static_best) * 100
    print(f"\n🦎 SHAPESHIFTER ADVANTAGE: +{improvement:.1f}% over best static competitor")
    
    # --- VISUALIZATION ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Tracking comparison
    ax1 = axes[0]
    ax1.plot(true_path, 'k-', lw=3, alpha=0.3, label='TRUE PATH')
    ax1.plot(path_kalman, 'g--', lw=1, alpha=0.7, label=f'Kalman (MSE={mse_kalman:.2f})')
    ax1.plot(path_balanced, 'b--', lw=1, alpha=0.7, label=f'Static Balanced (MSE={mse_balanced:.2f})')
    ax1.plot(path_shape, 'r-', lw=2, label=f'Shapeshifter (MSE={mse_shape:.2f})')
    
    ax1.set_title("🦎 DDA Shapeshifter vs Static Competitors on Mixed-Regime Signal", 
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Position")
    
    # Plot 2: Ground truth regimes
    ax2 = axes[1]
    regime_colors = {Regime.STABLE: 'green', Regime.VOLATILE: 'gold', 
                     Regime.CHAOTIC: 'red', Regime.FROZEN: 'gray'}
    regime_names = {Regime.STABLE: 'Stable', Regime.VOLATILE: 'Volatile',
                    Regime.CHAOTIC: 'Chaotic', Regime.FROZEN: 'Frozen'}
    
    for i, regime in enumerate(ground_truth_regimes):
        ax2.axvspan(i, i+1, color=regime_colors[regime], alpha=0.4)
    
    ax2.set_title("Ground Truth Regime Zones", fontsize=11)
    ax2.set_ylabel("Regime")
    ax2.set_yticks([])
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, alpha=0.6, label=regime_names[r]) 
                       for r, c in regime_colors.items()]
    ax2.legend(handles=legend_elements, loc='upper right', ncol=4)
    
    # Plot 3: Detected regimes
    ax3 = axes[2]
    for i, regime in enumerate(detected_regimes):
        ax3.axvspan(i, i+1, color=regime_colors[Regime(regime)], alpha=0.4)
    
    ax3.set_title(f"Shapeshifter Detected Regimes (Accuracy: {regime_accuracy:.1f}%)", fontsize=11)
    ax3.set_xlabel("Time Step")
    ax3.set_ylabel("Detected")
    ax3.set_yticks([])
    
    plt.tight_layout()
    plt.savefig('dda_shapeshifter_proof.png', dpi=150)
    print("\n✓ Evidence saved to dda_shapeshifter_proof.png")


if __name__ == "__main__":
    run_shapeshifter_simulation()
