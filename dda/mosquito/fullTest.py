"""
DDA MOSQUITO TRACKER - SYNTHETIC TEST SUITE v1.0
=================================================
Generates synthetic mosquito flight patterns for testing
the DDA tracker without real footage.

Simulates realistic insect flight dynamics:
    - Erratic Brownian hovering
    - Sudden saccadic direction changes  
    - Burst-coast acceleration patterns
    - Multiple behavioral modes

Usage:
    python dda_mosquito_test.py              # Run interactive test
    python dda_mosquito_test.py --benchmark  # Run accuracy benchmark
    python dda_mosquito_test.py --export     # Export test video

Requirements:
    pip install opencv-python numpy
"""

import cv2
import numpy as np
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
import argparse

# Import the tracker from main module
from dda_mosquito_tracker import DDATracker2D


# ═══════════════════════════════════════════════════════════════════════════════
# FLIGHT BEHAVIOR MODES
# ═══════════════════════════════════════════════════════════════════════════════
class FlightMode(Enum):
    HOVER = "hover"           # Erratic stationary hovering
    CRUISE = "cruise"         # Steady directional flight
    SACCADE = "saccade"       # Sudden direction change
    BURST = "burst"           # Rapid acceleration burst
    COAST = "coast"           # Decelerating glide
    LAND = "land"             # Slowing to stationary
    ESCAPE = "escape"         # High-speed evasive maneuver


