"""
DDA v10.0 "THE PROPHET" (Multi-Horizon Extrapolatory Predator)
---------------------------------------------------------------
The Final Evolution of the Predator Line.

INNOVATION: Predicts target positions at T+1, T+3, T+5 horizons using:
1. Polynomial Trajectory Fitting (Position + Velocity + Acceleration)
2. Confidence Decay (Uncertainty grows with prediction horizon)
3. Saccadic Gating (Resets predictions on hard turns)
4. Dead Reckoning (Maintains extrapolation during signal freeze)

Scenario: "Missile Intercept" — Predict where to aim, not where to track.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List, Tuple
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE PROPHET ENGINE (DDA v10.0)
# =============================================================================
@dataclass
class ProphetConfig:
    # Core DDA Settings
    P0_pursuit: float = 0.90        # High stability during smooth flight
    P0_saccade: float = 0.0         # Instant snap on hard turns
    saccade_thresh: float = 3.5     # Error threshold to trigger saccade
    
    # Extrapolation Settings
    horizons: List[int] = field(default_factory=lambda: [1, 3, 5])  # T+N predictions
    window_size: int = 8            # History window for trajectory fitting
    confidence_decay: float = 0.15  # Confidence drops per horizon step
    
    # Derivative Settings
    derivative_boost: float = 0.5   # Pre-cognitive boost multiplier
    use_ema_filter: bool = True
    ema_alpha: float = 0.25         # Derivative filter strength
    
    # Adaptation
    alpha: float = 0.001            # Learning rate for k
    beta: float = 0.5               # Error sensitivity exponent


class DDA_Prophet:
    """
    The Prophet: A multi-horizon extrapolatory predator.
    
    Tracks a target AND predicts where it will be at configurable 
    future time steps using polynomial trajectory fitting.
    """
    
    def __init__(self, noise_profile: float = 1.0):
        self.c = ProphetConfig()
        self.k = 1.0
        self.F_prev = 0.0           # Previous estimate
        self.I_prev = 0.0           # Previous input
        self.dF = 0.0               # Filtered velocity
        self.ddF = 0.0              # Filtered acceleration
        self.last_valid_dF = 0.0    # For dead reckoning
        self.last_valid_ddF = 0.0   # For dead reckoning
        self.noise_sigma = noise_profile
        
        # State history for polynomial fitting
        self.history: List[float] = []
        
        self.init = False
        
    def update(self, I_n: float) -> Tuple[float, dict]:
        """
        Process observation and return:
        - Current estimate
        - Dictionary with predictions at each horizon + mode info
        """
        if not self.init:
            self.F_prev = I_n
            self.I_prev = I_n
            self.history = [I_n]
            self.init = True
            return I_n, {
                'predictions': {h: I_n for h in self.c.horizons},
                'confidence': {h: 1.0 for h in self.c.horizons},
                'mode': 0
            }
        
        # --- DETECT SIGNAL FREEZE (For Dead Reckoning) ---
        is_frozen = (I_n == self.I_prev)
        
        if is_frozen:
            # MODE: DEAD RECKONING — Coast on last known trajectory
            F = self.F_prev + self.last_valid_dF
            predictions = self._extrapolate_dead_reckoning(F)
            
            self.F_prev = F
            return F, {
                'predictions': predictions,
                'confidence': self._get_confidence(decay_factor=1.5),  # Lower confidence
                'mode': 2  # Coasting
            }
        
        # --- SIGNAL IS LIVE ---
        
        # 1. Calculate derivatives
        delta = I_n - self.I_prev
        
        if self.c.use_ema_filter:
            prev_dF = self.dF
            self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
            
            # Acceleration (derivative of velocity)
            d_delta = self.dF - prev_dF
            self.ddF = (self.c.ema_alpha * d_delta) + ((1 - self.c.ema_alpha) * self.ddF)
        else:
            self.dF = delta
            self.ddF = delta - (self.I_prev - (self.history[-2] if len(self.history) >= 2 else self.I_prev))
        
        # Store for dead reckoning
        self.last_valid_dF = self.dF
        self.last_valid_ddF = self.ddF
        
        # 2. Update history window
        self.history.append(I_n)
        if len(self.history) > self.c.window_size:
            self.history.pop(0)
        
        # 3. Retinal Slip Detection
        raw_error = np.abs(I_n - self.F_prev)
        
        # 4. SACCADIC GATING
        if raw_error > (self.c.saccade_thresh * self.noise_sigma):
            # MODE: SACCADE — Hard reset
            effective_P0 = self.c.P0_saccade
            effective_m = 1.0
            mode = 1
            
            # Reset derivatives on teleport
            self.dF = 0.0
            self.ddF = 0.0
            self.last_valid_dF = 0.0
            self.last_valid_ddF = 0.0
            self.history = [I_n]  # Reset history
        else:
            # MODE: PURSUIT — Smooth tracking with extrapolation
            effective_P0 = self.c.P0_pursuit
            effective_m = 1.0 - effective_P0
            mode = 0
        
        # 5. Update Law (with pre-cognitive boost)
        if mode == 0:
            L = I_n + (self.c.derivative_boost * self.dF)
        else:
            L = I_n
        
        prior = effective_P0 * self.k * self.F_prev
        F = prior + (effective_m * L)
        
        # 6. Adaptive Gain
        if mode == 0:
            err = I_n - F
            self.k += self.c.alpha * np.sign(err) * (np.abs(err) ** self.c.beta)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0
        
        # 7. EXTRAPOLATION — The Prophet's Power
        predictions = self._extrapolate(F)
        confidence = self._get_confidence(decay_factor=1.0 if mode == 0 else 2.0)
        
        self.F_prev = F
        self.I_prev = I_n
        
        return F, {
            'predictions': predictions,
            'confidence': confidence,
            'mode': mode
        }
    
    def _extrapolate(self, current_estimate: float) -> dict:
        """
        Predict future positions using polynomial extrapolation.
        Uses: position + velocity*t + 0.5*acceleration*t^2
        """
        predictions = {}
        for horizon in self.c.horizons:
            # Quadratic extrapolation
            pred = (current_estimate + 
                    self.dF * horizon + 
                    0.5 * self.ddF * (horizon ** 2))
            predictions[horizon] = pred
        return predictions
    
    def _extrapolate_dead_reckoning(self, current_estimate: float) -> dict:
        """Extrapolate during signal freeze using last known trajectory."""
        predictions = {}
        for horizon in self.c.horizons:
            pred = (current_estimate + 
                    self.last_valid_dF * horizon + 
                    0.5 * self.last_valid_ddF * (horizon ** 2))
            predictions[horizon] = pred
        return predictions
    
    def _get_confidence(self, decay_factor: float = 1.0) -> dict:
        """Calculate confidence for each prediction horizon."""
        confidence = {}
        for horizon in self.c.horizons:
            conf = np.exp(-self.c.confidence_decay * decay_factor * horizon)
            confidence[horizon] = conf
        return confidence


# =============================================================================
# 2. THE COMPETITOR: KALMAN FILTER (With Prediction)
# =============================================================================
class KalmanPredictor:
    """
    Kalman Filter with multi-step prediction capability.
    State: [position, velocity, acceleration]
    """
    
    def __init__(self, dt: float = 1.0, std_meas: float = 1.0, horizons: List[int] = None):
        self.dt = dt
        self.horizons = horizons or [1, 3, 5]
        
        # State [pos, vel, acc]
        self.x = np.zeros((3, 1))
        
        # State transition (constant acceleration model)
        self.F = np.array([
            [1, dt, 0.5*dt**2],
            [0, 1, dt],
            [0, 0, 1]
        ])
        
        # Measurement matrix (observe position only)
        self.H = np.array([[1, 0, 0]])
        
        # Covariances
        self.P = np.eye(3) * 10
        self.R = np.eye(1) * std_meas**2
        self.Q = np.eye(3) * np.array([[0.1], [0.5], [1.0]])  # Process noise
        
    def update(self, z: float) -> Tuple[float, dict]:
        """Update with measurement and return predictions."""
        # Predict
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        # Update
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot((np.eye(3) - np.dot(K, self.H)), self.P)
        
        # Multi-step predictions
        predictions = {}
        pos, vel, acc = self.x[0, 0], self.x[1, 0], self.x[2, 0]
        for h in self.horizons:
            pred_pos = pos + vel * h * self.dt + 0.5 * acc * (h * self.dt) ** 2
            predictions[h] = pred_pos
            
        return self.x[0, 0], {'predictions': predictions}


# =============================================================================
# 3. SCENARIO: "MISSILE INTERCEPT"
# =============================================================================
def run_prophet_simulation():
    print("🎯 INITIALIZING 'MISSILE INTERCEPT' SCENARIO...")
    np.random.seed(2024)
    
    steps = 400
    noise_level = 1.0
    horizons = [1, 3, 5]
    
    # --- Generate Target Path: Evasive Missile ---
    t = np.linspace(0, 15, steps)
    
    # Base trajectory: accelerating curve with evasive weaves
    true_path = (
        20 * np.sin(0.3 * t) +             # Primary motion
        5 * np.sin(1.5 * t) +              # Evasive weave
        0.5 * t**1.5                        # Acceleration
    )
    
    # Add sudden direction changes (jinks) at specific points
    true_path[100:] += 8
    true_path[250:] -= 12
    true_path[320:] += 6
    
    # Noisy observations
    obs = true_path + np.random.normal(0, noise_level, steps)
    
    # Add packet loss zones (signal freeze)
    freeze_mask = np.zeros(steps, dtype=bool)
    freeze_zones = [(80, 95), (200, 215), (340, 355)]
    for start, end in freeze_zones:
        freeze_mask[start:end] = True
        obs[start:end] = obs[start - 1]  # Freeze at last value
    
    # --- Initialize Trackers ---
    dda = DDA_Prophet(noise_profile=noise_level)
    kalman = KalmanPredictor(dt=1.0, std_meas=noise_level, horizons=horizons)
    
    # Storage
    dda_estimates = []
    dda_predictions = {h: [] for h in horizons}
    dda_modes = []
    
    kalman_estimates = []
    kalman_predictions = {h: [] for h in horizons}
    
    print("⚔️  ENGAGING INTERCEPT SOLUTION...")
    
    for i in range(steps):
        # DDA Prophet
        est, info = dda.update(obs[i])
        dda_estimates.append(est)
        dda_modes.append(info['mode'])
        for h in horizons:
            dda_predictions[h].append(info['predictions'][h])
        
        # Kalman
        k_est, k_info = kalman.update(obs[i])
        kalman_estimates.append(k_est)
        for h in horizons:
            kalman_predictions[h].append(k_info['predictions'][h])
    
    # Convert to arrays
    dda_estimates = np.array(dda_estimates)
    kalman_estimates = np.array(kalman_estimates)
    for h in horizons:
        dda_predictions[h] = np.array(dda_predictions[h])
        kalman_predictions[h] = np.array(kalman_predictions[h])
    
    # --- EVALUATION: Prediction Accuracy ---
    print("\n" + "=" * 70)
    print("🏆 PREDICTION ACCURACY SCORECARD")
    print("=" * 70)
    print(f"{'Horizon':<12} {'Kalman MSE':<15} {'DDA MSE':<15} {'Winner':<12} {'Improvement':<12}")
    print("-" * 70)
    
    results = {}
    for h in horizons:
        # Shift true path forward by horizon to get "ground truth at T+h"
        # We need the actual future position, compared to our prediction made at T
        if h < steps:
            true_future = true_path[h:]
            dda_pred_aligned = dda_predictions[h][:-h]
            kalman_pred_aligned = kalman_predictions[h][:-h]
            
            mse_dda = np.mean((true_future - dda_pred_aligned) ** 2)
            mse_kalman = np.mean((true_future - kalman_pred_aligned) ** 2)
            
            winner = "DDA" if mse_dda < mse_kalman else "KALMAN"
            improvement = ((mse_kalman - mse_dda) / mse_kalman * 100) if mse_dda < mse_kalman else 0
            
            results[h] = {'dda': mse_dda, 'kalman': mse_kalman, 'winner': winner}
            
            print(f"T+{h:<10} {mse_kalman:<15.4f} {mse_dda:<15.4f} {winner:<12} {improvement:+.1f}%")
    
    # Tracking accuracy (T+0)
    mse_dda_track = np.mean((true_path - dda_estimates) ** 2)
    mse_kalman_track = np.mean((true_path - kalman_estimates) ** 2)
    print("-" * 70)
    print(f"{'T+0 (Track)':<12} {mse_kalman_track:<15.4f} {mse_dda_track:<15.4f} {'DDA' if mse_dda_track < mse_kalman_track else 'KALMAN':<12}")
    
    # Count wins
    dda_wins = sum(1 for r in results.values() if r['winner'] == 'DDA')
    print("\n" + "=" * 70)
    if dda_wins >= 2:
        print(f"🏆 OVERALL WINNER: DDA PROPHET ({dda_wins}/{len(horizons)} horizons)")
    else:
        print(f"🏆 OVERALL WINNER: KALMAN ({len(horizons) - dda_wins}/{len(horizons)} horizons)")
    print("=" * 70)
    
    # --- VISUALIZATION ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Tracking + Predictions
    ax1 = axes[0]
    ax1.plot(true_path, 'k-', lw=3, alpha=0.3, label='TRUE PATH')
    ax1.plot(obs, 'k.', ms=1, alpha=0.2, label='Observations')
    ax1.plot(dda_estimates, 'r-', lw=1.5, label='DDA Estimate (T+0)')
    ax1.plot(kalman_estimates, 'g--', lw=1.5, label='Kalman Estimate (T+0)')
    
    # Highlight freeze zones
    for start, end in freeze_zones:
        ax1.axvspan(start, end, color='blue', alpha=0.1)
    
    # Highlight jinks
    for jink_point in [100, 250, 320]:
        ax1.axvline(jink_point, color='orange', alpha=0.3, linestyle='--')
    
    ax1.set_title("DDA Prophet vs Kalman: Missile Intercept Tracking", fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Position")
    
    # Plot 2: Prediction Comparison at T+5
    ax2 = axes[1]
    h_show = 5
    ax2.plot(true_path, 'k-', lw=3, alpha=0.3, label='TRUE PATH')
    ax2.plot(dda_predictions[h_show], 'r-', lw=1.5, label=f'DDA Prediction (T+{h_show})')
    ax2.plot(kalman_predictions[h_show], 'g--', lw=1.5, label=f'Kalman Prediction (T+{h_show})')
    ax2.set_title(f"Extrapolation Quality: T+{h_show} Predictions vs True Future", fontsize=11)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("Position")
    
    # Plot 3: Mode Switching
    ax3 = axes[2]
    mode_colors = {0: 'green', 1: 'red', 2: 'blue'}
    mode_labels = {0: 'Pursuit', 1: 'Saccade', 2: 'Coasting'}
    
    for i, mode in enumerate(dda_modes):
        ax3.axvspan(i, i+1, color=mode_colors[mode], alpha=0.3)
    
    # Create legend patches
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, alpha=0.5, label=mode_labels[m]) 
                       for m, c in mode_colors.items()]
    ax3.legend(handles=legend_elements, loc='upper right')
    ax3.set_title("DDA Internal State: Mode Switching", fontsize=11)
    ax3.set_xlabel("Time Step")
    ax3.set_ylabel("Mode")
    ax3.set_ylim(-0.5, 2.5)
    ax3.set_yticks([0, 1, 2])
    ax3.set_yticklabels(['Pursuit', 'Saccade', 'Coast'])
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_prophet_proof.png', dpi=150)
    print("\n✓ Evidence saved to dda_prophet_proof.png")


if __name__ == "__main__":
    run_prophet_simulation()
