"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     DDA MOSQUITO TERMINATOR v2.0                                             ║
║     ════════════════════════════                                             ║
║                                                                              ║
║     LASER TURRET DEMONSTRATION                                               ║
║                                                                              ║
║     The ultimate proof of DDA superiority:                                   ║
║       - Turret fires at PREDICTED position                                   ║
║       - Good prediction = HIT                                                ║
║       - Bad prediction = MISS                                                ║
║                                                                              ║
║     Compare DDA vs Kalman hit rates in real-time.                            ║
║     Watch the kill counter. Feel the satisfaction.                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python dda_terminator.py                      # Default mode
    python dda_terminator.py --compare            # DDA vs Kalman comparison
    python dda_terminator.py --nightmare --swarm 30
    python dda_terminator.py --auto               # Full auto mode
"""

import cv2
import numpy as np
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import colorsys
import argparse
import random


# ═══════════════════════════════════════════════════════════════════════════════
#  DDA TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
class DDATracker:
    """snakewizardd's Dynamic Decision Algorithm - maintains lock through saccades"""
    
    def __init__(self, target_id: int, prediction_ms: float = 60):
        self.id = target_id
        self.prediction_ms = prediction_ms
        
        self.Fx = None
        self.Fy = None
        self.vx = 0.0
        self.vy = 0.0
        
        self.history = deque(maxlen=20)
        self.timestamps = deque(maxlen=20)
        
        self.volatility = 1.0
        self.mode = "ACQUIRING"
        self.frames = 0
        
        # Tuned parameters
        self.P0_stable = 0.82
        self.P0_saccade = 0.12
        self.saccade_thresh = 3.5
        
        # Color
        hue = (target_id * 0.618033988749895) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
        self.is_active = True
        self.lost_frames = 0
        
    def update(self, x: float, y: float, timestamp: float = None) -> dict:
        if timestamp is None:
            timestamp = time.time()
        
        if self.Fx is None:
            self.Fx, self.Fy = x, y
            self.history.append((x, y))
            self.timestamps.append(timestamp)
            self.frames = 1
            return self._result()
        
        # Position error
        error = np.sqrt((x - self.Fx)**2 + (y - self.Fy)**2)
        
        # Update volatility
        if len(self.history) >= 5:
            recent = list(self.history)[-5:]
            diffs = [np.sqrt((recent[i+1][0]-recent[i][0])**2 + 
                            (recent[i+1][1]-recent[i][1])**2) 
                    for i in range(len(recent)-1)]
            self.volatility = max(1.0, np.std(diffs) * 2)
        
        # Saccade detection
        is_saccade = error > (self.saccade_thresh * self.volatility)
        P0 = self.P0_saccade if is_saccade else self.P0_stable
        self.mode = "SACCADE" if is_saccade else "TRACKING"
        
        # Velocity estimation
        self.vx, self.vy = self._velocity(timestamp)
        
        # DDA update with predictive boost
        dt = timestamp - self.timestamps[-1] if self.timestamps else 0.016
        boost = 0.25
        self.Fx = P0 * self.Fx + (1 - P0) * (x + boost * self.vx * dt)
        self.Fy = P0 * self.Fy + (1 - P0) * (y + boost * self.vy * dt)
        
        self.history.append((x, y))
        self.timestamps.append(timestamp)
        self.frames += 1
        self.lost_frames = 0
        
        return self._result()
    
    def _velocity(self, t):
        if len(self.history) < 2:
            return 0, 0
        n = min(5, len(self.history))
        h = list(self.history)
        ts = list(self.timestamps)
        dx = h[-1][0] - h[-n][0]
        dy = h[-1][1] - h[-n][1]
        dt = ts[-1] - ts[-n]
        return (dx/dt, dy/dt) if dt > 0 else (0, 0)
    
    def _result(self):
        dt = self.prediction_ms / 1000.0
        return {
            'id': self.id,
            'x': self.Fx, 'y': self.Fy,
            'pred_x': self.Fx + self.vx * dt,
            'pred_y': self.Fy + self.vy * dt,
            'vx': self.vx, 'vy': self.vy,
            'speed': np.sqrt(self.vx**2 + self.vy**2),
            'mode': self.mode,
            'color': self.color
        }
    
    def predict(self, ms_ahead):
        dt = ms_ahead / 1000.0
        return self.Fx + self.vx * dt, self.Fy + self.vy * dt
    
    def mark_lost(self):
        self.lost_frames += 1
        if self.lost_frames > 30:
            self.is_active = False