@dataclass
class FlightState:
    """Current state of synthetic mosquito"""
    x: float
    y: float
    vx: float
    vy: float
    mode: FlightMode
    mode_timer: float         # Time remaining in current mode
    target_x: float = None    # For directed flight
    target_y: float = None


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC MOSQUITO GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
class SyntheticMosquito:
    """
    Generates realistic mosquito flight trajectories.
    
    Based on observed insect flight dynamics:
    - Wingbeat-induced micro-oscillations
    - Lévy flight patterns (occasional long jumps)
    - Saccadic direction changes
    - Burst-coast locomotion
    """
    
    def __init__(self, 
                 frame_width=640, 
                 frame_height=480,
                 difficulty="medium"):
        
        self.width = frame_width
        self.height = frame_height
        self.margin = 50  # Keep away from edges
        
        # Difficulty presets affect speed and erraticism
        self.difficulty_params = {
            "easy": {
                "base_speed": 80,
                "hover_noise": 15,
                "saccade_prob": 0.02,
                "saccade_speed": 200,
                "burst_prob": 0.01,
            },
            "medium": {
                "base_speed": 150,
                "hover_noise": 30,
                "saccade_prob": 0.05,
                "saccade_speed": 400,
                "burst_prob": 0.03,
            },
            "hard": {
                "base_speed": 250,
                "hover_noise": 50,
                "saccade_prob": 0.08,
                "saccade_speed": 600,
                "burst_prob": 0.05,
            },
            "nightmare": {
                "base_speed": 400,
                "hover_noise": 80,
                "saccade_prob": 0.12,
                "saccade_speed": 900,
                "burst_prob": 0.08,
            }
        }
        
        self.params = self.difficulty_params.get(difficulty, self.difficulty_params["medium"])
        
        # Initialize state
        self.state = FlightState(
            x=frame_width / 2,
            y=frame_height / 2,
            vx=0,
            vy=0,
            mode=FlightMode.HOVER,
            mode_timer=np.random.uniform(0.5, 2.0)
        )
        
        # Trajectory history (ground truth)
        self.history = deque(maxlen=1000)
        self.frame_count = 0
        
    def update(self, dt):
        """
        Advance simulation by dt seconds.
        
        Returns:
            (x, y, vx, vy, mode) - Ground truth position and velocity
        """
        self.frame_count += 1
        
        # Decrement mode timer
        self.state.mode_timer -= dt
        
        # Check for mode transitions
        if self.state.mode_timer <= 0:
            self._transition_mode()
        
        # Apply mode-specific dynamics
        if self.state.mode == FlightMode.HOVER:
            self._update_hover(dt)
        elif self.state.mode == FlightMode.CRUISE:
            self._update_cruise(dt)
        elif self.state.mode == FlightMode.SACCADE:
            self._update_saccade(dt)
        elif self.state.mode == FlightMode.BURST:
            self._update_burst(dt)
        elif self.state.mode == FlightMode.COAST:
            self._update_coast(dt)
        elif self.state.mode == FlightMode.ESCAPE:
            self._update_escape(dt)
        
        # Add wingbeat micro-oscillation (high frequency noise)
        wingbeat_freq = 300  # Hz (real mosquito ~300-600Hz)
        wingbeat_amp = 0.5   # pixels
        t = self.frame_count * dt
        micro_x = wingbeat_amp * np.sin(2 * np.pi * wingbeat_freq * t)
        micro_y = wingbeat_amp * np.sin(2 * np.pi * wingbeat_freq * t + np.pi/4)
        
        # Update position
        self.state.x += self.state.vx * dt + micro_x
        self.state.y += self.state.vy * dt + micro_y
        
        # Boundary handling - bounce off edges
        self._handle_boundaries()
        
        # Store ground truth
        self.history.append({
            'frame': self.frame_count,
            'x': self.state.x,
            'y': self.state.y,
            'vx': self.state.vx,
            'vy': self.state.vy,
            'mode': self.state.mode.value
        })
        
        return (self.state.x, self.state.y, 
                self.state.vx, self.state.vy, 
                self.state.mode)
    
    def _transition_mode(self):
        """Probabilistic state machine for flight mode transitions"""
        current = self.state.mode
        
        # Transition probabilities depend on current mode
        if current == FlightMode.HOVER:
            choices = [
                (FlightMode.HOVER, 0.5),
                (FlightMode.CRUISE, 0.25),
                (FlightMode.SACCADE, self.params["saccade_prob"] * 5),
                (FlightMode.BURST, self.params["burst_prob"] * 5),
            ]
        elif current == FlightMode.CRUISE:
            choices = [
                (FlightMode.CRUISE, 0.4),
                (FlightMode.HOVER, 0.3),
                (FlightMode.SACCADE, 0.2),
                (FlightMode.COAST, 0.1),
            ]
        elif current in [FlightMode.SACCADE, FlightMode.BURST, FlightMode.ESCAPE]:
            choices = [
                (FlightMode.COAST, 0.5),
                (FlightMode.CRUISE, 0.3),
                (FlightMode.HOVER, 0.2),
            ]
        elif current == FlightMode.COAST:
            choices = [
                (FlightMode.HOVER, 0.4),
                (FlightMode.CRUISE, 0.4),
                (FlightMode.SACCADE, 0.2),
            ]
        else:
            choices = [(FlightMode.HOVER, 1.0)]
        
        # Normalize and select
        modes, probs = zip(*choices)
        probs = np.array(probs)
        probs /= probs.sum()
        
        new_mode = np.random.choice(modes, p=probs)
        
        # Set mode duration
        durations = {
            FlightMode.HOVER: (0.5, 3.0),
            FlightMode.CRUISE: (0.3, 1.5),
            FlightMode.SACCADE: (0.05, 0.15),  # Very brief!
            FlightMode.BURST: (0.1, 0.3),
            FlightMode.COAST: (0.2, 0.8),
            FlightMode.ESCAPE: (0.1, 0.4),
        }
        
        dur_range = durations.get(new_mode, (0.5, 1.0))
        self.state.mode_timer = np.random.uniform(*dur_range)
        self.state.mode = new_mode
        
        # Initialize mode-specific state
        if new_mode == FlightMode.CRUISE:
            angle = np.random.uniform(0, 2 * np.pi)
            speed = self.params["base_speed"] * np.random.uniform(0.5, 1.0)
            self.state.target_x = self.state.x + np.cos(angle) * 500
            self.state.target_y = self.state.y + np.sin(angle) * 500
            
        elif new_mode == FlightMode.SACCADE:
            # Sudden random direction at high speed
            angle = np.random.uniform(0, 2 * np.pi)
            speed = self.params["saccade_speed"]
            self.state.vx = np.cos(angle) * speed
            self.state.vy = np.sin(angle) * speed
            
        elif new_mode == FlightMode.BURST:
            # Accelerate in current direction or random
            if np.sqrt(self.state.vx**2 + self.state.vy**2) > 10:
                # Continue current direction
                angle = np.arctan2(self.state.vy, self.state.vx)
            else:
                angle = np.random.uniform(0, 2 * np.pi)
            self.state.target_x = np.cos(angle)  # Store unit vector
            self.state.target_y = np.sin(angle)
            
        elif new_mode == FlightMode.ESCAPE:
            # High speed away from center (simulates predator avoidance)
            dx = self.state.x - self.width / 2
            dy = self.state.y - self.height / 2
            dist = np.sqrt(dx**2 + dy**2) + 1
            self.state.vx = (dx / dist) * self.params["saccade_speed"] * 1.5
            self.state.vy = (dy / dist) * self.params["saccade_speed"] * 1.5
    
    def _update_hover(self, dt):
        """Erratic stationary hovering with Brownian-ish motion"""
        noise = self.params["hover_noise"]
        
        # Ornstein-Uhlenbeck process (mean-reverting noise)
        theta = 5.0  # Mean reversion rate
        self.state.vx += theta * (0 - self.state.vx) * dt + noise * np.random.randn() * np.sqrt(dt)
        self.state.vy += theta * (0 - self.state.vy) * dt + noise * np.random.randn() * np.sqrt(dt)
        
        # Occasional micro-saccades even while hovering
        if np.random.random() < self.params["saccade_prob"]:
            angle = np.random.uniform(0, 2 * np.pi)
            impulse = self.params["hover_noise"] * 3
            self.state.vx += np.cos(angle) * impulse
            self.state.vy += np.sin(angle) * impulse
    
    def _update_cruise(self, dt):
        """Steady directional flight toward target"""
        if self.state.target_x is None:
            return
        
        # Steer toward target
        dx = self.state.target_x - self.state.x
        dy = self.state.target_y - self.state.y
        dist = np.sqrt(dx**2 + dy**2) + 1
        
        target_vx = (dx / dist) * self.params["base_speed"]
        target_vy = (dy / dist) * self.params["base_speed"]
        
        # Smooth steering
        steer_rate = 3.0
        self.state.vx += (target_vx - self.state.vx) * steer_rate * dt
        self.state.vy += (target_vy - self.state.vy) * steer_rate * dt
        
        # Add slight noise
        self.state.vx += np.random.randn() * 10 * dt
        self.state.vy += np.random.randn() * 10 * dt
    
    def _update_saccade(self, dt):
        """Maintain high velocity during saccade (already set in transition)"""
        # Just add slight drag
        drag = 0.95
        self.state.vx *= drag
        self.state.vy *= drag
    
    def _update_burst(self, dt):
        """Rapid acceleration burst"""
        accel = self.params["saccade_speed"] * 3  # High acceleration
        self.state.vx += self.state.target_x * accel * dt
        self.state.vy += self.state.target_y * accel * dt
        
        # Cap velocity
        speed = np.sqrt(self.state.vx**2 + self.state.vy**2)
        max_speed = self.params["saccade_speed"]
        if speed > max_speed:
            self.state.vx = (self.state.vx / speed) * max_speed
            self.state.vy = (self.state.vy / speed) * max_speed
    
    def _update_coast(self, dt):
        """Decelerating glide"""
        drag = 0.92
        self.state.vx *= drag
        self.state.vy *= drag
    
    def _update_escape(self, dt):
        """High-speed evasive flight"""
        # Slight random walk at high speed
        self.state.vx += np.random.randn() * 50 * dt
        self.state.vy += np.random.randn() * 50 * dt
        
        # Slight drag
        self.state.vx *= 0.98
        self.state.vy *= 0.98
    
    def _handle_boundaries(self):
        """Bounce off frame boundaries"""
        if self.state.x < self.margin:
            self.state.x = self.margin
            self.state.vx = abs(self.state.vx)
        elif self.state.x > self.width - self.margin:
            self.state.x = self.width - self.margin
            self.state.vx = -abs(self.state.vx)
        
        if self.state.y < self.margin:
            self.state.y = self.margin
            self.state.vy = abs(self.state.vy)
        elif self.state.y > self.height - self.margin:
            self.state.y = self.height - self.margin
            self.state.vy = -abs(self.state.vy)
    
    def get_position(self):
        """Get current position"""
        return self.state.x, self.state.y
    
    def get_velocity(self):
        """Get current velocity"""
        return self.state.vx, self.state.vy
    
    def reset(self):
        """Reset to center with random initial state"""
        self.state = FlightState(
            x=self.width / 2 + np.random.uniform(-100, 100),
            y=self.height / 2 + np.random.uniform(-100, 100),
            vx=np.random.uniform(-50, 50),
            vy=np.random.uniform(-50, 50),
            mode=FlightMode.HOVER,
            mode_timer=np.random.uniform(0.5, 2.0)
        )
        self.history.clear()
        self.frame_count = 0


