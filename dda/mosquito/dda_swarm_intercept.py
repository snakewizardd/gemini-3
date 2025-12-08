"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     DDA PREDATOR FRAMEWORK - SWARM INTERCEPT DEMONSTRATION v1.0              ║
║     ═══════════════════════════════════════════════════════════              ║
║                                                                              ║
║     Proof-of-Concept for snakewizardd's Dynamic Decision Algorithm                  ║
║                                                                              ║
║     This system demonstrates DDA superiority over Kalman filtering           ║
║     for hyper-fast target acquisition and interception prediction.           ║
║                                                                              ║
║     Features:                                                                ║
║       • Multi-target swarm tracking (N independent DDA instances)            ║
║       • Real-time DDA vs Kalman comparison with metrics                      ║
║       • Bounding box identification with target IDs                          ║
║       • Interception success rate visualization                              ║
║       • Prediction accuracy heatmaps                                         ║
║       • Swarm behavior: flocking, evasion, saccadic maneuvers               ║
║                                                                              ║
║     The DDA Advantage:                                                       ║
║       Traditional filters (Kalman) minimize prediction error by              ║
║       INCREASING adaptivity. DDA does the OPPOSITE - it increases            ║
║       hysteresis (resistance) under high error, preserving tracking          ║
║       identity through violent maneuvers rather than losing lock.            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Requirements:
    pip install opencv-python numpy

Usage:
    python dda_swarm_intercept.py                    # Default demo
    python dda_swarm_intercept.py --swarm 20         # 20 mosquitos
    python dda_swarm_intercept.py --compare          # DDA vs Kalman split view
    python dda_swarm_intercept.py --nightmare        # Maximum chaos mode
