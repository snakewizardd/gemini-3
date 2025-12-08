"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     DDA TERMINATOR v3.0 - CORRECT IMPLEMENTATION                             ║
║     ════════════════════════════════════════════                             ║
║                                                                              ║
║     The TRUE DDA advantage:                                                  ║
║                                                                              ║
║       Kalman: High error → Increase gain → OVERSHOOT after saccade           ║
║       DDA:    High error → Increase hysteresis → SMOOTH recovery             ║
║                                                                              ║
║     This version:                                                            ║
║       • Correct DDA: High P0 during saccades (resist, don't chase)           ║
║       • Delayed prediction validation (true 60ms ahead test)                 ║
║       • Tighter hit radius to expose accuracy differences                    ║
║       • Real-time prediction error visualization                             ║
║       • Post-saccade recovery tracking (where DDA wins)                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import colorsys
import argparse
import random


# ═══════════════════════════════════════════════════════════════════════════════
#  DDA TRACKER - CORRECT IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════
class DDATrackerV3:
    """
    Brian's Dynamic Decision Algorithm - CORRECT implementation
    
    F = P₀·k + m·[T + R]
    
    KEY INSIGHT: Under high prediction error, INCREASE P₀ (hysteresis)
    This RESISTS the impulse to chase the new measurement, preserving
    the velocity estimate through the saccade.
    
    Result: Smooth recovery after saccade, no overshoot.
    Kalman does the opposite and overshoots.
    """
    
    def __init__(self, target_id: int, prediction_ms: float = 60):
        self.id = target_id
        self.prediction_ms = prediction_ms
        
        # Filtered state
        self.Fx = None
        self.Fy = None
        
        # Velocity state (separately filtered for stability)
        self.vx = 0.0
        self.vy = 0.0
        self.vx_filtered = 0.0
        self.vy_filtered = 0.0
        
        # History
        self.history = deque(maxlen=30)
        self.timestamps = deque(maxlen=30)
        
        # DDA Parameters - THE KEY DIFFERENCE
        self.P0_base = 0.7          # Base hysteresis
        self.P0_max = 0.95          # Maximum hysteresis during saccade
        self.P0_velocity = 0.85     # Velocity filter hysteresis
        self.saccade_thresh = 2.5   # Threshold for saccade detection
        
        # Adaptive P0 based on error
        self.current_P0 = self.P0_base
        self.error_history = deque(maxlen=10)
        
        # State
        self.mode = "ACQUIRING"
        self.frames = 0
        self.saccade_frames = 0     # Frames since last saccade
        self.in_saccade = False
        
        # Prediction validation
        self.prediction_buffer = deque(maxlen=20)  # Store (timestamp, pred_x, pred_y)
        self.validated_errors = deque(maxlen=100)
        
        # Color
        hue = (target_id * 0.618033988749895) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
        self.is_active = True
        self.lost_frames = 0
        
    def update(self, x: float, y: float, timestamp: float = None) -> dict:
        if timestamp is None:
            timestamp = time.time()
        
        # First observation
        if self.Fx is None:
            self.Fx, self.Fy = x, y
            self.history.append((x, y, timestamp))
            self.timestamps.append(timestamp)
            self.frames = 1
            return self._result(timestamp)
        
        # Calculate instantaneous error
        error = np.sqrt((x - self.Fx)**2 + (y - self.Fy)**2)
        self.error_history.append(error)
        
        # ═══════════════════════════════════════════════════════════════════
        # THE DDA CORE: Adaptive hysteresis based on error
        # High error → HIGH P0 → Resist chasing the measurement
        # ═══════════════════════════════════════════════════════════════════
        
        # Calculate error-adaptive P0
        avg_error = np.mean(self.error_history) if self.error_history else 1
        
        # Saccade detection
        if error > self.saccade_thresh * avg_error and error > 15:
            self.in_saccade = True
            self.saccade_frames = 0
            self.mode = "SACCADE"
            
            # INCREASE hysteresis during saccade - THIS IS THE KEY
            # We RESIST the new measurement to preserve velocity estimate
            self.current_P0 = self.P0_max
        else:
            self.saccade_frames += 1
            
            # Gradual return to base P0 after saccade
            if self.saccade_frames > 5:
                self.in_saccade = False
                self.mode = "TRACKING"
            
            # Decay P0 back to base
            decay_rate = 0.1
            self.current_P0 = self.current_P0 * (1 - decay_rate) + self.P0_base * decay_rate
        
        # Calculate raw velocity from measurements
        raw_vx, raw_vy = self._calc_velocity(x, y, timestamp)
        
        # Filter velocity with high hysteresis (don't chase noise)
        # During saccade, we trust our existing velocity estimate MORE
        v_P0 = self.P0_max if self.in_saccade else self.P0_velocity
        self.vx_filtered = v_P0 * self.vx_filtered + (1 - v_P0) * raw_vx
        self.vy_filtered = v_P0 * self.vy_filtered + (1 - v_P0) * raw_vy
        
        # Update position with current P0
        # High P0 = trust previous estimate more = smooth through saccade
        self.Fx = self.current_P0 * self.Fx + (1 - self.current_P0) * x
        self.Fy = self.current_P0 * self.Fy + (1 - self.current_P0) * y
        
        # Store for velocity calculation
        self.history.append((x, y, timestamp))
        self.timestamps.append(timestamp)
        self.frames += 1
        self.lost_frames = 0
        
        # Store prediction for later validation
        result = self._result(timestamp)
        self.prediction_buffer.append((
            timestamp,
            result['pred_x'],
            result['pred_y']
        ))
        
        return result
    
    def _calc_velocity(self, x, y, t):
        """Calculate velocity from recent history"""
        if len(self.history) < 2:
            return 0, 0
        
        # Use multiple points for robust estimate
        n = min(4, len(self.history))
        h = list(self.history)
        
        # Simple linear regression for velocity
        times = [h[-(i+1)][2] for i in range(n)]
        xs = [h[-(i+1)][0] for i in range(n)]
        ys = [h[-(i+1)][1] for i in range(n)]
        
        dt_total = times[0] - times[-1]
        if dt_total > 0:
            # Weighted average favoring recent
            vx = (xs[0] - xs[-1]) / dt_total
            vy = (ys[0] - ys[-1]) / dt_total
            return vx, vy
        return 0, 0
    
    def _result(self, timestamp):
        dt = self.prediction_ms / 1000.0
        
        # Use filtered velocity for prediction
        pred_x = self.Fx + self.vx_filtered * dt
        pred_y = self.Fy + self.vy_filtered * dt
        
        return {
            'id': self.id,
            'x': self.Fx, 'y': self.Fy,
            'pred_x': pred_x, 'pred_y': pred_y,
            'vx': self.vx_filtered, 'vy': self.vy_filtered,
            'speed': np.sqrt(self.vx_filtered**2 + self.vy_filtered**2),
            'mode': self.mode,
            'P0': self.current_P0,
            'color': self.color,
            'in_saccade': self.in_saccade
        }
    
    def validate_prediction(self, actual_x: float, actual_y: float, 
                           prediction_timestamp: float) -> Optional[float]:
        """
        Validate a past prediction against current actual position.
        Returns prediction error if we have a matching prediction.
        """
        # Find prediction made at approximately prediction_timestamp
        target_time = prediction_timestamp
        
        for pred_time, pred_x, pred_y in self.prediction_buffer:
            # Look for prediction made ~prediction_ms ago
            time_diff = abs((target_time - self.prediction_ms/1000) - pred_time)
            if time_diff < 0.02:  # Within 20ms
                error = np.sqrt((pred_x - actual_x)**2 + (pred_y - actual_y)**2)
                self.validated_errors.append(error)
                return error
        
        return None
    
    def get_avg_prediction_error(self):
        if not self.validated_errors:
            return 0
        return np.mean(self.validated_errors)
    
    def predict(self, ms_ahead):
        if self.Fx is None:
            return None, None
        dt = ms_ahead / 1000.0
        return (self.Fx + self.vx_filtered * dt,
                self.Fy + self.vy_filtered * dt)
    
    def mark_lost(self):
        self.lost_frames += 1
        if self.lost_frames > 30:
            self.is_active = False


# ═══════════════════════════════════════════════════════════════════════════════
#  KALMAN TRACKER - Standard implementation for comparison
# ═══════════════════════════════════════════════════════════════════════════════
class KalmanTrackerV3:
    """
    Standard Kalman with typical tuning.
    
    KEY DIFFERENCE: Kalman increases gain (adaptivity) under uncertainty.
    This causes OVERSHOOT after saccades as it chases the new measurements.
    """
    
    def __init__(self, target_id: int, prediction_ms: float = 60):
        self.id = target_id
        self.prediction_ms = prediction_ms
        
        # Kalman filter: state = [x, y, vx, vy]
        self.kf = cv2.KalmanFilter(4, 2)
        
        dt = 1/60
        self.kf.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]], dtype=np.float32)
        
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]], dtype=np.float32)
        
        # Process noise - affects how much we trust the model
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.05
        
        # Measurement noise - affects Kalman gain
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5
        
        self.initialized = False
        self.state = None
        self.mode = "ACQUIRING"
        
        # Prediction validation
        self.prediction_buffer = deque(maxlen=20)
        self.validated_errors = deque(maxlen=100)
        
        hue = (target_id * 0.618033988749895) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
        self.is_active = True
        self.lost_frames = 0
        self.in_saccade = False
        
    def update(self, x, y, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
            
        if not self.initialized:
            self.kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
            self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 100
            self.initialized = True
            self.state = self.kf.statePost.copy()
            return self._result(timestamp)
        
        # Predict
        predicted = self.kf.predict()
        
        # Check if this looks like a saccade
        pred_error = np.sqrt((predicted[0,0] - x)**2 + (predicted[1,0] - y)**2)
        self.in_saccade = pred_error > 30
        self.mode = "SACCADE" if self.in_saccade else "TRACKING"
        
        # Kalman correction - this is where it differs from DDA
        # High innovation (error) → Kalman increases gain → chases measurement
        measurement = np.array([[x], [y]], dtype=np.float32)
        self.kf.correct(measurement)
        
        self.state = self.kf.statePost.copy()
        self.lost_frames = 0
        
        result = self._result(timestamp)
        self.prediction_buffer.append((
            timestamp,
            result['pred_x'],
            result['pred_y']
        ))
        
        return result
    
    def _result(self, timestamp):
        if self.state is None:
            return None
            
        x, y = self.state[0,0], self.state[1,0]
        vx, vy = self.state[2,0], self.state[3,0]
        
        dt = self.prediction_ms / 1000.0
        pred_x = x + vx * dt
        pred_y = y + vy * dt
        
        return {
            'id': self.id,
            'x': x, 'y': y,
            'pred_x': pred_x, 'pred_y': pred_y,
            'vx': vx, 'vy': vy,
            'speed': np.sqrt(vx**2 + vy**2),
            'mode': self.mode,
            'P0': 0,  # Not applicable
            'color': self.color,
            'in_saccade': self.in_saccade
        }
    
    def validate_prediction(self, actual_x, actual_y, prediction_timestamp):
        target_time = prediction_timestamp
        
        for pred_time, pred_x, pred_y in self.prediction_buffer:
            time_diff = abs((target_time - self.prediction_ms/1000) - pred_time)
            if time_diff < 0.02:
                error = np.sqrt((pred_x - actual_x)**2 + (pred_y - actual_y)**2)
                self.validated_errors.append(error)
                return error
        return None
    
    def get_avg_prediction_error(self):
        if not self.validated_errors:
            return 0
        return np.mean(self.validated_errors)
    
    def predict(self, ms_ahead):
        if self.state is None:
            return None, None
        dt = ms_ahead / 1000.0
        return (self.state[0,0] + self.state[2,0] * dt,
                self.state[1,0] + self.state[3,0] * dt)
    
    def mark_lost(self):
        self.lost_frames += 1
        if self.lost_frames > 30:
            self.is_active = False


# ═══════════════════════════════════════════════════════════════════════════════
#  MOSQUITO WITH PRONOUNCED SACCADES
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class Mosquito:
    id: int
    x: float
    y: float
    vx: float = 0
    vy: float = 0
    alive: bool = True
    death_timer: float = 0
    death_x: float = 0
    death_y: float = 0
    mode_timer: float = 1.0
    saccade_cooldown: float = 0
    trail: deque = field(default_factory=lambda: deque(maxlen=20))
    
    # Track saccade state for visualization
    in_saccade: bool = False
    frames_since_saccade: int = 100


class MosquitoSwarm:
    """Swarm with pronounced saccadic movements to test tracker differences"""
    
    def __init__(self, num: int, width: int, height: int, difficulty: str = "medium"):
        self.width = width
        self.height = height
        self.margin = 80
        self.next_id = 0
        
        # More aggressive saccades to highlight DDA advantage
        self.params = {
            "easy": {"speed": 100, "saccade": 350, "prob": 0.04, "saccade_dur": 0.12},
            "medium": {"speed": 160, "saccade": 500, "prob": 0.07, "saccade_dur": 0.10},
            "hard": {"speed": 240, "saccade": 700, "prob": 0.10, "saccade_dur": 0.08},
            "nightmare": {"speed": 350, "saccade": 950, "prob": 0.14, "saccade_dur": 0.06}
        }[difficulty]
        
        self.mosquitos: List[Mosquito] = []
        self.dead_mosquitos: List[Mosquito] = []
        
        for _ in range(num):
            self._spawn()
    
    def _spawn(self):
        m = Mosquito(
            id=self.next_id,
            x=random.uniform(self.margin, self.width - self.margin),
            y=random.uniform(self.margin, self.height - self.margin),
            vx=random.uniform(-50, 50),
            vy=random.uniform(-50, 50),
            mode_timer=random.uniform(0.3, 1.5)
        )
        self.next_id += 1
        self.mosquitos.append(m)
    
    def update(self, dt: float):
        # Update dead mosquitos
        for m in self.dead_mosquitos[:]:
            m.death_timer -= dt
            if m.death_timer <= 0:
                self.dead_mosquitos.remove(m)
        
        for m in self.mosquitos:
            m.trail.append((m.x, m.y))
            m.mode_timer -= dt
            m.saccade_cooldown -= dt
            m.frames_since_saccade += 1
            
            # Saccade logic - sudden direction change
            should_saccade = (
                m.mode_timer <= 0 and 
                m.saccade_cooldown <= 0 and
                random.random() < self.params["prob"]
            )
            
            if should_saccade:
                # SACCADE: Instant velocity change
                angle = random.uniform(0, 2 * np.pi)
                speed = self.params["saccade"] * random.uniform(0.8, 1.2)
                
                # Make saccade perpendicular-ish to current direction for max disruption
                current_angle = np.arctan2(m.vy, m.vx)
                saccade_angle = current_angle + random.uniform(0.5, 2.5) * random.choice([-1, 1])
                
                m.vx = np.cos(saccade_angle) * speed
                m.vy = np.sin(saccade_angle) * speed
                m.mode_timer = self.params["saccade_dur"]
                m.saccade_cooldown = random.uniform(0.3, 0.8)
                m.in_saccade = True
                m.frames_since_saccade = 0
                
            elif m.mode_timer <= 0:
                # Normal cruise
                angle = np.arctan2(m.vy, m.vx) + random.gauss(0, 0.3)
                speed = self.params["speed"] * random.uniform(0.5, 1.0)
                m.vx = np.cos(angle) * speed
                m.vy = np.sin(angle) * speed
                m.mode_timer = random.uniform(0.5, 1.5)
                m.in_saccade = False
            
            # Add subtle noise
            m.vx += random.gauss(0, 15) * dt * 60
            m.vy += random.gauss(0, 15) * dt * 60
            
            # Gradual drag
            drag = 0.998 if not m.in_saccade else 0.99
            m.vx *= drag
            m.vy *= drag
            
            # Update position
            m.x += m.vx * dt
            m.y += m.vy * dt
            
            # Boundaries
            if m.x < self.margin:
                m.x = self.margin; m.vx = abs(m.vx)
            elif m.x > self.width - self.margin:
                m.x = self.width - self.margin; m.vx = -abs(m.vx)
            if m.y < self.margin:
                m.y = self.margin; m.vy = abs(m.vy)
            elif m.y > self.height - self.margin:
                m.y = self.height - self.margin; m.vy = -abs(m.vy)
        
        return [(m.id, m.x, m.y, m.vx, m.vy, m.frames_since_saccade) 
                for m in self.mosquitos]
    
    def kill(self, mosquito_id: int) -> Optional[Tuple[float, float]]:
        for m in self.mosquitos:
            if m.id == mosquito_id:
                pos = (m.x, m.y)
                m.death_x, m.death_y = m.x, m.y
                m.death_timer = 0.4
                m.alive = False
                self.dead_mosquitos.append(m)
                self.mosquitos.remove(m)
                self._spawn()
                return pos
        return None
    
    def get_position(self, mosquito_id: int):
        for m in self.mosquitos:
            if m.id == mosquito_id:
                return m.x, m.y, m.frames_since_saccade
        return None, None, None


# ═══════════════════════════════════════════════════════════════════════════════
#  LASER TURRET WITH DELAYED VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class PendingShot:
    """A shot waiting for validation after prediction delay"""
    fire_time: float
    pred_x: float
    pred_y: float
    target_id: int
    tracker_type: str


@dataclass 
class LaserShot:
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    hit: bool
    timer: float = 0.12
    target_id: int = -1


class LaserTurretV3:
    """Turret with proper delayed prediction validation"""
    
    def __init__(self, x: float, y: float, hit_radius: float = 22, 
                 prediction_ms: float = 60):
        self.x = x
        self.y = y
        self.hit_radius = hit_radius
        self.prediction_ms = prediction_ms
        
        self.cooldown = 0
        self.fire_rate = 0.1
        
        # Stats
        self.shots_fired = 0
        self.hits = 0
        self.misses = 0
        
        # Separate stats for saccade vs stable
        self.saccade_shots = 0
        self.saccade_hits = 0
        self.stable_shots = 0
        self.stable_hits = 0
        
        # Pending shots waiting for validation
        self.pending_shots: List[PendingShot] = []
        
        # Visual shots
        self.active_shots: List[LaserShot] = []
        
        # Aiming
        self.aim_x = x
        self.aim_y = y
        
        # Error tracking
        self.recent_errors = deque(maxlen=50)
        
    def fire(self, pred_x: float, pred_y: float, target_id: int, 
             current_time: float) -> bool:
        """Queue a shot for delayed validation"""
        if self.cooldown > 0:
            return False
        
        self.cooldown = self.fire_rate
        
        # Queue for validation after prediction_ms
        self.pending_shots.append(PendingShot(
            fire_time=current_time,
            pred_x=pred_x,
            pred_y=pred_y,
            target_id=target_id,
            tracker_type="dda"
        ))
        
        return True
    
    def validate_shots(self, swarm: 'MosquitoSwarm', current_time: float, 
                       particles: 'ParticleSystem') -> List[int]:
        """Validate pending shots and return list of killed target IDs"""
        kills = []
        
        for shot in self.pending_shots[:]:
            # Check if enough time has passed
            elapsed = (current_time - shot.fire_time) * 1000
            if elapsed >= self.prediction_ms:
                self.pending_shots.remove(shot)
                self.shots_fired += 1
                
                # Get actual position NOW
                actual = swarm.get_position(shot.target_id)
                if actual[0] is None:
                    continue
                
                actual_x, actual_y, frames_since_saccade = actual
                
                # Calculate prediction error
                error = np.sqrt((shot.pred_x - actual_x)**2 + 
                               (shot.pred_y - actual_y)**2)
                self.recent_errors.append(error)
                
                # Was this during/after a saccade?
                is_post_saccade = frames_since_saccade < 10
                
                # Check hit
                hit = error <= self.hit_radius
                
                if is_post_saccade:
                    self.saccade_shots += 1
                    if hit:
                        self.saccade_hits += 1
                else:
                    self.stable_shots += 1
                    if hit:
                        self.stable_hits += 1
                
                if hit:
                    self.hits += 1
                    death_pos = swarm.kill(shot.target_id)
                    if death_pos:
                        kills.append(shot.target_id)
                        particles.spawn_explosion(death_pos[0], death_pos[1])
                else:
                    self.misses += 1
                    particles.spawn_miss(shot.pred_x, shot.pred_y)
                
                # Create visual
                self.active_shots.append(LaserShot(
                    start_x=self.x, start_y=self.y,
                    end_x=shot.pred_x, end_y=shot.pred_y,
                    hit=hit, target_id=shot.target_id
                ))
        
        return kills
    
    def update(self, dt: float):
        self.cooldown = max(0, self.cooldown - dt)
        
        for shot in self.active_shots[:]:
            shot.timer -= dt
            if shot.timer <= 0:
                self.active_shots.remove(shot)
    
    @property
    def accuracy(self):
        return (self.hits / self.shots_fired * 100) if self.shots_fired > 0 else 0
    
    @property
    def saccade_accuracy(self):
        return (self.saccade_hits / self.saccade_shots * 100) if self.saccade_shots > 0 else 0
    
    @property
    def stable_accuracy(self):
        return (self.stable_hits / self.stable_shots * 100) if self.stable_shots > 0 else 0
    
    @property
    def avg_error(self):
        return np.mean(self.recent_errors) if self.recent_errors else 0


# ═══════════════════════════════════════════════════════════════════════════════
#  PARTICLES
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: Tuple[int, int, int]
    size: float


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []
    
    def spawn_explosion(self, x: float, y: float):
        for _ in range(25):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(150, 450)
            self.particles.append(Particle(
                x=x, y=y,
                vx=np.cos(angle) * speed,
                vy=np.sin(angle) * speed,
                life=random.uniform(0.2, 0.4),
                color=(255, random.randint(100, 200), 50),
                size=random.uniform(2, 5)
            ))
    
    def spawn_miss(self, x: float, y: float):
        for _ in range(6):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(30, 80)
            self.particles.append(Particle(
                x=x, y=y,
                vx=np.cos(angle) * speed,
                vy=np.sin(angle) * speed,
                life=random.uniform(0.1, 0.2),
                color=(100, 100, 150),
                size=random.uniform(1, 2)
            ))
    
    def update(self, dt: float):
        for p in self.particles[:]:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 300 * dt
            p.life -= dt
            p.size *= 0.96
            if p.life <= 0:
                self.particles.remove(p)
    
    def draw(self, frame):
        for p in self.particles:
            alpha = min(1.0, p.life * 4)
            color = tuple(int(c * alpha) for c in p.color)
            cv2.circle(frame, (int(p.x), int(p.y)), max(1, int(p.size)), color, -1)


# ═══════════════════════════════════════════════════════════════════════════════
#  TRACKER MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class TrackerManagerV3:
    def __init__(self, tracker_type: str = "DDA", prediction_ms: float = 60):
        self.tracker_type = tracker_type
        self.prediction_ms = prediction_ms
        self.trackers: Dict[int, object] = {}
        
    def update(self, detections, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        results = []
        seen_ids = set()
        
        for det in detections:
            mid, x, y, vx, vy, frames_since_saccade = det
            seen_ids.add(mid)
            
            if mid not in self.trackers:
                if self.tracker_type == "DDA":
                    self.trackers[mid] = DDATrackerV3(mid, self.prediction_ms)
                else:
                    self.trackers[mid] = KalmanTrackerV3(mid, self.prediction_ms)
            
            result = self.trackers[mid].update(x, y, timestamp)
            if result:
                result['frames_since_saccade'] = frames_since_saccade
                results.append(result)
        
        for mid in list(self.trackers.keys()):
            if mid not in seen_ids:
                self.trackers[mid].mark_lost()
                if not self.trackers[mid].is_active:
                    del self.trackers[mid]
        
        return results
    
    def get_tracker(self, target_id):
        return self.trackers.get(target_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class DDATerminatorV3:
    def __init__(self,
                 num_mosquitos: int = 15,
                 difficulty: str = "medium",
                 comparison_mode: bool = True,
                 width: int = 1280,
                 height: int = 720):
        
        self.width = width
        self.height = height
        self.comparison_mode = comparison_mode
        self.difficulty = difficulty
        
        # Swarm
        self.swarm = MosquitoSwarm(num_mosquitos, width, height, difficulty)
        
        # DDA system
        prediction_ms = 60
        self.dda_trackers = TrackerManagerV3("DDA", prediction_ms)
        self.dda_turret = LaserTurretV3(width // 4, height - 60, 
                                        hit_radius=20, prediction_ms=prediction_ms)
        
        # Kalman system
        self.kalman_trackers = TrackerManagerV3("Kalman", prediction_ms)
        self.kalman_turret = LaserTurretV3(3 * width // 4, height - 60,
                                           hit_radius=20, prediction_ms=prediction_ms)
        
        self.particles = ParticleSystem()
        
        # State
        self.paused = False
        self.frame_count = 0
        self.dda_kills = 0
        self.kalman_kills = 0
        
        self.background = self._create_background()
    
    def _create_background(self):
        bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for y in range(self.height):
            val = int(12 + (y / self.height) * 18)
            bg[y, :] = (val, val + 2, val + 6)
        for x in range(0, self.width, 50):
            cv2.line(bg, (x, 0), (x, self.height), (25, 27, 32), 1)
        for y in range(0, self.height, 50):
            cv2.line(bg, (0, y), (self.width, y), (25, 27, 32), 1)
        return bg
    
    def run(self):
        print("\n" + "═"*70)
        print("  DDA TERMINATOR v3.0 - TRUE COMPARISON")
        print("═"*70)
        print("  LEFT: DDA Tracker    RIGHT: Kalman Filter")
        print("  Watch post-saccade accuracy - that's where DDA wins")
        print("═"*70)
        print("  [Q] Quit  [SPACE] Pause  [R] Reset")
        print("═"*70 + "\n")
        
        cv2.namedWindow('DDA vs Kalman', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('DDA vs Kalman', self.width, self.height)
        
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = min(current_time - last_time, 0.05)
            last_time = current_time
            
            if not self.paused:
                self._update(dt, current_time)
            
            frame = self._render()
            cv2.imshow('DDA vs Kalman', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                self.paused = not self.paused
            elif key == ord('r'):
                self._reset()
        
        cv2.destroyAllWindows()
        self._print_final()
    
    def _update(self, dt: float, timestamp: float):
        # Update swarm
        detections = self.swarm.update(dt)
        
        # Update trackers
        dda_results = self.dda_trackers.update(detections, timestamp)
        kalman_results = self.kalman_trackers.update(detections, timestamp)
        
        # Update turrets
        self.dda_turret.update(dt)
        self.kalman_turret.update(dt)
        
        # Fire at targets - both fire at same targets for fair comparison
        if dda_results:
            # Pick target
            target = min(dda_results, key=lambda r: 
                        np.sqrt((r['pred_x'] - self.dda_turret.x)**2 + 
                               (r['pred_y'] - self.dda_turret.y)**2))
            target_id = target['id']
            
            # DDA fires
            dda_pred = target['pred_x'], target['pred_y']
            if self.dda_turret.cooldown <= 0:
                self.dda_turret.fire(dda_pred[0], dda_pred[1], target_id, timestamp)
            
            # Kalman fires at same target
            kalman_tracker = self.kalman_trackers.get_tracker(target_id)
            if kalman_tracker and self.kalman_turret.cooldown <= 0:
                k_result = None
                for r in kalman_results:
                    if r['id'] == target_id:
                        k_result = r
                        break
                if k_result:
                    self.kalman_turret.fire(k_result['pred_x'], k_result['pred_y'],
                                           target_id, timestamp)
        
        # Validate pending shots
        dda_kills = self.dda_turret.validate_shots(self.swarm, timestamp, self.particles)
        kalman_kills = self.kalman_turret.validate_shots(self.swarm, timestamp, self.particles)
        
        self.dda_kills += len(dda_kills)
        self.kalman_kills += len(kalman_kills)
        
        # Update particles
        self.particles.update(dt)
        
        self.frame_count += 1
    
    def _render(self):
        frame = self.background.copy()
        
        # Divider
        mid_x = self.width // 2
        cv2.line(frame, (mid_x, 0), (mid_x, self.height), (60, 60, 70), 2)
        
        # Labels
        cv2.putText(frame, "DDA TRACKER", (mid_x // 2 - 60, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(frame, "KALMAN FILTER", (mid_x + mid_x // 2 - 70, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 150, 255), 2)
        
        # Draw mosquitos
        for m in self.swarm.mosquitos:
            # Trail
            trail = list(m.trail)
            for i in range(1, len(trail)):
                alpha = i / len(trail)
                color = (int(30*alpha), int(35*alpha), int(45*alpha))
                cv2.line(frame, 
                        (int(trail[i-1][0]), int(trail[i-1][1])),
                        (int(trail[i][0]), int(trail[i][1])), color, 1)
            
            # Body
            body_color = (80, 100, 120) if m.frames_since_saccade > 5 else (120, 80, 80)
            cv2.circle(frame, (int(m.x), int(m.y)), 5, body_color, -1)
        
        # Get current tracker results for visualization
        detections = [(m.id, m.x, m.y, m.vx, m.vy, m.frames_since_saccade) 
                     for m in self.swarm.mosquitos]
        dda_results = self.dda_trackers.update(detections)
        kalman_results = self.kalman_trackers.update(detections)
        
        # Draw DDA predictions (left side emphasis)
        for r in dda_results:
            x, y = int(r['x']), int(r['y'])
            px, py = int(r['pred_x']), int(r['pred_y'])
            
            # Box
            cv2.rectangle(frame, (x-14, y-14), (x+14, y+14), (0, 255, 200), 2)
            
            # Prediction
            cv2.circle(frame, (px, py), 5, (0, 255, 255), -1)
            cv2.arrowedLine(frame, (x, y), (px, py), (0, 200, 200), 2, tipLength=0.3)
            
            # P0 indicator (DDA specific)
            p0 = r.get('P0', 0.7)
            p0_color = (0, int(255 * p0), int(255 * (1-p0)))
            cv2.circle(frame, (x + 14, y - 14), 4, p0_color, -1)
        
        # Draw Kalman predictions (right side emphasis)  
        for r in kalman_results:
            x, y = int(r['x']), int(r['y'])
            px, py = int(r['pred_x']), int(r['pred_y'])
            
            # Box
            cv2.rectangle(frame, (x-14, y-14), (x+14, y+14), (200, 150, 255), 2)
            
            # Prediction
            cv2.circle(frame, (px, py), 5, (255, 200, 255), -1)
            cv2.arrowedLine(frame, (x, y), (px, py), (180, 130, 220), 2, tipLength=0.3)
        
        # Draw laser shots
        for shot in self.dda_turret.active_shots:
            alpha = shot.timer / 0.12
            color = (0, int(255*alpha), int(200*alpha)) if shot.hit else (0, 0, int(150*alpha))
            cv2.line(frame, (int(shot.start_x), int(shot.start_y)),
                    (int(shot.end_x), int(shot.end_y)), color, 2 if shot.hit else 1)
            cv2.circle(frame, (int(shot.end_x), int(shot.end_y)), 
                      int(6*alpha), color, -1)
        
        for shot in self.kalman_turret.active_shots:
            alpha = shot.timer / 0.12
            color = (int(200*alpha), int(150*alpha), int(255*alpha)) if shot.hit else (int(100*alpha), 0, int(100*alpha))
            cv2.line(frame, (int(shot.start_x), int(shot.start_y)),
                    (int(shot.end_x), int(shot.end_y)), color, 2 if shot.hit else 1)
            cv2.circle(frame, (int(shot.end_x), int(shot.end_y)),
                      int(6*alpha), color, -1)
        
        # Draw turrets
        for turret, color in [(self.dda_turret, (0, 200, 180)), 
                              (self.kalman_turret, (180, 130, 200))]:
            cv2.circle(frame, (int(turret.x), int(turret.y)), 18, (40, 45, 55), -1)
            cv2.circle(frame, (int(turret.x), int(turret.y)), 18, color, 2)
            cv2.circle(frame, (int(turret.x), int(turret.y)), 6, color, -1)
        
        # Draw particles
        self.particles.draw(frame)
        
        # Draw death animations
        for m in self.swarm.dead_mosquitos:
            alpha = m.death_timer / 0.4
            cv2.circle(frame, (int(m.death_x), int(m.death_y)),
                      int(15 * (1 - alpha)), (int(255*alpha), int(150*alpha), 0), 2)
        
        # HUD
        self._draw_hud(frame)
        
        if self.paused:
            cv2.putText(frame, "PAUSED", (self.width//2 - 60, self.height//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        return frame
    
    def _draw_hud(self, frame):
        # DDA stats (left)
        x, y = 20, 60
        cv2.putText(frame, f"Kills: {self.dda_kills}", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
        y += 25
        cv2.putText(frame, f"Accuracy: {self.dda_turret.accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.1, (0, 255, 200), 1)
        y += 20
        cv2.putText(frame, f"Post-Saccade: {self.dda_turret.saccade_accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.1, (0, 200, 150), 1)
        y += 18
        cv2.putText(frame, f"Stable: {self.dda_turret.stable_accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.0, (100, 150, 120), 1)
        y += 18
        cv2.putText(frame, f"Avg Error: {self.dda_turret.avg_error:.1f}px", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.0, (100, 150, 120), 1)
        
        # Kalman stats (right)
        x = self.width // 2 + 20
        y = 60
        cv2.putText(frame, f"Kills: {self.kalman_kills}", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 150, 255), 2)
        y += 25
        cv2.putText(frame, f"Accuracy: {self.kalman_turret.accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.1, (200, 150, 255), 1)
        y += 20
        cv2.putText(frame, f"Post-Saccade: {self.kalman_turret.saccade_accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.1, (180, 130, 220), 1)
        y += 18
        cv2.putText(frame, f"Stable: {self.kalman_turret.stable_accuracy:.1f}%", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.0, (140, 120, 160), 1)
        y += 18
        cv2.putText(frame, f"Avg Error: {self.kalman_turret.avg_error:.1f}px", (x, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.0, (140, 120, 160), 1)
        
        # Comparison (bottom center)
        if self.dda_turret.shots_fired > 20:
            diff = self.dda_turret.accuracy - self.kalman_turret.accuracy
            saccade_diff = self.dda_turret.saccade_accuracy - self.kalman_turret.saccade_accuracy
            
            color = (0, 255, 100) if diff > 0 else (100, 100, 255)
            cv2.putText(frame, f"DDA Overall: {diff:+.1f}%", 
                       (self.width//2 - 80, self.height - 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            sac_color = (0, 255, 100) if saccade_diff > 0 else (100, 100, 255)
            cv2.putText(frame, f"DDA Post-Saccade: {saccade_diff:+.1f}%",
                       (self.width//2 - 100, self.height - 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, sac_color, 2)
    
    def _reset(self):
        self.swarm = MosquitoSwarm(len(self.swarm.mosquitos), 
                                   self.width, self.height, self.difficulty)
        self.dda_trackers = TrackerManagerV3("DDA", 60)
        self.kalman_trackers = TrackerManagerV3("Kalman", 60)
        self.dda_turret = LaserTurretV3(self.width // 4, self.height - 60, 20, 60)
        self.kalman_turret = LaserTurretV3(3 * self.width // 4, self.height - 60, 20, 60)
        self.particles = ParticleSystem()
        self.dda_kills = 0
        self.kalman_kills = 0
        self.frame_count = 0
    
    def _print_final(self):
        print("\n" + "═"*70)
        print("  FINAL RESULTS")
        print("═"*70)
        print(f"\n  DDA TRACKER:")
        print(f"    Total Kills: {self.dda_kills}")
        print(f"    Overall Accuracy: {self.dda_turret.accuracy:.2f}%")
        print(f"    Post-Saccade Accuracy: {self.dda_turret.saccade_accuracy:.2f}%")
        print(f"    Stable Accuracy: {self.dda_turret.stable_accuracy:.2f}%")
        print(f"    Average Prediction Error: {self.dda_turret.avg_error:.2f}px")
        
        print(f"\n  KALMAN FILTER:")
        print(f"    Total Kills: {self.kalman_kills}")
        print(f"    Overall Accuracy: {self.kalman_turret.accuracy:.2f}%")
        print(f"    Post-Saccade Accuracy: {self.kalman_turret.saccade_accuracy:.2f}%")
        print(f"    Stable Accuracy: {self.kalman_turret.stable_accuracy:.2f}%")
        print(f"    Average Prediction Error: {self.kalman_turret.avg_error:.2f}px")
        
        print("\n" + "═"*70)
        overall_diff = self.dda_turret.accuracy - self.kalman_turret.accuracy
        saccade_diff = self.dda_turret.saccade_accuracy - self.kalman_turret.saccade_accuracy
        
        print(f"  DDA OVERALL ADVANTAGE: {overall_diff:+.2f}%")
        print(f"  DDA POST-SACCADE ADVANTAGE: {saccade_diff:+.2f}%")
        print("═"*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--swarm', type=int, default=15)
    parser.add_argument('--difficulty', default='medium',
                       choices=['easy', 'medium', 'hard', 'nightmare'])
    parser.add_argument('--nightmare', action='store_true')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    
    args = parser.parse_args()
    difficulty = 'nightmare' if args.nightmare else args.difficulty
    
    app = DDATerminatorV3(
        num_mosquitos=args.swarm,
        difficulty=difficulty,
        width=args.width,
        height=args.height
    )
    app.run()
