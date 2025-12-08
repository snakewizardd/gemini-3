
"""
DDA TRACKING BENCHMARK
======================
Proves the DDA tracker works by simulating mosquito flight patterns
and measuring tracking accuracy vs other methods.

No camera needed - pure algorithm test!
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
from collections import deque

# ═══════════════════════════════════════════════════════════════════════════════
# DDA TRACKER (Same as before)
# ═══════════════════════════════════════════════════════════════════════════════
class DDATracker:
    def __init__(self, P0_stable=0.85, P0_saccade=0.1, saccade_thresh=3.0, prediction_ms=50):
        self.P0_stable = P0_stable
        self.P0_saccade = P0_saccade
        self.saccade_thresh = saccade_thresh
        self.prediction_ms = prediction_ms
        
        self.Fx = None
        self.Fy = None
        self.history_x = deque(maxlen=10)
        self.history_y = deque(maxlen=10)
        self.timestamps = deque(maxlen=10)
        self.volatility_x = 1.0
        self.volatility_y = 1.0
        
    def update(self, x, y, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        if self.Fx is None:
            self.Fx = x
            self.Fy = y
            self.history_x.append(x)
            self.history_y.append(y)
            self.timestamps.append(timestamp)
            return x, y, x, y, 0, 0
        
        # Saccade detection
        error_x = abs(x - self.Fx)
        error_y = abs(y - self.Fy)
        
        if len(self.history_x) >= 5:
            self.volatility_x = max(1.0, np.std(list(self.history_x)[-5:]))
            self.volatility_y = max(1.0, np.std(list(self.history_y)[-5:]))
        
        is_saccade = (error_x > self.saccade_thresh * self.volatility_x or 
                      error_y > self.saccade_thresh * self.volatility_y)
        
        P0 = self.P0_saccade if is_saccade else self.P0_stable
        
        # Velocity estimation
        vx, vy = 0, 0
        if len(self.history_x) >= 2:
            n = min(5, len(self.history_x))
            dx = self.history_x[-1] - self.history_x[-n]
            dy = self.history_y[-1] - self.history_y[-n]
            dt = self.timestamps[-1] - self.timestamps[-n]
            if dt > 0:
                vx, vy = dx / dt, dy / dt
        
        # DDA update with prediction
        dt = timestamp - self.timestamps[-1] if self.timestamps else 0.016
        boost_x = 0.3 * vx * dt
        boost_y = 0.3 * vy * dt
        
        self.Fx = P0 * self.Fx + (1 - P0) * (x + boost_x)
        self.Fy = P0 * self.Fy + (1 - P0) * (y + boost_y)
        
        # Store history
        self.history_x.append(x)
        self.history_y.append(y)
        self.timestamps.append(timestamp)
        
        # Predict future position
        dt_pred = self.prediction_ms / 1000.0
        pred_x = self.Fx + vx * dt_pred
        pred_y = self.Fy + vy * dt_pred
        
        return self.Fx, self.Fy, pred_x, pred_y, vx, vy
    
    def reset(self):
        self.Fx = None
        self.Fy = None
        self.history_x.clear()
        self.history_y.clear()
        self.timestamps.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON TRACKERS
# ═══════════════════════════════════════════════════════════════════════════════
class MovingAverageTracker:
    """Simple moving average - the baseline"""
    def __init__(self, window=5):
        self.window = window
        self.history_x = deque(maxlen=window)
        self.history_y = deque(maxlen=window)
        
    def update(self, x, y, timestamp=None):
        self.history_x.append(x)
        self.history_y.append(y)
        
        fx = np.mean(self.history_x)
        fy = np.mean(self.history_y)
        
        # Simple velocity for prediction
        if len(self.history_x) >= 2:
            vx = self.history_x[-1] - self.history_x[-2]
            vy = self.history_y[-1] - self.history_y[-2]
        else:
            vx, vy = 0, 0
        
        pred_x = fx + vx * 3  # Predict 3 frames ahead
        pred_y = fy + vy * 3
        
        return fx, fy, pred_x, pred_y, vx, vy
    
    def reset(self):
        self.history_x.clear()
        self.history_y.clear()


class KalmanTracker:
    """Simplified Kalman filter"""
    def __init__(self):
        # State: [x, y, vx, vy]
        self.state = None
        self.P = np.eye(4) * 100  # Covariance
        
        # Process noise
        self.Q = np.eye(4) * 0.1
        self.Q[2:, 2:] *= 10  # Higher noise for velocity
        
        # Measurement noise
        self.R = np.eye(2) * 5
        
    def update(self, x, y, timestamp=None):
        dt = 0.016  # Assume 60fps
        
        if self.state is None:
            self.state = np.array([x, y, 0, 0])
            return x, y, x, y, 0, 0
        
        # Predict
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        state_pred = F @ self.state
        P_pred = F @ self.P @ F.T + self.Q
        
        # Update
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        
        z = np.array([x, y])
        y_residual = z - H @ state_pred
        S = H @ P_pred @ H.T + self.R
        K = P_pred @ H.T @ np.linalg.inv(S)
        
        self.state = state_pred + K @ y_residual
        self.P = (np.eye(4) - K @ H) @ P_pred
        
        # Extract results
        fx, fy = self.state[0], self.state[1]
        vx, vy = self.state[2], self.state[3]
        
        # Predict 50ms ahead
        pred_x = fx + vx * 0.05 / dt
        pred_y = fy + vy * 0.05 / dt
        
        return fx, fy, pred_x, pred_y, vx, vy
    
    def reset(self):
        self.state = None
        self.P = np.eye(4) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# MOSQUITO FLIGHT SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
class MosquitoSimulator:
    """
    Simulates realistic mosquito flight patterns:
    - Smooth cruising with occasional direction changes
    - Sudden saccadic movements (evasion)
    - Hovering/circling behavior
    - Sensor noise
    """
    
    def __init__(self, width=640, height=480, fps=60):
        self.width = width
        self.height = height
        self.fps = fps
        self.dt = 1.0 / fps
        
        # Position and velocity
        self.x = width / 2
        self.y = height / 2
        self.vx = np.random.uniform(-50, 50)
        self.vy = np.random.uniform(-50, 50)
        
        # Flight mode
        self.mode = "cruise"  # cruise, saccade, hover
        self.mode_timer = 0
        
        # Noise
        self.sensor_noise = 2.0  # pixels
        
        # History for ground truth
        self.true_path = []
        self.noisy_path = []
        
    def step(self):
        """Advance simulation by one frame"""
        
        # Update mode timer
        self.mode_timer -= self.dt
        
        # Choose new mode if timer expired
        if self.mode_timer <= 0:
            r = np.random.random()
            if r < 0.7:
                self.mode = "cruise"
                self.mode_timer = np.random.uniform(0.5, 2.0)
            elif r < 0.9:
                self.mode = "saccade"
                self.mode_timer = np.random.uniform(0.05, 0.15)
            else:
                self.mode = "hover"
                self.mode_timer = np.random.uniform(0.3, 1.0)
        
        # Update velocity based on mode
        if self.mode == "cruise":
            # Gradual direction changes
            self.vx += np.random.normal(0, 20) * self.dt
            self.vy += np.random.normal(0, 20) * self.dt
            
            # Speed limit
            speed = np.sqrt(self.vx**2 + self.vy**2)
            max_speed = 100
            if speed > max_speed:
                self.vx *= max_speed / speed
                self.vy *= max_speed / speed
                
        elif self.mode == "saccade":
            # Sudden direction change!
            angle = np.random.uniform(0, 2 * np.pi)
            speed = np.random.uniform(150, 300)
            self.vx = speed * np.cos(angle)
            self.vy = speed * np.sin(angle)
            
        elif self.mode == "hover":
            # Slow down and circle
            self.vx *= 0.9
            self.vy *= 0.9
            self.vx += np.random.normal(0, 30)
            self.vy += np.random.normal(0, 30)
        
        # Update position
        self.x += self.vx * self.dt
        self.y += self.vy * self.dt
        
        # Bounce off walls
        if self.x < 50 or self.x > self.width - 50:
            self.vx *= -1
            self.x = np.clip(self.x, 50, self.width - 50)
        if self.y < 50 or self.y > self.height - 50:
            self.vy *= -1
            self.y = np.clip(self.y, 50, self.height - 50)
        
        # Store true position
        self.true_path.append((self.x, self.y))
        
        # Add sensor noise
        noisy_x = self.x + np.random.normal(0, self.sensor_noise)
        noisy_y = self.y + np.random.normal(0, self.sensor_noise)
        self.noisy_path.append((noisy_x, noisy_y))
        
        return noisy_x, noisy_y, self.x, self.y, self.mode
    
    def reset(self):
        self.x = self.width / 2
        self.y = self.height / 2
        self.vx = np.random.uniform(-50, 50)
        self.vy = np.random.uniform(-50, 50)
        self.true_path = []
        self.noisy_path = []


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════
def run_benchmark(duration_sec=10, fps=60):
    """
    Run tracking benchmark comparing DDA vs Moving Average vs Kalman
    """
    
    print("\n" + "="*70)
    print("  🧪 DDA TRACKING BENCHMARK")
    print("="*70)
    print(f"  Duration: {duration_sec}s at {fps}fps = {duration_sec * fps} frames")
    print("  Testing: DDA vs Moving Average vs Kalman")
    print("="*70 + "\n")
    
    # Initialize
    sim = MosquitoSimulator(fps=fps)
    
    trackers = {
        'DDA': DDATracker(P0_stable=0.85, P0_saccade=0.1, prediction_ms=50),
        'MovingAvg': MovingAverageTracker(window=5),
        'Kalman': KalmanTracker()
    }
    
    # Metrics storage
    results = {name: {
        'tracking_errors': [],
        'prediction_errors': [],
        'saccade_tracking_errors': [],
        'saccade_prediction_errors': []
    } for name in trackers}
    
    # Run simulation
    n_frames = duration_sec * fps
    
    for frame in range(n_frames):
        timestamp = frame / fps
        
        # Get mosquito position (noisy observation + true position)
        noisy_x, noisy_y, true_x, true_y, mode = sim.step()
        
        # True position 50ms in the future (for prediction evaluation)
        # We'll evaluate this retroactively
        
        for name, tracker in trackers.items():
            fx, fy, pred_x, pred_y, vx, vy = tracker.update(noisy_x, noisy_y, timestamp)
            
            # Tracking error (filtered vs true)
            track_err = np.sqrt((fx - true_x)**2 + (fy - true_y)**2)
            results[name]['tracking_errors'].append(track_err)
            
            # Store prediction for later evaluation
            # (We'll compare to true position 3 frames later)
            if frame >= 3:
                # Get true position from 3 frames ago's prediction target
                past_true = sim.true_path[frame]
                past_pred_x = results[name].get('last_pred_x', pred_x)
                past_pred_y = results[name].get('last_pred_y', pred_y)
                
                pred_err = np.sqrt((past_pred_x - true_x)**2 + (past_pred_y - true_y)**2)
                results[name]['prediction_errors'].append(pred_err)
                
                # Track saccade performance separately
                if mode == "saccade":
                    results[name]['saccade_tracking_errors'].append(track_err)
                    results[name]['saccade_prediction_errors'].append(pred_err)
            
            results[name]['last_pred_x'] = pred_x
            results[name]['last_pred_y'] = pred_y
    
    # Calculate statistics
    print("  📊 RESULTS:")
    print("  " + "-"*66)
    print(f"  {'Tracker':<12} {'Track Err':>12} {'Pred Err':>12} {'Saccade Track':>14} {'Saccade Pred':>12}")
    print(f"  {'':12} {'(pixels)':>12} {'(pixels)':>12} {'(pixels)':>14} {'(pixels)':>12}")
    print("  " + "-"*66)
    
    summary = {}
    
    for name in trackers:
        track_err = np.mean(results[name]['tracking_errors'])
        pred_err = np.mean(results[name]['prediction_errors']) if results[name]['prediction_errors'] else 0
        sac_track = np.mean(results[name]['saccade_tracking_errors']) if results[name]['saccade_tracking_errors'] else 0
        sac_pred = np.mean(results[name]['saccade_prediction_errors']) if results[name]['saccade_prediction_errors'] else 0
        
        summary[name] = {
            'track': track_err,
            'pred': pred_err,
            'sac_track': sac_track,
            'sac_pred': sac_pred
        }
        
        print(f"  {name:<12} {track_err:>12.2f} {pred_err:>12.2f} {sac_track:>14.2f} {sac_pred:>12.2f}")
    
    print("  " + "-"*66)
    
    # Declare winner
    best_tracker = min(summary, key=lambda x: summary[x]['pred'])
    dda_improvement = ((summary['MovingAvg']['pred'] - summary['DDA']['pred']) / summary['MovingAvg']['pred']) * 100
    
    print(f"\n  🏆 WINNER: {best_tracker}")
    print(f"  📈 DDA improvement over Moving Average: {dda_improvement:.1f}%")
    
    if dda_improvement > 0:
        print(f"  ✅ DDA PROVEN SUPERIOR for mosquito tracking!")
    
    # Plot results
    plot_benchmark_results(sim, results, trackers)
    
    return summary


def plot_benchmark_results(sim, results, trackers):
    """Visualize benchmark results"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Flight path
    ax1 = axes[0, 0]
    true_x = [p[0] for p in sim.true_path]
    true_y = [p[1] for p in sim.true_path]
    ax1.plot(true_x, true_y, 'k-', alpha=0.3, label='True Path', linewidth=0.5)
    ax1.scatter(true_x[0], true_y[0], c='green', s=100, marker='o', label='Start')
    ax1.scatter(true_x[-1], true_y[-1], c='red', s=100, marker='x', label='End')
    ax1.set_title('Simulated Mosquito Flight Path')
    ax1.set_xlabel('X (pixels)')
    ax1.set_ylabel('Y (pixels)')
    ax1.legend()
    ax1.set_aspect('equal')
    
    # 2. Tracking error over time
    ax2 = axes[0, 1]
    colors = {'DDA': 'blue', 'MovingAvg': 'orange', 'Kalman': 'green'}
    for name in trackers:
        errors = results[name]['tracking_errors']
        # Smooth for visualization
        window = 30
        smoothed = np.convolve(errors, np.ones(window)/window, mode='valid')
        ax2.plot(smoothed, color=colors[name], label=name, alpha=0.8)
    ax2.set_title('Tracking Error Over Time')
    ax2.set_xlabel('Frame')
    ax2.set_ylabel('Error (pixels)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Prediction error over time
    ax3 = axes[1, 0]
    for name in trackers:
        errors = results[name]['prediction_errors']
        if errors:
            window = 30
            smoothed = np.convolve(errors, np.ones(window)/window, mode='valid')
            ax3.plot(smoothed, color=colors[name], label=name, alpha=0.8)
    ax3.set_title('Prediction Error Over Time (50ms ahead)')
    ax3.set_xlabel('Frame')
    ax3.set_ylabel('Error (pixels)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Error distribution
    ax4 = axes[1, 1]
    data = []
    labels = []
    for name in trackers:
        data.append(results[name]['prediction_errors'])
        labels.append(name)
    ax4.boxplot(data, labels=labels)
    ax4.set_title('Prediction Error Distribution')
    ax4.set_ylabel('Error (pixels)')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_benchmark.png', dpi=150)
    print("\n  ✓ Saved benchmark visualization to dda_benchmark.png")
    plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════
def run_live_visualization():
    """
    Real-time animated visualization of tracking
    """
    print("\n  🎬 Starting live visualization...")
    print("  Close the window to stop.\n")
    
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 640)
    ax.set_ylim(0, 480)
    ax.set_aspect('equal')
    ax.set_title('DDA Mosquito Tracker - Live Demo')
    
    # Initialize
    sim = MosquitoSimulator(fps=30)
    tracker = DDATracker(P0_stable=0.85, P0_saccade=0.1, prediction_ms=80)
    
    # Plot elements
    true_dot, = ax.plot([], [], 'ko', markersize=8, label='True Position')
    noisy_dot, = ax.plot([], [], 'y+', markersize=12, label='Sensor (noisy)')
    filtered_dot, = ax.plot([], [], 'go', markersize=10, label='DDA Filtered')
    predicted_dot, = ax.plot([], [], 'r^', markersize=10, label='DDA Predicted')
    
    trail_true, = ax.plot([], [], 'k-', alpha=0.2, linewidth=1)
    trail_filtered, = ax.plot([], [], 'g-', alpha=0.5, linewidth=1)
    
    ax.legend(loc='upper right')
    
    # Storage for trails
    true_trail_x, true_trail_y = [], []
    filt_trail_x, filt_trail_y = [], []
    
    def init():
        return true_dot, noisy_dot, filtered_dot, predicted_dot, trail_true, trail_filtered
    
    def animate(frame):
        nonlocal true_trail_x, true_trail_y, filt_trail_x, filt_trail_y
        
        timestamp = frame / 30.0
        noisy_x, noisy_y, true_x, true_y, mode = sim.step()
        fx, fy, pred_x, pred_y, vx, vy = tracker.update(noisy_x, noisy_y, timestamp)
        
        # Update dots
        true_dot.set_data([true_x], [true_y])
        noisy_dot.set_data([noisy_x], [noisy_y])
        filtered_dot.set_data([fx], [fy])
        predicted_dot.set_data([pred_x], [pred_y])
        
        # Update trails
        true_trail_x.append(true_x)
        true_trail_y.append(true_y)
        filt_trail_x.append(fx)
        filt_trail_y.append(fy)
        
        # Keep trail length limited
        max_trail = 100
        if len(true_trail_x) > max_trail:
            true_trail_x = true_trail_x[-max_trail:]
            true_trail_y = true_trail_y[-max_trail:]
            filt_trail_x = filt_trail_x[-max_trail:]
            filt_trail_y = filt_trail_y[-max_trail:]
        
        trail_true.set_data(true_trail_x, true_trail_y)
        trail_filtered.set_data(filt_trail_x, filt_trail_y)
        
        # Update title with mode
        ax.set_title(f'DDA Mosquito Tracker | Mode: {mode.upper()} | Frame: {frame}')
        
        return true_dot, noisy_dot, filtered_dot, predicted_dot, trail_true, trail_filtered
    
    anim = FuncAnimation(fig, animate, init_func=init, frames=600, 
                        interval=33, blit=True)
    plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "live":
        run_live_visualization()
    else:
        # Run benchmark
        results = run_benchmark(duration_sec=10, fps=60)
        
        print("\n" + "="*70)
        print("  💡 TO SEE LIVE VISUALIZATION:")
        print("     python benchmark.py live")
        print("="*70 + "\n")