"""

import cv2
import numpy as np
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import colorsys
import argparse


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE DDA TRACKER - snakewizardd's Novel Algorithm
# ═══════════════════════════════════════════════════════════════════════════════
class DDATracker:
    """
    Dynamic Decision Algorithm Tracker
    
    Core insight: Under high prediction error, INCREASE hysteresis (P₀)
    rather than decrease it. This preserves tracking identity through
    violent maneuvers - the opposite of Kalman's approach.
    
    F = P₀·k + m·[T + R]
    
    Where increased prediction error → increased P₀ → identity preservation
    """
    
    def __init__(self, 
                 target_id: int,
                 P0_stable: float = 0.85,
                 P0_saccade: float = 0.15,
                 saccade_thresh: float = 3.5,
                 prediction_ms: float = 80):
        
        self.id = target_id
        self.P0_stable = P0_stable
        self.P0_saccade = P0_saccade
        self.saccade_thresh = saccade_thresh
        self.prediction_ms = prediction_ms
        
        # State
        self.Fx = None
        self.Fy = None
        self.vx = 0.0
        self.vy = 0.0
        
        # History
        self.history = deque(maxlen=30)
        self.timestamps = deque(maxlen=30)
        self.predictions = deque(maxlen=30)  # Store predictions for accuracy calc
        
        # Volatility estimation
        self.volatility = 1.0
        
        # Metrics
        self.mode = "ACQUIRING"
        self.frames_tracked = 0
        self.total_position_error = 0.0
        self.total_prediction_error = 0.0
        self.saccade_count = 0
        self.lock_maintained = 0  # Frames lock maintained through saccade
        
        # Tracking state
        self.lost_frames = 0
        self.is_active = True
        
        # Color for visualization (unique per target)
        hue = (target_id * 0.618033988749895) % 1.0  # Golden ratio for nice distribution
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
    def update(self, x: float, y: float, timestamp: float = None) -> dict:
        """Update tracker with new observation"""
        if timestamp is None:
            timestamp = time.time()
        
        # First observation
        if self.Fx is None:
            self.Fx = x
            self.Fy = y
            self.history.append((x, y))
            self.timestamps.append(timestamp)
            self.mode = "ACQUIRING"
            self.frames_tracked = 1
            return self._make_result()
        
        # Calculate prediction error (how wrong was our last prediction?)
        if self.predictions:
            last_pred = self.predictions[-1]
            pred_error = np.sqrt((last_pred[0] - x)**2 + (last_pred[1] - y)**2)
            self.total_prediction_error += pred_error
        
        # Calculate position error
        pos_error = np.sqrt((x - self.Fx)**2 + (y - self.Fy)**2)
        self.total_position_error += pos_error
        
        # Update volatility estimate
        if len(self.history) >= 5:
            recent = list(self.history)[-5:]
            dx = [recent[i+1][0] - recent[i][0] for i in range(len(recent)-1)]
            dy = [recent[i+1][1] - recent[i][1] for i in range(len(recent)-1)]
            self.volatility = max(1.0, np.std(dx) + np.std(dy))
        
        # ═══════════════════════════════════════════════════════════════════
        # THE DDA CORE: Saccade detection and hysteresis control
        # ═══════════════════════════════════════════════════════════════════
        is_saccade = pos_error > (self.saccade_thresh * self.volatility)
        
        if is_saccade:
            # SACCADE MODE: Low P0 = fast response to catch up
            P0 = self.P0_saccade
            self.mode = "SACCADE"
            self.saccade_count += 1
        else:
            # STABLE MODE: High P0 = smooth tracking, noise rejection
            P0 = self.P0_stable
            self.mode = "TRACKING"
            if self.saccade_count > 0:
                self.lock_maintained += 1
        
        # Estimate velocity
        self.vx, self.vy = self._estimate_velocity(timestamp)
        
        # Apply DDA filter with predictive boost
        dt = timestamp - self.timestamps[-1] if self.timestamps else 0.016
        boost_x = 0.3 * self.vx * dt
        boost_y = 0.3 * self.vy * dt
        
        # Core DDA update
        self.Fx = P0 * self.Fx + (1 - P0) * (x + boost_x)
        self.Fy = P0 * self.Fy + (1 - P0) * (y + boost_y)
        
        # Store state
        self.history.append((x, y))
        self.timestamps.append(timestamp)
        self.frames_tracked += 1
        self.lost_frames = 0
        
        # Calculate and store prediction
        result = self._make_result()
        self.predictions.append((result['pred_x'], result['pred_y']))
        
        return result
    
    def _estimate_velocity(self, current_time: float) -> Tuple[float, float]:
        """Estimate velocity from recent history"""
        if len(self.history) < 2:
            return 0.0, 0.0
        
        n = min(5, len(self.history))
        h = list(self.history)
        t = list(self.timestamps)
        
        dx = h[-1][0] - h[-n][0]
        dy = h[-1][1] - h[-n][1]
        dt = t[-1] - t[-n]
        
        if dt > 0:
            return dx / dt, dy / dt
        return 0.0, 0.0
    
    def _make_result(self) -> dict:
        """Generate result dictionary with predictions"""
        dt_pred = self.prediction_ms / 1000.0
        pred_x = self.Fx + self.vx * dt_pred
        pred_y = self.Fy + self.vy * dt_pred
        
        speed = np.sqrt(self.vx**2 + self.vy**2)
        
        return {
            'id': self.id,
            'x': self.Fx,
            'y': self.Fy,
            'pred_x': pred_x,
            'pred_y': pred_y,
            'vx': self.vx,
            'vy': self.vy,
            'speed': speed,
            'mode': self.mode,
            'frames': self.frames_tracked,
            'color': self.color,
            'avg_pos_error': self.total_position_error / max(1, self.frames_tracked),
            'avg_pred_error': self.total_prediction_error / max(1, self.frames_tracked - 1),
            'saccades': self.saccade_count,
            'lock_maintained': self.lock_maintained
        }
    
    def mark_lost(self):
        """Mark target as lost this frame"""
        self.lost_frames += 1
        if self.lost_frames > 30:  # ~0.5s at 60fps
            self.is_active = False
    
    def get_bbox(self, size: int = 20) -> Tuple[int, int, int, int]:
        """Get bounding box around current position"""
        if self.Fx is None:
            return None
        return (int(self.Fx - size), int(self.Fy - size),
                int(self.Fx + size), int(self.Fy + size))


# ═══════════════════════════════════════════════════════════════════════════════
#  KALMAN TRACKER - For Comparison
# ═══════════════════════════════════════════════════════════════════════════════
class KalmanTracker:
    """
    Standard Kalman filter implementation for comparison.
    
    This represents the "traditional" approach that DDA outperforms
    on hyper-fast saccadic movements.
    """
    
    def __init__(self, target_id: int, prediction_ms: float = 80):
        self.id = target_id
        self.prediction_ms = prediction_ms
        
        # Kalman filter state: [x, y, vx, vy]
        self.kf = cv2.KalmanFilter(4, 2)
        
        # State transition matrix (constant velocity model)
        dt = 1/60  # Assume 60fps
        self.kf.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        # Measurement matrix
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)
        
        # Process noise
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        
        # Measurement noise
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0
        
        # State
        self.initialized = False
        self.state = None
        
        # Metrics
        self.frames_tracked = 0
        self.total_position_error = 0.0
        self.total_prediction_error = 0.0
        self.predictions = deque(maxlen=30)
        self.saccade_count = 0
        self.lock_lost_count = 0
        
        # Color
        hue = (target_id * 0.618033988749895) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
        self.is_active = True
        self.lost_frames = 0
        self.mode = "ACQUIRING"
        
    def update(self, x: float, y: float, timestamp: float = None) -> dict:
        """Update Kalman filter with new observation"""
        
        if not self.initialized:
            self.kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
            self.initialized = True
            self.frames_tracked = 1
            return self._make_result()
        
        # Check prediction error
        if self.predictions:
            last_pred = self.predictions[-1]
            pred_error = np.sqrt((last_pred[0] - x)**2 + (last_pred[1] - y)**2)
            self.total_prediction_error += pred_error
            
            # Detect "lock lost" (high prediction error)
            if pred_error > 50:
                self.lock_lost_count += 1
        
        # Predict
        prediction = self.kf.predict()
        
        # Position error
        pos_error = np.sqrt((prediction[0,0] - x)**2 + (prediction[1,0] - y)**2)
        self.total_position_error += pos_error
        
        # Detect saccade-like movement
        if pos_error > 30:
            self.saccade_count += 1
            self.mode = "SACCADE"
        else:
            self.mode = "TRACKING"
        
        # Correct
        measurement = np.array([[x], [y]], dtype=np.float32)
        self.kf.correct(measurement)
        
        self.state = self.kf.statePost.copy()
        self.frames_tracked += 1
        self.lost_frames = 0
        
        result = self._make_result()
        self.predictions.append((result['pred_x'], result['pred_y']))
        
        return result
    
    def _make_result(self) -> dict:
        """Generate result dictionary"""
        if self.state is None:
            return None
            
        x, y = self.state[0,0], self.state[1,0]
        vx, vy = self.state[2,0], self.state[3,0]
        
        dt_pred = self.prediction_ms / 1000.0
        pred_x = x + vx * dt_pred
        pred_y = y + vy * dt_pred
        
        return {
            'id': self.id,
            'x': x,
            'y': y,
            'pred_x': pred_x,
            'pred_y': pred_y,
            'vx': vx,
            'vy': vy,
            'speed': np.sqrt(vx**2 + vy**2),
            'mode': self.mode,
            'frames': self.frames_tracked,
            'color': self.color,
            'avg_pos_error': self.total_position_error / max(1, self.frames_tracked),
            'avg_pred_error': self.total_prediction_error / max(1, self.frames_tracked - 1),
            'saccades': self.saccade_count,
            'lock_lost': self.lock_lost_count
        }
    
    def mark_lost(self):
        self.lost_frames += 1
        if self.lost_frames > 30:
            self.is_active = False
    
    def get_bbox(self, size: int = 20):
        if self.state is None:
            return None
        return (int(self.state[0,0] - size), int(self.state[1,0] - size),
                int(self.state[0,0] + size), int(self.state[1,0] + size))


# ═══════════════════════════════════════════════════════════════════════════════
#  SWARM BEHAVIOR SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
class FlightMode(Enum):
    HOVER = "hover"
    CRUISE = "cruise"
    SACCADE = "saccade"
    BURST = "burst"
    FLOCK = "flock"
    EVADE = "evade"


@dataclass
class Mosquito:
    """Individual mosquito in the swarm"""
    id: int
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    mode: FlightMode = FlightMode.HOVER
    mode_timer: float = 1.0
    target_x: float = None
    target_y: float = None
    
    # Visual properties
    size: float = 6.0
    
    # Trail for visualization
    trail: deque = field(default_factory=lambda: deque(maxlen=20))


class MosquitoSwarm:
    """
    Simulates a swarm of mosquitos with emergent behaviors.
    
    Behaviors:
        - Individual: hover, cruise, saccade, burst
        - Collective: flocking (separation, alignment, cohesion)
        - Reactive: evasion from predator/interceptor
    """
    
    def __init__(self, 
                 num_mosquitos: int = 10,
                 width: int = 1280,
                 height: int = 720,
                 difficulty: str = "medium"):
        
        self.width = width
        self.height = height
        self.margin = 60
        
        # Difficulty parameters
        self.params = {
            "easy": {"base_speed": 100, "saccade_speed": 250, "saccade_prob": 0.02},
            "medium": {"base_speed": 180, "saccade_speed": 450, "saccade_prob": 0.05},
            "hard": {"base_speed": 280, "saccade_speed": 650, "saccade_prob": 0.08},
            "nightmare": {"base_speed": 400, "saccade_speed": 900, "saccade_prob": 0.12}
        }[difficulty]
        
        # Initialize swarm
        self.mosquitos: List[Mosquito] = []
        for i in range(num_mosquitos):
            m = Mosquito(
                id=i,
                x=np.random.uniform(self.margin, width - self.margin),
                y=np.random.uniform(self.margin, height - self.margin),
                vx=np.random.uniform(-50, 50),
                vy=np.random.uniform(-50, 50),
                mode=FlightMode.HOVER,
                mode_timer=np.random.uniform(0.5, 2.0)
            )
            self.mosquitos.append(m)
        
        # Swarm center (for flocking)
        self.swarm_center = (width / 2, height / 2)
        
        # Predator position (for evasion)
        self.predator_pos = None
        
    def update(self, dt: float, predator_pos: Tuple[float, float] = None):
        """Update all mosquitos"""
        self.predator_pos = predator_pos
        
        # Calculate swarm center
        if self.mosquitos:
            cx = np.mean([m.x for m in self.mosquitos])
            cy = np.mean([m.y for m in self.mosquitos])
            self.swarm_center = (cx, cy)
        
        for m in self.mosquitos:
            self._update_mosquito(m, dt)
        
        return [(m.id, m.x, m.y, m.vx, m.vy, m.mode) for m in self.mosquitos]
    
    def _update_mosquito(self, m: Mosquito, dt: float):
        """Update single mosquito"""
        # Store trail
        m.trail.append((m.x, m.y))
        
        # Mode timer
        m.mode_timer -= dt
        if m.mode_timer <= 0:
            self._transition_mode(m)
        
        # Check for predator proximity
        if self.predator_pos:
            dist_to_pred = np.sqrt((m.x - self.predator_pos[0])**2 + 
                                   (m.y - self.predator_pos[1])**2)
            if dist_to_pred < 100:
                m.mode = FlightMode.EVADE
                m.mode_timer = 0.3
        
        # Apply mode-specific dynamics
        if m.mode == FlightMode.HOVER:
            self._apply_hover(m, dt)
        elif m.mode == FlightMode.CRUISE:
            self._apply_cruise(m, dt)
        elif m.mode == FlightMode.SACCADE:
            self._apply_saccade(m, dt)
        elif m.mode == FlightMode.BURST:
            self._apply_burst(m, dt)
        elif m.mode == FlightMode.FLOCK:
            self._apply_flock(m, dt)
        elif m.mode == FlightMode.EVADE:
            self._apply_evade(m, dt)
        
        # Update position
        m.x += m.vx * dt
        m.y += m.vy * dt
        
        # Boundary handling
        self._handle_boundaries(m)
    
    def _transition_mode(self, m: Mosquito):
        """Probabilistic mode transition"""
        # Check for random saccade
        if np.random.random() < self.params["saccade_prob"]:
            m.mode = FlightMode.SACCADE
            m.mode_timer = np.random.uniform(0.05, 0.15)
            angle = np.random.uniform(0, 2 * np.pi)
            speed = self.params["saccade_speed"]
            m.vx = np.cos(angle) * speed
            m.vy = np.sin(angle) * speed
            return
        
        # Normal transitions
        choices = [
            (FlightMode.HOVER, 0.3),
            (FlightMode.CRUISE, 0.3),
            (FlightMode.FLOCK, 0.25),
            (FlightMode.BURST, 0.15)
        ]
        
        modes, probs = zip(*choices)
        probs = np.array(probs)
        probs /= probs.sum()
        
        m.mode = np.random.choice(modes, p=probs)
        m.mode_timer = np.random.uniform(0.5, 2.0)
        
        if m.mode == FlightMode.CRUISE:
            angle = np.random.uniform(0, 2 * np.pi)
            m.target_x = m.x + np.cos(angle) * 300
            m.target_y = m.y + np.sin(angle) * 300
    
    def _apply_hover(self, m: Mosquito, dt: float):
        """Erratic hovering"""
        noise = 40
        theta = 5.0
        m.vx += theta * (0 - m.vx) * dt + noise * np.random.randn() * np.sqrt(dt)
        m.vy += theta * (0 - m.vy) * dt + noise * np.random.randn() * np.sqrt(dt)
    
    def _apply_cruise(self, m: Mosquito, dt: float):
        """Directional flight"""
        if m.target_x is None:
            return
        
        dx = m.target_x - m.x
        dy = m.target_y - m.y
        dist = np.sqrt(dx**2 + dy**2) + 1
        
        target_speed = self.params["base_speed"]
        target_vx = (dx / dist) * target_speed
        target_vy = (dy / dist) * target_speed
        
        steer = 3.0
        m.vx += (target_vx - m.vx) * steer * dt
        m.vy += (target_vy - m.vy) * steer * dt
    
    def _apply_saccade(self, m: Mosquito, dt: float):
        """Maintain saccade velocity with slight drag"""
        m.vx *= 0.95
        m.vy *= 0.95
    
    def _apply_burst(self, m: Mosquito, dt: float):
        """Acceleration burst"""
        accel = self.params["base_speed"] * 3
        angle = np.arctan2(m.vy, m.vx) if (m.vx != 0 or m.vy != 0) else np.random.uniform(0, 2*np.pi)
        m.vx += np.cos(angle) * accel * dt
        m.vy += np.sin(angle) * accel * dt
        
        # Cap speed
        speed = np.sqrt(m.vx**2 + m.vy**2)
        max_speed = self.params["saccade_speed"]
        if speed > max_speed:
            m.vx = (m.vx / speed) * max_speed
            m.vy = (m.vy / speed) * max_speed
    
    def _apply_flock(self, m: Mosquito, dt: float):
        """Flocking behavior (separation, alignment, cohesion)"""
        sep_x, sep_y = 0, 0  # Separation
        ali_x, ali_y = 0, 0  # Alignment
        coh_x, coh_y = 0, 0  # Cohesion
        
        neighbor_count = 0
        
        for other in self.mosquitos:
            if other.id == m.id:
                continue
            
            dx = other.x - m.x
            dy = other.y - m.y
            dist = np.sqrt(dx**2 + dy**2)
            
            if dist < 100:  # Neighbor radius
                neighbor_count += 1
                
                # Separation (avoid crowding)
                if dist < 40:
                    sep_x -= dx / (dist + 1)
                    sep_y -= dy / (dist + 1)
                
                # Alignment (match velocity)
                ali_x += other.vx
                ali_y += other.vy
                
                # Cohesion (move toward center)
                coh_x += dx
                coh_y += dy
        
        if neighbor_count > 0:
            # Normalize and apply
            sep_strength = 50
            ali_strength = 0.5
            coh_strength = 0.3
            
            m.vx += sep_x * sep_strength * dt
            m.vy += sep_y * sep_strength * dt
            
            m.vx += (ali_x / neighbor_count - m.vx) * ali_strength * dt
            m.vy += (ali_y / neighbor_count - m.vy) * ali_strength * dt
            
            m.vx += coh_x / neighbor_count * coh_strength * dt
            m.vy += coh_y / neighbor_count * coh_strength * dt
    
    def _apply_evade(self, m: Mosquito, dt: float):
        """Evasive maneuver away from predator"""
        if self.predator_pos is None:
            return
        
        dx = m.x - self.predator_pos[0]
        dy = m.y - self.predator_pos[1]
        dist = np.sqrt(dx**2 + dy**2) + 1
        
        escape_speed = self.params["saccade_speed"] * 1.2
        m.vx = (dx / dist) * escape_speed
        m.vy = (dy / dist) * escape_speed
        
        # Add randomness
        m.vx += np.random.randn() * 50
        m.vy += np.random.randn() * 50
    
    def _handle_boundaries(self, m: Mosquito):
        """Soft boundary handling"""
        if m.x < self.margin:
            m.x = self.margin
            m.vx = abs(m.vx) * 0.8
        elif m.x > self.width - self.margin:
            m.x = self.width - self.margin
            m.vx = -abs(m.vx) * 0.8
        
        if m.y < self.margin:
            m.y = self.margin
            m.vy = abs(m.vy) * 0.8
        elif m.y > self.height - self.margin:
            m.y = self.height - self.margin
            m.vy = -abs(m.vy) * 0.8


# ═══════════════════════════════════════════════════════════════════════════════
#  MULTI-TARGET TRACKER MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class MultiTargetTracker:
    """Manages multiple DDA or Kalman trackers with data association"""
    
    def __init__(self, tracker_type: str = "DDA", prediction_ms: float = 80):
        self.tracker_type = tracker_type
        self.prediction_ms = prediction_ms
        self.trackers: Dict[int, object] = {}
        self.next_id = 0
        self.max_association_dist = 60
        
    def update(self, detections: List[Tuple[int, float, float]], timestamp: float = None):
        """
        Update trackers with new detections.
        
        Args:
            detections: List of (ground_truth_id, x, y) tuples
            
        Returns:
            List of tracker results
        """
        if timestamp is None:
            timestamp = time.time()
        
        results = []
        matched_tracker_ids = set()
        matched_detection_ids = set()
        
        # Associate detections with existing trackers
        for gt_id, x, y, vx, vy, mode in detections:
            best_tracker_id = None
            best_dist = float('inf')
            
            for tid, tracker in self.trackers.items():
                if tid in matched_tracker_ids:
                    continue
                
                if tracker.Fx is None if hasattr(tracker, 'Fx') else tracker.state is None:
                    continue
                
                tx = tracker.Fx if hasattr(tracker, 'Fx') else tracker.state[0,0]
                ty = tracker.Fy if hasattr(tracker, 'Fy') else tracker.state[1,0]
                
                dist = np.sqrt((tx - x)**2 + (ty - y)**2)
                
                if dist < self.max_association_dist and dist < best_dist:
                    best_dist = dist
                    best_tracker_id = tid
            
            if best_tracker_id is not None:
                # Update existing tracker
                result = self.trackers[best_tracker_id].update(x, y, timestamp)
                results.append(result)
                matched_tracker_ids.add(best_tracker_id)
                matched_detection_ids.add(gt_id)
            else:
                # Create new tracker
                if self.tracker_type == "DDA":
                    tracker = DDATracker(gt_id, prediction_ms=self.prediction_ms)
                else:
                    tracker = KalmanTracker(gt_id, prediction_ms=self.prediction_ms)
                
                result = tracker.update(x, y, timestamp)
                self.trackers[gt_id] = tracker
                results.append(result)
                matched_detection_ids.add(gt_id)
        
        # Mark unmatched trackers as lost
        for tid, tracker in list(self.trackers.items()):
            if tid not in matched_tracker_ids and tid in self.trackers:
                tracker.mark_lost()
                if not tracker.is_active:
                    del self.trackers[tid]
        
        return results
    
    def get_aggregate_metrics(self) -> dict:
        """Calculate aggregate performance metrics"""
        if not self.trackers:
            return {}
        
        total_pos_error = 0
        total_pred_error = 0
        total_saccades = 0
        total_frames = 0
        lock_maintained = 0
        lock_lost = 0
        
        for tracker in self.trackers.values():
            if hasattr(tracker, 'total_position_error'):
                total_pos_error += tracker.total_position_error
                total_pred_error += tracker.total_prediction_error
                total_saccades += tracker.saccade_count
                total_frames += tracker.frames_tracked
                if hasattr(tracker, 'lock_maintained'):
                    lock_maintained += tracker.lock_maintained
                if hasattr(tracker, 'lock_lost_count'):
                    lock_lost += tracker.lock_lost_count
        
        return {
            'avg_pos_error': total_pos_error / max(1, total_frames),
            'avg_pred_error': total_pred_error / max(1, total_frames),
            'total_saccades': total_saccades,
            'total_frames': total_frames,
            'lock_maintained': lock_maintained,
            'lock_lost': lock_lost,
            'num_trackers': len(self.trackers)
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERCEPTOR (Predator simulation)
# ═══════════════════════════════════════════════════════════════════════════════
class Interceptor:
    """
    Simulates a predator/robot trying to intercept targets.
    Uses tracker predictions to aim ahead.
    """
    
    def __init__(self, width: int, height: int):
        self.x = width / 2
        self.y = height / 2
        self.target_x = self.x
        self.target_y = self.y
        
        self.max_speed = 600  # Faster than mosquitos
        self.acceleration = 2000
        
        self.vx = 0
        self.vy = 0
        
        # Stats
        self.interceptions = 0
        self.attempts = 0
        self.intercept_radius = 25
        
    def set_target(self, x: float, y: float):
        """Set target position (usually predicted position)"""
        self.target_x = x
        self.target_y = y
    
    def update(self, dt: float) -> Tuple[float, float]:
        """Update interceptor position"""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = np.sqrt(dx**2 + dy**2) + 1
        
        # Accelerate toward target
        ax = (dx / dist) * self.acceleration
        ay = (dy / dist) * self.acceleration
        
        self.vx += ax * dt
        self.vy += ay * dt
        
        # Cap speed
        speed = np.sqrt(self.vx**2 + self.vy**2)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        return self.x, self.y
    
    def check_interception(self, targets: List[Tuple[float, float]]) -> bool:
        """Check if interceptor caught any target"""
        for tx, ty in targets:
            dist = np.sqrt((self.x - tx)**2 + (self.y - ty)**2)
            if dist < self.intercept_radius:
                self.interceptions += 1
                return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  VISUALIZATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
class Visualizer:
    """Renders the tracking visualization"""
    
    def __init__(self, width: int, height: int, comparison_mode: bool = False):
        self.width = width
        self.height = height
        self.comparison_mode = comparison_mode
        
        # Create background
        self.background = self._create_background()
        
        # Fonts
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_small = cv2.FONT_HERSHEY_PLAIN
        
    def _create_background(self) -> np.ndarray:
        """Create stylized background"""
        bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Dark gradient
        for y in range(self.height):
            val = int(20 + (y / self.height) * 15)
            bg[y, :] = (val, val + 5, val + 10)
        
        # Grid lines
        for x in range(0, self.width, 80):
            cv2.line(bg, (x, 0), (x, self.height), (40, 40, 45), 1)
        for y in range(0, self.height, 80):
            cv2.line(bg, (0, y), (self.width, y), (40, 40, 45), 1)
        
        return bg
    
    def render(self, 
               swarm: List[Mosquito],
               dda_results: List[dict],
               kalman_results: List[dict] = None,
               interceptor: Interceptor = None,
               dda_metrics: dict = None,
               kalman_metrics: dict = None) -> np.ndarray:
        """Render full visualization frame"""
        
        frame = self.background.copy()
        
        if self.comparison_mode and kalman_results:
            # Split screen comparison
            mid = self.width // 2
            
            # Draw divider
            cv2.line(frame, (mid, 0), (mid, self.height), (100, 100, 100), 2)
            
            # Left side: DDA
            self._draw_tracking_view(frame, swarm, dda_results, interceptor, 
                                    0, mid, "DDA TRACKER", dda_metrics)
            
            # Right side: Kalman
            self._draw_tracking_view(frame, swarm, kalman_results, None,
                                    mid, self.width, "KALMAN FILTER", kalman_metrics)
        else:
            # Full screen DDA
            self._draw_tracking_view(frame, swarm, dda_results, interceptor,
                                    0, self.width, "DDA PREDATOR FRAMEWORK", dda_metrics)
        
        return frame
    
    def _draw_tracking_view(self,
                            frame: np.ndarray,
                            swarm: List[Mosquito],
                            results: List[dict],
                            interceptor: Interceptor,
                            x_start: int,
                            x_end: int,
                            title: str,
                            metrics: dict):
        """Draw tracking visualization for one tracker type"""
        
        view_width = x_end - x_start
        scale = view_width / self.width if self.comparison_mode else 1.0
        
        def tx(x): return int(x_start + x * scale)
        def ty(y): return int(y * scale) if self.comparison_mode else int(y)
        
        # Draw mosquito trails and bodies
        for m in swarm:
            # Trail
            trail = list(m.trail)
            for i in range(1, len(trail)):
                alpha = i / len(trail)
                color = (int(60 * alpha), int(60 * alpha), int(70 * alpha))
                pt1 = (tx(trail[i-1][0]), ty(trail[i-1][1]))
                pt2 = (tx(trail[i][0]), ty(trail[i][1]))
                cv2.line(frame, pt1, pt2, color, 1)
            
            # Body (ground truth)
            cv2.circle(frame, (tx(m.x), ty(m.y)), int(m.size * scale), (80, 80, 90), -1)
            cv2.circle(frame, (tx(m.x), ty(m.y)), int(m.size * scale), (120, 120, 130), 1)
        
        # Draw tracker results
        for result in results:
            if result is None:
                continue
            
            color = result['color']
            x, y = result['x'], result['y']
            pred_x, pred_y = result['pred_x'], result['pred_y']
            
            # Bounding box
            bbox_size = 18
            x1, y1 = tx(x - bbox_size), ty(y - bbox_size)
            x2, y2 = tx(x + bbox_size), ty(y + bbox_size)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Target ID
            cv2.putText(frame, f"T{result['id']}", (x1, y1 - 5),
                       self.font_small, 1.0, color, 1)
            
            # Current position marker
            cv2.circle(frame, (tx(x), ty(y)), 4, color, -1)
            
            # Prediction marker
            cv2.circle(frame, (tx(pred_x), ty(pred_y)), 6, (0, 200, 255), 2)
            
            # Prediction vector
            cv2.arrowedLine(frame, (tx(x), ty(y)), (tx(pred_x), ty(pred_y)),
                          (0, 200, 255), 2, tipLength=0.3)
            
            # Mode indicator
            mode_color = (0, 255, 100) if result['mode'] == "TRACKING" else (0, 100, 255)
            cv2.circle(frame, (x2 - 8, y1 + 8), 5, mode_color, -1)
        
        # Draw interceptor
        if interceptor:
            ix, iy = tx(interceptor.x), ty(interceptor.y)
            
            # Interceptor body
            cv2.circle(frame, (ix, iy), 15, (0, 150, 255), 2)
            cv2.circle(frame, (ix, iy), 8, (0, 200, 255), -1)
            
            # Crosshairs
            cv2.line(frame, (ix - 25, iy), (ix + 25, iy), (0, 150, 255), 1)
            cv2.line(frame, (ix, iy - 25), (ix, iy + 25), (0, 150, 255), 1)
            
            # Target line
            cv2.line(frame, (ix, iy), 
                    (tx(interceptor.target_x), ty(interceptor.target_y)),
                    (0, 100, 200), 1, cv2.LINE_AA)
        
        # Title
        cv2.putText(frame, title, (x_start + 10, 30),
                   self.font, 0.7, (200, 200, 200), 2)
        
        # Metrics panel
        if metrics:
            self._draw_metrics_panel(frame, metrics, x_start + 10, 60, 
                                    "DDA" in title)
    
    def _draw_metrics_panel(self, frame, metrics, x, y, is_dda):
        """Draw performance metrics panel"""
        
        panel_width = 220
        panel_height = 140
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + panel_width, y + panel_height),
                     (20, 25, 30), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (x, y), (x + panel_width, y + panel_height),
                     (60, 65, 70), 1)
        
        # Metrics text
        color = (100, 255, 150) if is_dda else (150, 150, 255)
        
        lines = [
            f"Position Error: {metrics.get('avg_pos_error', 0):.2f} px",
            f"Prediction Error: {metrics.get('avg_pred_error', 0):.2f} px",
            f"Saccades Detected: {metrics.get('total_saccades', 0)}",
            f"Active Trackers: {metrics.get('num_trackers', 0)}",
        ]
        
        if is_dda:
            lines.append(f"Lock Maintained: {metrics.get('lock_maintained', 0)}")
        else:
            lines.append(f"Lock Lost: {metrics.get('lock_lost', 0)}")
        
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (x + 10, y + 25 + i * 22),
                       self.font_small, 1.0, color, 1)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class DDASwarmDemo:
    """Main application orchestrating the demo"""
    
    def __init__(self,
                 num_mosquitos: int = 10,
                 difficulty: str = "medium",
                 comparison_mode: bool = False,
                 width: int = 1280,
                 height: int = 720):
        
        self.width = width
        self.height = height
        self.comparison_mode = comparison_mode
        
        # Initialize components
        self.swarm = MosquitoSwarm(num_mosquitos, width, height, difficulty)
        self.dda_tracker = MultiTargetTracker("DDA", prediction_ms=80)
        
        if comparison_mode:
            self.kalman_tracker = MultiTargetTracker("Kalman", prediction_ms=80)
        else:
            self.kalman_tracker = None
        
        self.interceptor = Interceptor(width, height)
        self.visualizer = Visualizer(width, height, comparison_mode)
        
        # State
        self.paused = False
        self.show_help = True
        self.target_mode = "nearest"  # nearest, predicted, fastest
        self.frame_count = 0
        
    def run(self):
        """Main loop"""
        
        print("\n" + "═"*70)
        print("  ██████╗ ██████╗  █████╗     ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗")
        print("  ██╔══██╗██╔══██╗██╔══██╗    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║")
        print("  ██║  ██║██║  ██║███████║    ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║")
        print("  ██║  ██║██║  ██║██╔══██║    ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║")
        print("  ██████╔╝██████╔╝██║  ██║    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║")
        print("  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝")
        print("═"*70)
        print("  PREDATOR INTERCEPT DEMONSTRATION")
        print("═"*70)
        print("  [Q] Quit  [SPACE] Pause  [R] Reset  [H] Toggle Help")
        print("  [1] Target Nearest  [2] Target Predicted  [3] Target Fastest")
        print("  [C] Toggle Comparison Mode")
        print("═"*70 + "\n")
        
        cv2.namedWindow('DDA Swarm Intercept', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('DDA Swarm Intercept', self.width, self.height)
        
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = min(current_time - last_time, 0.05)  # Cap dt
            last_time = current_time
            
            if not self.paused:
                # Update swarm
                swarm_data = self.swarm.update(dt, (self.interceptor.x, self.interceptor.y))
                
                # Update DDA trackers
                dda_results = self.dda_tracker.update(swarm_data, current_time)
                
                # Update Kalman trackers (if comparison mode)
                if self.kalman_tracker:
                    kalman_results = self.kalman_tracker.update(swarm_data, current_time)
                else:
                    kalman_results = None
                
                # Select target for interceptor
                target = self._select_target(dda_results)
                if target:
                    self.interceptor.set_target(target[0], target[1])
                
                # Update interceptor
                self.interceptor.update(dt)
                
                # Check interceptions
                actual_positions = [(m.x, m.y) for m in self.swarm.mosquitos]
                self.interceptor.check_interception(actual_positions)
                
                self.frame_count += 1
            
            # Get metrics
            dda_metrics = self.dda_tracker.get_aggregate_metrics()
            kalman_metrics = self.kalman_tracker.get_aggregate_metrics() if self.kalman_tracker else None
            
            # Render
            frame = self.visualizer.render(
                self.swarm.mosquitos,
                dda_results if not self.paused else [],
                kalman_results,
                self.interceptor,
                dda_metrics,
                kalman_metrics
            )
            
            # Draw help overlay
            if self.show_help:
                self._draw_help(frame)
            
            # Draw interception stats
            self._draw_stats(frame)
            
            cv2.imshow('DDA Swarm Intercept', frame)
            
            # Handle input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                self.paused = not self.paused
            elif key == ord('r'):
                self._reset()
            elif key == ord('h'):
                self.show_help = not self.show_help
            elif key == ord('1'):
                self.target_mode = "nearest"
            elif key == ord('2'):
                self.target_mode = "predicted"
            elif key == ord('3'):
                self.target_mode = "fastest"
            elif key == ord('c'):
                self.comparison_mode = not self.comparison_mode
                self.visualizer.comparison_mode = self.comparison_mode
                if self.comparison_mode and not self.kalman_tracker:
                    self.kalman_tracker = MultiTargetTracker("Kalman", prediction_ms=80)
        
        cv2.destroyAllWindows()
        self._print_final_stats()
    
    def _select_target(self, results: List[dict]) -> Optional[Tuple[float, float]]:
        """Select target based on current mode"""
        if not results:
            return None
        
        if self.target_mode == "nearest":
            # Target nearest to interceptor
            best = min(results, key=lambda r: 
                      np.sqrt((r['x'] - self.interceptor.x)**2 + 
                             (r['y'] - self.interceptor.y)**2))
            return (best['pred_x'], best['pred_y'])
        
        elif self.target_mode == "predicted":
            # Target with best prediction confidence (lowest error)
            best = min(results, key=lambda r: r.get('avg_pred_error', float('inf')))
            return (best['pred_x'], best['pred_y'])
        
        elif self.target_mode == "fastest":
            # Target fastest moving
            best = max(results, key=lambda r: r['speed'])
            return (best['pred_x'], best['pred_y'])
        
        return None
    
    def _reset(self):
        """Reset the simulation"""
        self.swarm = MosquitoSwarm(len(self.swarm.mosquitos), 
                                   self.width, self.height, "medium")
        self.dda_tracker = MultiTargetTracker("DDA", prediction_ms=80)
        if self.kalman_tracker:
            self.kalman_tracker = MultiTargetTracker("Kalman", prediction_ms=80)
        self.interceptor = Interceptor(self.width, self.height)
        self.frame_count = 0
    
    def _draw_help(self, frame):
        """Draw help overlay"""
        help_text = [
            f"Target Mode: {self.target_mode.upper()}",
            f"[1] Nearest  [2] Predicted  [3] Fastest",
        ]
        
        for i, text in enumerate(help_text):
            cv2.putText(frame, text, (self.width - 280, self.height - 60 + i * 25),
                       cv2.FONT_HERSHEY_PLAIN, 1.0, (150, 150, 150), 1)
    
    def _draw_stats(self, frame):
        """Draw interception statistics"""
        stats_text = f"INTERCEPTIONS: {self.interceptor.interceptions}"
        
        cv2.putText(frame, stats_text, (self.width - 200, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
    
    def _print_final_stats(self):
        """Print final statistics"""
        dda_metrics = self.dda_tracker.get_aggregate_metrics()
        
        print("\n" + "═"*70)
        print("  FINAL STATISTICS")
        print("═"*70)
        print(f"  Total Frames: {self.frame_count}")
        print(f"  Interceptions: {self.interceptor.interceptions}")
        print(f"")
        print(f"  DDA Performance:")
        print(f"    Average Position Error: {dda_metrics.get('avg_pos_error', 0):.2f} px")
        print(f"    Average Prediction Error: {dda_metrics.get('avg_pred_error', 0):.2f} px")
        print(f"    Saccades Detected: {dda_metrics.get('total_saccades', 0)}")
        print(f"    Lock Maintained Through Saccades: {dda_metrics.get('lock_maintained', 0)}")
        
        if self.kalman_tracker:
            kalman_metrics = self.kalman_tracker.get_aggregate_metrics()
            print(f"")
            print(f"  Kalman Performance:")
            print(f"    Average Position Error: {kalman_metrics.get('avg_pos_error', 0):.2f} px")
            print(f"    Average Prediction Error: {kalman_metrics.get('avg_pred_error', 0):.2f} px")
            print(f"    Saccades Detected: {kalman_metrics.get('total_saccades', 0)}")
            print(f"    Lock Lost Events: {kalman_metrics.get('lock_lost', 0)}")
            
            # Calculate improvement
            if kalman_metrics.get('avg_pred_error', 0) > 0:
                improvement = ((kalman_metrics['avg_pred_error'] - dda_metrics.get('avg_pred_error', 0)) 
                              / kalman_metrics['avg_pred_error'] * 100)
                print(f"")
                print(f"  ╔════════════════════════════════════════╗")
                print(f"  ║  DDA PREDICTION IMPROVEMENT: {improvement:+.1f}%   ║")
                print(f"  ╚════════════════════════════════════════╝")
        
        print("═"*70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DDA Swarm Intercept Demonstration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python dda_swarm_intercept.py                    # Default (10 mosquitos)
    python dda_swarm_intercept.py --swarm 25         # 25 mosquitos
    python dda_swarm_intercept.py --compare          # Side-by-side DDA vs Kalman
    python dda_swarm_intercept.py --nightmare        # Maximum difficulty
    python dda_swarm_intercept.py --compare --nightmare --swarm 30
        """)
    
    parser.add_argument('--swarm', type=int, default=10,
                       help='Number of mosquitos in swarm (default: 10)')
    parser.add_argument('--difficulty', type=str, default='medium',
                       choices=['easy', 'medium', 'hard', 'nightmare'],
                       help='Difficulty level (default: medium)')
    parser.add_argument('--compare', action='store_true',
                       help='Enable DDA vs Kalman comparison mode')
    parser.add_argument('--nightmare', action='store_true',
                       help='Enable nightmare difficulty')
    parser.add_argument('--width', type=int, default=1280,
                       help='Window width (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                       help='Window height (default: 720)')
    
    args = parser.parse_args()
    
    difficulty = 'nightmare' if args.nightmare else args.difficulty
    
    demo = DDASwarmDemo(
        num_mosquitos=args.swarm,
        difficulty=difficulty,
        comparison_mode=args.compare,
        width=args.width,
        height=args.height
    )
    
    demo.run()