# ═══════════════════════════════════════════════════════════════════════════════
# FRAME RENDERER
# ═══════════════════════════════════════════════════════════════════════════════
class MosquitoRenderer:
    """
    Renders synthetic mosquito as realistic blob for detector testing.
    """
    
    def __init__(self, frame_width=640, frame_height=480):
        self.width = frame_width
        self.height = frame_height
        
        # Background with slight texture
        self.background = self._generate_background()
        
        # Rendering params
        self.mosquito_size = (8, 12)  # width, height range
        self.blur_amount = 1
        self.noise_level = 10
        
    def _generate_background(self):
        """Generate a slightly textured background"""
        bg = np.ones((self.height, self.width), dtype=np.uint8) * 200
        
        # Add Perlin-ish noise texture
        noise = np.random.randint(0, 30, (self.height // 4, self.width // 4), dtype=np.uint8)
        noise = cv2.resize(noise, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        bg = cv2.add(bg, noise)
        
        return bg
    
    def render(self, mosquito_x, mosquito_y, velocity=None, add_noise=True):
        """
        Render a frame with mosquito at given position.
        
        Args:
            mosquito_x, mosquito_y: Position
            velocity: (vx, vy) tuple for motion blur direction
            add_noise: Whether to add sensor noise
            
        Returns:
            BGR frame
        """
        # Start with background copy
        frame = self.background.copy()
        
        # Calculate mosquito size (slightly varies)
        size = np.random.randint(self.mosquito_size[0], self.mosquito_size[1])
        
        # Draw mosquito as dark ellipse
        x, y = int(mosquito_x), int(mosquito_y)
        
        # Body orientation based on velocity
        if velocity and (velocity[0] != 0 or velocity[1] != 0):
            angle = np.degrees(np.arctan2(velocity[1], velocity[0]))
        else:
            angle = np.random.uniform(0, 180)
        
        # Draw body (dark ellipse)
        cv2.ellipse(frame, (x, y), (size, size // 2), angle, 0, 360, 40, -1)
        
        # Add slight motion blur if moving fast
        if velocity:
            speed = np.sqrt(velocity[0]**2 + velocity[1]**2)
            if speed > 100:
                blur_len = min(15, int(speed / 50))
                if blur_len > 1:
                    # Create motion blur kernel
                    kernel = np.zeros((blur_len, blur_len))
                    kernel[blur_len // 2, :] = 1
                    kernel = kernel / blur_len
                    
                    # Rotate kernel to match velocity direction
                    M = cv2.getRotationMatrix2D((blur_len // 2, blur_len // 2), -angle, 1)
                    kernel = cv2.warpAffine(kernel, M, (blur_len, blur_len))
                    
                    frame = cv2.filter2D(frame, -1, kernel)
        
        # Add sensor noise
        if add_noise:
            noise = np.random.randint(-self.noise_level, self.noise_level, 
                                      frame.shape, dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Slight blur (camera defocus)
        frame = cv2.GaussianBlur(frame, (3, 3), 0)
        
        # Convert to BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        return frame_bgr


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════
class TrackerBenchmark:
    """
    Benchmarks DDA tracker against ground truth synthetic trajectories.
    """
    
    def __init__(self, difficulty="medium"):
        self.difficulty = difficulty
        self.results = []
        
    def run(self, duration_sec=30, prediction_horizons=[20, 50, 80, 120]):
        """
        Run benchmark for specified duration.
        
        Args:
            duration_sec: How long to run test
            prediction_horizons: List of prediction times (ms) to test
            
        Returns:
            dict with benchmark results
        """
        print("\n" + "="*60)
        print("  🧪 DDA TRACKER BENCHMARK")
        print("="*60)
        print(f"  Difficulty: {self.difficulty}")
        print(f"  Duration: {duration_sec}s")
        print(f"  Testing horizons: {prediction_horizons}ms")
        print("="*60 + "\n")
        
        results = {}
        
        for horizon in prediction_horizons:
            print(f"  Testing {horizon}ms prediction horizon...")
            
            # Create fresh instances
            mosquito = SyntheticMosquito(difficulty=self.difficulty)
            tracker = DDATracker2D(
                P0_stable=0.8,
                P0_saccade=0.1,
                saccade_thresh=4.0,
                prediction_ms=horizon
            )
            
            # Metrics
            position_errors = []
            prediction_errors = []
            mode_detections = {mode.value: {'correct': 0, 'total': 0} for mode in FlightMode}
            
            # Run simulation
            dt = 1/60  # 60 FPS
            frames = int(duration_sec / dt)
            
            future_buffer = deque(maxlen=int(horizon / 1000 / dt) + 1)
            
            for frame in range(frames):
                # Update ground truth
                gt_x, gt_y, gt_vx, gt_vy, gt_mode = mosquito.update(dt)
                
                # Store for future prediction validation
                future_buffer.append((gt_x, gt_y))
                
                # Update tracker
                result = tracker.update(gt_x, gt_y)
                
                # Position error (filtered vs actual)
                pos_err = np.sqrt(
                    (result['filtered_x'] - gt_x)**2 + 
                    (result['filtered_y'] - gt_y)**2
                )
                position_errors.append(pos_err)
                
                # Prediction error (compare prediction from N frames ago to now)
                if len(future_buffer) == future_buffer.maxlen:
                    # We stored a prediction, now we can compare
                    pred_err = np.sqrt(
                        (result['predicted_x'] - gt_x)**2 + 
                        (result['predicted_y'] - gt_y)**2
                    )
                    prediction_errors.append(pred_err)
                
                # Mode detection accuracy
                detected_saccade = result['mode'] == 'SACCADE'
                actual_saccade = gt_mode in [FlightMode.SACCADE, FlightMode.BURST, FlightMode.ESCAPE]
                
                mode_detections[gt_mode.value]['total'] += 1
                if (detected_saccade and actual_saccade) or (not detected_saccade and not actual_saccade):
                    mode_detections[gt_mode.value]['correct'] += 1
            
            # Calculate stats
            results[horizon] = {
                'position_error_mean': np.mean(position_errors),
                'position_error_std': np.std(position_errors),
                'position_error_max': np.max(position_errors),
                'prediction_error_mean': np.mean(prediction_errors) if prediction_errors else 0,
                'prediction_error_std': np.std(prediction_errors) if prediction_errors else 0,
                'prediction_error_max': np.max(prediction_errors) if prediction_errors else 0,
                'mode_accuracy': mode_detections
            }
            
            print(f"    Position error: {results[horizon]['position_error_mean']:.2f} ± "
                  f"{results[horizon]['position_error_std']:.2f} px")
            print(f"    Prediction error: {results[horizon]['prediction_error_mean']:.2f} ± "
                  f"{results[horizon]['prediction_error_std']:.2f} px")
        
        self._print_summary(results)
        return results
    
    def _print_summary(self, results):
        """Print formatted benchmark summary"""
        print("\n" + "="*60)
        print("  📊 BENCHMARK RESULTS")
        print("="*60)
        print(f"  {'Horizon':<12} {'Pos Error':<15} {'Pred Error':<15} {'Improvement':<12}")
        print("  " + "-"*54)
        
        for horizon, data in results.items():
            pos_err = data['position_error_mean']
            pred_err = data['prediction_error_mean']
            
            # Improvement = how much better prediction is vs no prediction
            # (comparing pred error to what position error would be at that horizon)
            improvement = ((pos_err - pred_err) / pos_err * 100) if pos_err > 0 else 0
            
            print(f"  {horizon:>4}ms      {pos_err:>6.2f} px       {pred_err:>6.2f} px       "
                  f"{improvement:>+6.1f}%")
        
        print("="*60 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE TEST HARNESS
# ═══════════════════════════════════════════════════════════════════════════════
class InteractiveTest:
    """
    Visual interactive test of the tracker against synthetic mosquito.
    """
    
    def __init__(self, difficulty="medium"):
        self.width = 640
        self.height = 480
        
        self.mosquito = SyntheticMosquito(self.width, self.height, difficulty)
        self.renderer = MosquitoRenderer(self.width, self.height)
        self.tracker = DDATracker2D(
            P0_stable=0.8,
            P0_saccade=0.1,
            saccade_thresh=4.0,
            prediction_ms=80
        )
        
        self.difficulty = difficulty
        self.paused = False
        
        # Real-time metrics
        self.position_errors = deque(maxlen=100)
        self.prediction_errors = deque(maxlen=100)
        
    def run(self):
        """Run interactive visualization"""
        
        print("\n" + "="*60)
        print("  🦟 SYNTHETIC MOSQUITO TEST")
        print("="*60)
        print("  Controls:")
        print("    [Q] Quit")
        print("    [R] Reset mosquito")
        print("    [SPACE] Pause/Resume")
        print("    [1-4] Difficulty (1=easy, 4=nightmare)")
        print("    [+/-] Adjust prediction horizon")
        print("="*60 + "\n")
        
        dt = 1/60
        
        while True:
            if not self.paused:
                # Update ground truth
                gt_x, gt_y, gt_vx, gt_vy, gt_mode = self.mosquito.update(dt)
                
                # Render frame
                frame = self.renderer.render(gt_x, gt_y, (gt_vx, gt_vy))
                
                # Update tracker
                result = self.tracker.update(gt_x, gt_y)
                
                # Calculate errors
                pos_err = np.sqrt(
                    (result['filtered_x'] - gt_x)**2 + 
                    (result['filtered_y'] - gt_y)**2
                )
                self.position_errors.append(pos_err)
                
                pred_err = np.sqrt(
                    (result['predicted_x'] - gt_x)**2 + 
                    (result['predicted_y'] - gt_y)**2
                )
                self.prediction_errors.append(pred_err)
                
                # Draw visualization
                vis = self._draw_visualization(frame, gt_x, gt_y, gt_mode, result)
                
            cv2.imshow('DDA Tracker Test', vis)
            
            # Handle keys
            key = cv2.waitKey(16) & 0xFF  # ~60fps
            
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.mosquito.reset()
                self.tracker.reset()
                self.position_errors.clear()
                self.prediction_errors.clear()
                print("  🔄 Reset")
            elif key == ord(' '):
                self.paused = not self.paused
                print(f"  {'⏸️  Paused' if self.paused else '▶️  Running'}")
            elif key == ord('1'):
                self._set_difficulty("easy")
            elif key == ord('2'):
                self._set_difficulty("medium")
            elif key == ord('3'):
                self._set_difficulty("hard")
            elif key == ord('4'):
                self._set_difficulty("nightmare")
            elif key == ord('=') or key == ord('+'):
                self.tracker.prediction_ms = min(200, self.tracker.prediction_ms + 10)
                print(f"  Prediction horizon: {self.tracker.prediction_ms}ms")
            elif key == ord('-'):
                self.tracker.prediction_ms = max(10, self.tracker.prediction_ms - 10)
                print(f"  Prediction horizon: {self.tracker.prediction_ms}ms")
        
        cv2.destroyAllWindows()
    
    def _set_difficulty(self, diff):
        """Change difficulty level"""
        self.difficulty = diff
        self.mosquito = SyntheticMosquito(self.width, self.height, diff)
        self.tracker.reset()
        self.position_errors.clear()
        self.prediction_errors.clear()
        print(f"  Difficulty: {diff.upper()}")
    
    def _draw_visualization(self, frame, gt_x, gt_y, gt_mode, result):
        """Draw tracking overlay"""
        vis = frame.copy()
        
        # Ground truth (actual position) - white
        cv2.circle(vis, (int(gt_x), int(gt_y)), 12, (255, 255, 255), 1)
        
        # Filtered position (tracker's estimate of NOW) - green
        fx, fy = int(result['filtered_x']), int(result['filtered_y'])
        cv2.circle(vis, (fx, fy), 8, (0, 255, 0), 2)
        
        # Predicted position (where tracker thinks it WILL BE) - red
        px, py = int(result['predicted_x']), int(result['predicted_y'])
        cv2.circle(vis, (px, py), 10, (0, 0, 255), 2)
        
        # Prediction vector
        cv2.arrowedLine(vis, (fx, fy), (px, py), (255, 0, 255), 2)
        
        # Draw trajectory history
        history = list(self.mosquito.history)[-50:]
        for i in range(1, len(history)):
            alpha = i / len(history)
            color = (int(100 * alpha), int(100 * alpha), int(100 * alpha))
            pt1 = (int(history[i-1]['x']), int(history[i-1]['y']))
            pt2 = (int(history[i]['x']), int(history[i]['y']))
            cv2.line(vis, pt1, pt2, color, 1)
        
        # Info panel
        avg_pos_err = np.mean(self.position_errors) if self.position_errors else 0
        avg_pred_err = np.mean(self.prediction_errors) if self.prediction_errors else 0
        
        info = [
            f"Difficulty: {self.difficulty.upper()}",
            f"GT Mode: {gt_mode.value}",
            f"Tracker Mode: {result['mode']}",
            f"Speed: {result['speed']:.0f} px/s",
            f"Prediction: {self.tracker.prediction_ms}ms",
            f"",
            f"Pos Error: {avg_pos_err:.1f} px",
            f"Pred Error: {avg_pred_err:.1f} px",
        ]
        
        # Background for text
        cv2.rectangle(vis, (5, 5), (200, 180), (0, 0, 0), -1)
        cv2.rectangle(vis, (5, 5), (200, 180), (100, 100, 100), 1)
        
        for i, text in enumerate(info):
            cv2.putText(vis, text, (10, 25 + i*18), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        # Legend
        legend_y = self.height - 60
        cv2.circle(vis, (20, legend_y), 6, (255, 255, 255), 1)
        cv2.putText(vis, "Ground Truth", (35, legend_y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.circle(vis, (20, legend_y + 20), 6, (0, 255, 0), 2)
        cv2.putText(vis, "Filtered (NOW)", (35, legend_y + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        cv2.circle(vis, (20, legend_y + 40), 6, (0, 0, 255), 2)
        cv2.putText(vis, "Predicted (FUTURE)", (35, legend_y + 45), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        return vis


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════
class VideoExporter:
    """Export synthetic test footage for external analysis"""
    
    def __init__(self, difficulty="medium"):
        self.width = 640
        self.height = 480
        self.mosquito = SyntheticMosquito(self.width, self.height, difficulty)
        self.renderer = MosquitoRenderer(self.width, self.height)
        
    def export(self, filename="synthetic_mosquito.mp4", duration_sec=30, fps=60):
        """Export video file"""
        
        print(f"\n  📹 Exporting {duration_sec}s of synthetic footage...")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, fps, (self.width, self.height))
        
        dt = 1 / fps
        frames = int(duration_sec * fps)
        
        for i in range(frames):
            gt_x, gt_y, gt_vx, gt_vy, _ = self.mosquito.update(dt)
            frame = self.renderer.render(gt_x, gt_y, (gt_vx, gt_vy))
            out.write(frame)
            
            if (i + 1) % (fps * 5) == 0:
                print(f"    {(i + 1) / fps:.0f}s / {duration_sec}s")
        
        out.release()
        print(f"  ✅ Saved to {filename}\n")
        
        # Also export ground truth
        gt_filename = filename.replace('.mp4', '_ground_truth.csv')
        self._export_ground_truth(gt_filename)
        
    def _export_ground_truth(self, filename):
        """Export trajectory ground truth to CSV"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['frame', 'x', 'y', 'vx', 'vy', 'mode'])
            writer.writeheader()
            for entry in self.mosquito.history:
                writer.writerow(entry)
        
        print(f"  ✅ Ground truth saved to {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DDA Tracker Test Suite")
    parser.add_argument('--benchmark', action='store_true', help='Run accuracy benchmark')
    parser.add_argument('--export', action='store_true', help='Export test video')
    parser.add_argument('--difficulty', type=str, default='medium',
                       choices=['easy', 'medium', 'hard', 'nightmare'],
                       help='Difficulty level')
    parser.add_argument('--duration', type=int, default=30, help='Test duration (seconds)')
    
    args = parser.parse_args()
    
    if args.benchmark:
        benchmark = TrackerBenchmark(difficulty=args.difficulty)
        benchmark.run(duration_sec=args.duration)
        
    elif args.export:
        exporter = VideoExporter(difficulty=args.difficulty)
        exporter.export(duration_sec=args.duration)
        
    else:
        # Interactive mode
        test = InteractiveTest(difficulty=args.difficulty)
        test.run()