class KalmanTracker:
    """Standard Kalman for comparison"""
    
    def __init__(self, target_id: int, prediction_ms: float = 60):
        self.id = target_id
        self.prediction_ms = prediction_ms
        
        self.kf = cv2.KalmanFilter(4, 2)
        dt = 1/60
        self.kf.transitionMatrix = np.array([
            [1, 0, dt, 0], [0, 1, 0, dt],
            [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32)
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0
        
        self.initialized = False
        self.state = None
        self.mode = "ACQUIRING"
        
        hue = (target_id * 0.618033988749895) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
        self.color = (int(rgb[2]*255), int(rgb[1]*255), int(rgb[0]*255))
        
        self.is_active = True
        self.lost_frames = 0
        
    def update(self, x, y, timestamp=None):
        if not self.initialized:
            self.kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
            self.initialized = True
            self.state = self.kf.statePost.copy()
            return self._result()
        
        self.kf.predict()
        self.kf.correct(np.array([[x], [y]], dtype=np.float32))
        self.state = self.kf.statePost.copy()
        self.lost_frames = 0
        self.mode = "TRACKING"
        return self._result()
    
    def _result(self):
        if self.state is None:
            return None
        x, y = self.state[0,0], self.state[1,0]
        vx, vy = self.state[2,0], self.state[3,0]
        dt = self.prediction_ms / 1000.0
        return {
            'id': self.id,
            'x': x, 'y': y,
            'pred_x': x + vx * dt,
            'pred_y': y + vy * dt,
            'vx': vx, 'vy': vy,
            'speed': np.sqrt(vx**2 + vy**2),
            'mode': self.mode,
            'color': self.color
        }
    
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
#  MOSQUITO SWARM
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
    trail: deque = field(default_factory=lambda: deque(maxlen=15))


class MosquitoSwarm:
    def __init__(self, num: int, width: int, height: int, difficulty: str = "medium"):
        self.width = width
        self.height = height
        self.margin = 80
        self.next_id = 0
        
        self.params = {
            "easy": {"speed": 120, "saccade": 300, "prob": 0.03},
            "medium": {"speed": 200, "saccade": 500, "prob": 0.06},
            "hard": {"speed": 320, "saccade": 700, "prob": 0.10},
            "nightmare": {"speed": 450, "saccade": 950, "prob": 0.15}
        }[difficulty]
        
        self.mosquitos: List[Mosquito] = []
        self.dead_mosquitos: List[Mosquito] = []  # For death animations
        
        for _ in range(num):
            self._spawn()
    
    def _spawn(self):
        m = Mosquito(
            id=self.next_id,
            x=random.uniform(self.margin, self.width - self.margin),
            y=random.uniform(self.margin, self.height - self.margin),
            vx=random.uniform(-80, 80),
            vy=random.uniform(-80, 80),
            mode_timer=random.uniform(0.5, 2.0)
        )
        self.next_id += 1
        self.mosquitos.append(m)
    
    def update(self, dt: float):
        # Update dead mosquitos (for animation)
        for m in self.dead_mosquitos[:]:
            m.death_timer -= dt
            if m.death_timer <= 0:
                self.dead_mosquitos.remove(m)
        
        # Update live mosquitos
        for m in self.mosquitos:
            m.trail.append((m.x, m.y))
            m.mode_timer -= dt
            
            # Random saccade
            if m.mode_timer <= 0 or random.random() < self.params["prob"] * dt:
                if random.random() < 0.3:  # Saccade
                    angle = random.uniform(0, 2 * np.pi)
                    speed = self.params["saccade"]
                    m.vx = np.cos(angle) * speed
                    m.vy = np.sin(angle) * speed
                    m.mode_timer = random.uniform(0.08, 0.2)
                else:  # Cruise or hover
                    angle = random.uniform(0, 2 * np.pi)
                    speed = self.params["speed"] * random.uniform(0.3, 1.0)
                    m.vx = np.cos(angle) * speed
                    m.vy = np.sin(angle) * speed
                    m.mode_timer = random.uniform(0.5, 2.0)
            
            # Add noise
            m.vx += random.gauss(0, 30) * dt * 60
            m.vy += random.gauss(0, 30) * dt * 60
            
            # Drag
            m.vx *= 0.995
            m.vy *= 0.995
            
            # Update position
            m.x += m.vx * dt
            m.y += m.vy * dt
            
            # Boundaries
            if m.x < self.margin:
                m.x = self.margin
                m.vx = abs(m.vx)
            elif m.x > self.width - self.margin:
                m.x = self.width - self.margin
                m.vx = -abs(m.vx)
            if m.y < self.margin:
                m.y = self.margin
                m.vy = abs(m.vy)
            elif m.y > self.height - self.margin:
                m.y = self.height - self.margin
                m.vy = -abs(m.vy)
        
        return [(m.id, m.x, m.y, m.vx, m.vy) for m in self.mosquitos]
    
    def kill(self, mosquito_id: int) -> bool:
        """Kill a mosquito, returns True if found"""
        for m in self.mosquitos:
            if m.id == mosquito_id:
                # Store death position for animation
                m.death_x = m.x
                m.death_y = m.y
                m.death_timer = 0.5
                m.alive = False
                self.dead_mosquitos.append(m)
                self.mosquitos.remove(m)
                # Respawn a new one
                self._spawn()
                return True
        return False
    
    def get_position(self, mosquito_id: int) -> Optional[Tuple[float, float]]:
        for m in self.mosquitos:
            if m.id == mosquito_id:
                return m.x, m.y
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  LASER TURRET
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class LaserShot:
    """Represents a laser shot for visualization"""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    hit: bool
    timer: float = 0.15
    target_id: int = -1


class LaserTurret:
    """
    Fires at predicted positions.
    Hit detection checks if prediction was accurate.
    """
    
    def __init__(self, x: float, y: float, hit_radius: float = 25):
        self.x = x
        self.y = y
        self.hit_radius = hit_radius
        
        # Cooldown
        self.cooldown = 0
        self.fire_rate = 0.08  # Seconds between shots (12.5 shots/sec)
        
        # Stats
        self.shots_fired = 0
        self.hits = 0
        self.misses = 0
        
        # Active laser shots for visualization
        self.active_shots: List[LaserShot] = []
        
        # Aiming
        self.aim_x = x
        self.aim_y = y
        self.current_target_id = -1
        
    def aim_at(self, x: float, y: float, target_id: int = -1):
        """Set aim point"""
        self.aim_x = x
        self.aim_y = y
        self.current_target_id = target_id
    
    def fire(self, predicted_x: float, predicted_y: float, 
             actual_x: float, actual_y: float, target_id: int) -> bool:
        """
        Fire at predicted position, check against actual.
        Returns True if hit.
        """
        if self.cooldown > 0:
            return False
        
        self.cooldown = self.fire_rate
        self.shots_fired += 1
        
        # Check if prediction was accurate enough
        error = np.sqrt((predicted_x - actual_x)**2 + (predicted_y - actual_y)**2)
        hit = error <= self.hit_radius
        
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        
        # Create visual laser shot
        shot = LaserShot(
            start_x=self.x,
            start_y=self.y,
            end_x=predicted_x,
            end_y=predicted_y,
            hit=hit,
            target_id=target_id
        )
        self.active_shots.append(shot)
        
        return hit
    
    def update(self, dt: float):
        """Update cooldown and shot animations"""
        self.cooldown = max(0, self.cooldown - dt)
        
        # Update shot animations
        for shot in self.active_shots[:]:
            shot.timer -= dt
            if shot.timer <= 0:
                self.active_shots.remove(shot)
    
    @property
    def accuracy(self) -> float:
        if self.shots_fired == 0:
            return 0
        return self.hits / self.shots_fired * 100
    
    @property
    def ready(self) -> bool:
        return self.cooldown <= 0


# ═══════════════════════════════════════════════════════════════════════════════
#  PARTICLE EFFECTS
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
    
    def spawn_explosion(self, x: float, y: float, color: Tuple[int, int, int] = (255, 100, 50)):
        """Spawn death explosion particles"""
        for _ in range(20):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(100, 400)
            self.particles.append(Particle(
                x=x, y=y,
                vx=np.cos(angle) * speed,
                vy=np.sin(angle) * speed,
                life=random.uniform(0.2, 0.5),
                color=color,
                size=random.uniform(2, 6)
            ))
    
    def spawn_spark(self, x: float, y: float):
        """Spawn hit spark"""
        for _ in range(8):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(50, 150)
            self.particles.append(Particle(
                x=x, y=y,
                vx=np.cos(angle) * speed,
                vy=np.sin(angle) * speed,
                life=random.uniform(0.1, 0.2),
                color=(255, 255, 200),
                size=random.uniform(1, 3)
            ))
    
    def update(self, dt: float):
        for p in self.particles[:]:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 200 * dt  # Gravity
            p.life -= dt
            p.size *= 0.95
            if p.life <= 0:
                self.particles.remove(p)
    
    def draw(self, frame: np.ndarray):
        for p in self.particles:
            alpha = min(1.0, p.life * 3)
            color = tuple(int(c * alpha) for c in p.color)
            cv2.circle(frame, (int(p.x), int(p.y)), int(p.size), color, -1)


# ═══════════════════════════════════════════════════════════════════════════════
#  TRACKER MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class TrackerManager:
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
            mid, x, y, vx, vy = det
            seen_ids.add(mid)
            
            if mid not in self.trackers:
                if self.tracker_type == "DDA":
                    self.trackers[mid] = DDATracker(mid, self.prediction_ms)
                else:
                    self.trackers[mid] = KalmanTracker(mid, self.prediction_ms)
            
            result = self.trackers[mid].update(x, y, timestamp)
            if result:
                results.append(result)
        
        # Remove dead trackers
        for mid in list(self.trackers.keys()):
            if mid not in seen_ids:
                self.trackers[mid].mark_lost()
                if not self.trackers[mid].is_active:
                    del self.trackers[mid]
        
        return results
    
    def get_tracker(self, target_id: int):
        return self.trackers.get(target_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class DDATerminator:
    def __init__(self,
                 num_mosquitos: int = 15,
                 difficulty: str = "medium",
                 comparison_mode: bool = False,
                 auto_fire: bool = True,
                 width: int = 1280,
                 height: int = 720):
        
        self.width = width
        self.height = height
        self.comparison_mode = comparison_mode
        self.auto_fire = auto_fire
        
        # Components
        self.swarm = MosquitoSwarm(num_mosquitos, width, height, difficulty)
        
        # DDA system (always active)
        self.dda_trackers = TrackerManager("DDA", prediction_ms=60)
        self.dda_turret = LaserTurret(width // 2, height - 50, hit_radius=28)
        
        # Kalman system (comparison mode)
        if comparison_mode:
            self.kalman_trackers = TrackerManager("Kalman", prediction_ms=60)
            self.kalman_turret = LaserTurret(width // 2, height - 50, hit_radius=28)
        else:
            self.kalman_trackers = None
            self.kalman_turret = None
        
        self.particles = ParticleSystem()
        
        # State
        self.paused = False
        self.frame_count = 0
        self.kills = 0
        self.difficulty = difficulty
        
        # Background
        self.background = self._create_background()
        
    def _create_background(self):
        bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Dark gradient
        for y in range(self.height):
            val = int(15 + (y / self.height) * 20)
            bg[y, :] = (val, val + 3, val + 8)
        
        # Grid
        for x in range(0, self.width, 60):
            cv2.line(bg, (x, 0), (x, self.height), (30, 32, 38), 1)
        for y in range(0, self.height, 60):
            cv2.line(bg, (0, y), (self.width, y), (30, 32, 38), 1)
        
        return bg
    
    def run(self):
        print("\n" + "═"*70)
        print("  ██████╗ ██████╗  █████╗     ████████╗███████╗██████╗ ███╗   ███╗")
        print("  ██╔══██╗██╔══██╗██╔══██╗    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║")
        print("  ██║  ██║██║  ██║███████║       ██║   █████╗  ██████╔╝██╔████╔██║")
        print("  ██║  ██║██║  ██║██╔══██║       ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║")
        print("  ██████╔╝██████╔╝██║  ██║       ██║   ███████╗██║  ██║██║ ╚═╝ ██║")
        print("  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝")
        print("═"*70)
        print(f"  Mode: {'COMPARISON (DDA vs Kalman)' if self.comparison_mode else 'DDA HUNTER'}")
        print(f"  Difficulty: {self.difficulty.upper()}")
        print("═"*70)
        print("  [Q] Quit   [SPACE] Pause   [R] Reset   [C] Toggle Comparison")
        print("  [A] Toggle Auto-fire   [CLICK] Manual fire")
        print("═"*70 + "\n")
        
        cv2.namedWindow('DDA Terminator', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('DDA Terminator', self.width, self.height)
        
        # Mouse callback for manual firing
        cv2.setMouseCallback('DDA Terminator', self._mouse_callback)
        
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = min(current_time - last_time, 0.05)
            last_time = current_time
            
            if not self.paused:
                self._update(dt, current_time)
            
            frame = self._render()
            cv2.imshow('DDA Terminator', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                self.paused = not self.paused
            elif key == ord('r'):
                self._reset()
            elif key == ord('c'):
                self._toggle_comparison()
            elif key == ord('a'):
                self.auto_fire = not self.auto_fire
                print(f"  Auto-fire: {'ON' if self.auto_fire else 'OFF'}")
        
        cv2.destroyAllWindows()
        self._print_final_stats()
    
    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and not self.auto_fire:
            # Manual fire at click position
            pass  # Could implement manual targeting
    
    def _update(self, dt: float, timestamp: float):
        # Update swarm
        detections = self.swarm.update(dt)
        
        # Update DDA trackers
        dda_results = self.dda_trackers.update(detections, timestamp)
        
        # Update Kalman trackers
        if self.kalman_trackers:
            kalman_results = self.kalman_trackers.update(detections, timestamp)
        
        # Update turrets
        self.dda_turret.update(dt)
        if self.kalman_turret:
            self.kalman_turret.update(dt)
        
        # Auto-fire logic
        if self.auto_fire and dda_results:
            self._auto_fire_cycle(dda_results, timestamp)
        
        # Update particles
        self.particles.update(dt)
        
        self.frame_count += 1
    
    def _auto_fire_cycle(self, dda_results, timestamp):
        """Fire at targets using predictions"""
        
        # Find best target (nearest to turret with good tracking)
        best_target = None
        best_score = float('inf')
        
        for result in dda_results:
            # Score based on distance and tracking confidence
            dist = np.sqrt((result['pred_x'] - self.dda_turret.x)**2 +
                          (result['pred_y'] - self.dda_turret.y)**2)
            if dist < best_score:
                best_score = dist
                best_target = result
        
        if best_target and self.dda_turret.ready:
            target_id = best_target['id']
            pred_x, pred_y = best_target['pred_x'], best_target['pred_y']
            
            # Get actual position at moment of "impact"
            actual = self.swarm.get_position(target_id)
            if actual:
                actual_x, actual_y = actual
                
                # DDA fires
                hit = self.dda_turret.fire(pred_x, pred_y, actual_x, actual_y, target_id)
                
                if hit:
                    self.swarm.kill(target_id)
                    self.kills += 1
                    self.particles.spawn_explosion(actual_x, actual_y, (255, 150, 50))
                else:
                    self.particles.spawn_spark(pred_x, pred_y)
                
                # Kalman also fires at same target for comparison
                if self.kalman_turret and self.kalman_trackers:
                    kalman_tracker = self.kalman_trackers.get_tracker(target_id)
                    if kalman_tracker:
                        k_pred = kalman_tracker.predict(60)
                        if k_pred[0] is not None:
                            k_hit = self.kalman_turret.fire(
                                k_pred[0], k_pred[1],
                                actual_x, actual_y, target_id
                            )
                            # Kalman doesn't actually kill (DDA already did or didn't)
        
        # Update aim visualization
        if best_target:
            self.dda_turret.aim_at(best_target['pred_x'], best_target['pred_y'], 
                                   best_target['id'])
    
    def _render(self) -> np.ndarray:
        frame = self.background.copy()
        
        # Draw mosquito trails and bodies
        for m in self.swarm.mosquitos:
            # Trail
            trail = list(m.trail)
            for i in range(1, len(trail)):
                alpha = i / len(trail)
                color = (int(40 * alpha), int(50 * alpha), int(60 * alpha))
                cv2.line(frame, 
                        (int(trail[i-1][0]), int(trail[i-1][1])),
                        (int(trail[i][0]), int(trail[i][1])),
                        color, 1)
            
            # Body
            cv2.circle(frame, (int(m.x), int(m.y)), 5, (60, 70, 80), -1)
            cv2.circle(frame, (int(m.x), int(m.y)), 5, (100, 110, 120), 1)
        
        # Draw DDA tracker boxes and predictions
        for result in self.dda_trackers.update(
            [(m.id, m.x, m.y, m.vx, m.vy) for m in self.swarm.mosquitos]):
            
            x, y = int(result['x']), int(result['y'])
            px, py = int(result['pred_x']), int(result['pred_y'])
            color = result['color']
            
            # Bounding box
            size = 16
            cv2.rectangle(frame, (x - size, y - size), (x + size, y + size), color, 2)
            
            # ID label
            cv2.putText(frame, f"T{result['id']}", (x - size, y - size - 5),
                       cv2.FONT_HERSHEY_PLAIN, 0.9, color, 1)
            
            # Prediction point
            cv2.circle(frame, (px, py), 6, (0, 255, 255), 2)
            
            # Prediction vector
            cv2.arrowedLine(frame, (x, y), (px, py), (0, 200, 255), 2, tipLength=0.3)
            
            # Mode indicator
            mode_color = (0, 255, 100) if result['mode'] == "TRACKING" else (0, 100, 255)
            cv2.circle(frame, (x + size - 4, y - size + 4), 4, mode_color, -1)
        
        # Draw death animations
        for m in self.swarm.dead_mosquitos:
            alpha = m.death_timer / 0.5
            radius = int(20 * (1 - alpha) + 5)
            color = (int(255 * alpha), int(100 * alpha), 0)
            cv2.circle(frame, (int(m.death_x), int(m.death_y)), radius, color, 2)
        
        # Draw laser shots
        for shot in self.dda_turret.active_shots:
            alpha = shot.timer / 0.15
            if shot.hit:
                color = (0, int(255 * alpha), int(255 * alpha))
                thickness = 3
            else:
                color = (0, 0, int(200 * alpha))
                thickness = 1
            
            cv2.line(frame,
                    (int(shot.start_x), int(shot.start_y)),
                    (int(shot.end_x), int(shot.end_y)),
                    color, thickness, cv2.LINE_AA)
            
            # Impact point
            cv2.circle(frame, (int(shot.end_x), int(shot.end_y)),
                      int(8 * alpha), color, -1)
        
        # Draw turret
        tx, ty = int(self.dda_turret.x), int(self.dda_turret.y)
        cv2.circle(frame, (tx, ty), 20, (50, 60, 70), -1)
        cv2.circle(frame, (tx, ty), 20, (100, 120, 140), 2)
        cv2.circle(frame, (tx, ty), 8, (0, 200, 255), -1)
        
        # Aim line
        cv2.line(frame, (tx, ty), 
                (int(self.dda_turret.aim_x), int(self.dda_turret.aim_y)),
                (0, 100, 150), 1, cv2.LINE_AA)
        
        # Draw particles
        self.particles.draw(frame)
        
        # Draw HUD
        self._draw_hud(frame)
        
        return frame
    
    def _draw_hud(self, frame):
        """Draw heads-up display"""
        
        # Stats panel - top left
        panel_h = 160 if self.comparison_mode else 120
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (280, panel_h), (15, 18, 25), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (10, 10), (280, panel_h), (50, 55, 65), 1)
        
        # Title
        cv2.putText(frame, "DDA TERMINATOR", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        
        # Stats
        y = 60
        cv2.putText(frame, f"KILLS: {self.kills}", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 150), 2)
        y += 25
        cv2.putText(frame, f"DDA Accuracy: {self.dda_turret.accuracy:.1f}%", (20, y),
                   cv2.FONT_HERSHEY_PLAIN, 1.2, (100, 255, 150), 1)
        y += 20
        cv2.putText(frame, f"Shots: {self.dda_turret.shots_fired} | Hits: {self.dda_turret.hits}",
                   (20, y), cv2.FONT_HERSHEY_PLAIN, 1.0, (150, 150, 150), 1)
        
        # Kalman comparison
        if self.comparison_mode and self.kalman_turret:
            y += 25
            cv2.putText(frame, f"Kalman Accuracy: {self.kalman_turret.accuracy:.1f}%", (20, y),
                       cv2.FONT_HERSHEY_PLAIN, 1.2, (150, 150, 255), 1)
            y += 20
            cv2.putText(frame, f"Shots: {self.kalman_turret.shots_fired} | Hits: {self.kalman_turret.hits}",
                       (20, y), cv2.FONT_HERSHEY_PLAIN, 1.0, (150, 150, 150), 1)
            
            # Improvement indicator
            if self.dda_turret.shots_fired > 10:
                diff = self.dda_turret.accuracy - self.kalman_turret.accuracy
                color = (0, 255, 100) if diff > 0 else (0, 100, 255)
                cv2.putText(frame, f"DDA: {diff:+.1f}%", (200, 35),
                           cv2.FONT_HERSHEY_PLAIN, 1.0, color, 1)
        
        # Mode indicators - top right
        mode_y = 30
        mode_x = self.width - 150
        
        if self.auto_fire:
            cv2.putText(frame, "AUTO FIRE", (mode_x, mode_y),
                       cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 255, 200), 1)
        
        if self.paused:
            cv2.putText(frame, "PAUSED", (self.width // 2 - 50, self.height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        # Difficulty indicator
        diff_colors = {
            "easy": (100, 255, 100),
            "medium": (100, 200, 255),
            "hard": (100, 100, 255),
            "nightmare": (100, 0, 255)
        }
        cv2.putText(frame, self.difficulty.upper(), (mode_x, mode_y + 25),
                   cv2.FONT_HERSHEY_PLAIN, 1.0, diff_colors.get(self.difficulty, (200,200,200)), 1)
    
    def _reset(self):
        """Reset simulation"""
        self.swarm = MosquitoSwarm(len(self.swarm.mosquitos), 
                                   self.width, self.height, self.difficulty)
        self.dda_trackers = TrackerManager("DDA", prediction_ms=60)
        self.dda_turret = LaserTurret(self.width // 2, self.height - 50, hit_radius=28)
        
        if self.comparison_mode:
            self.kalman_trackers = TrackerManager("Kalman", prediction_ms=60)
            self.kalman_turret = LaserTurret(self.width // 2, self.height - 50, hit_radius=28)
        
        self.particles = ParticleSystem()
        self.kills = 0
        self.frame_count = 0
        print("  🔄 Reset")
    
    def _toggle_comparison(self):
        """Toggle comparison mode"""
        self.comparison_mode = not self.comparison_mode
        if self.comparison_mode:
            self.kalman_trackers = TrackerManager("Kalman", prediction_ms=60)
            self.kalman_turret = LaserTurret(self.width // 2, self.height - 50, hit_radius=28)
        else:
            self.kalman_trackers = None
            self.kalman_turret = None
        print(f"  Comparison mode: {'ON' if self.comparison_mode else 'OFF'}")
    
    def _print_final_stats(self):
        """Print final statistics"""
        print("\n" + "═"*70)
        print("  FINAL RESULTS")
        print("═"*70)
        print(f"  Total Kills: {self.kills}")
        print(f"  Total Frames: {self.frame_count}")
        print(f"")
        print(f"  DDA Performance:")
        print(f"    Shots Fired: {self.dda_turret.shots_fired}")
        print(f"    Hits: {self.dda_turret.hits}")
        print(f"    Accuracy: {self.dda_turret.accuracy:.2f}%")
        
        if self.comparison_mode and self.kalman_turret:
            print(f"")
            print(f"  Kalman Performance:")
            print(f"    Shots Fired: {self.kalman_turret.shots_fired}")
            print(f"    Hits: {self.kalman_turret.hits}")
            print(f"    Accuracy: {self.kalman_turret.accuracy:.2f}%")
            
            if self.kalman_turret.accuracy > 0:
                improvement = ((self.dda_turret.accuracy - self.kalman_turret.accuracy) 
                              / self.kalman_turret.accuracy * 100)
                print(f"")
                print(f"  ╔═══════════════════════════════════════════════════╗")
                print(f"  ║  DDA OUTPERFORMS KALMAN BY: {improvement:+.1f}%            ║")
                print(f"  ╚═══════════════════════════════════════════════════╝")
        
        print("═"*70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DDA Mosquito Terminator")
    
    parser.add_argument('--swarm', type=int, default=15,
                       help='Number of mosquitos (default: 15)')
    parser.add_argument('--difficulty', type=str, default='medium',
                       choices=['easy', 'medium', 'hard', 'nightmare'])
    parser.add_argument('--compare', action='store_true',
                       help='Enable DDA vs Kalman comparison')
    parser.add_argument('--nightmare', action='store_true',
                       help='Nightmare difficulty')
    parser.add_argument('--auto', action='store_true', default=True,
                       help='Auto-fire mode (default: on)')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    
    args = parser.parse_args()
    
    difficulty = 'nightmare' if args.nightmare else args.difficulty
    
    terminator = DDATerminator(
        num_mosquitos=args.swarm,
        difficulty=difficulty,
        comparison_mode=args.compare,
        auto_fire=args.auto,
        width=args.width,
        height=args.height
    )
    
    terminator.run()
