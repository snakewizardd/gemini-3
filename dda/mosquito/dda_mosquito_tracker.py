"""
DDA MOSQUITO TRACKER v1.0
=========================
Real-time tracking of fast-moving targets (mosquitos, flies, etc.)
Uses DDA for prediction to compensate for system latency.

Requirements:
    pip install opencv-python numpy
    
For actual robot control, you'd add:
    pip install pyserial  # for Arduino/microcontroller
    # or
    pip install RPi.GPIO  # for Raspberry Pi
"""

import cv2
import numpy as np
import time
from collections import deque

# ═══════════════════════════════════════════════════════════════════════════════
# DDA TRACKER - 2D Version for X,Y coordinates
# ═══════════════════════════════════════════════════════════════════════════════
class DDATracker2D:
    """
    Tracks a target in 2D space using DDA algorithm.
    Provides smoothed position AND predicted future position.
    """
    
    def __init__(self, 
                 P0_stable=0.85,      # Smoothing during normal tracking
                 P0_saccade=0.1,      # Fast response during sudden moves
                 saccade_thresh=3.0,  # Threshold for "sudden move" detection
                 prediction_ms=50):   # How far ahead to predict (milliseconds)
        
        self.P0_stable = P0_stable
        self.P0_saccade = P0_saccade
        self.saccade_thresh = saccade_thresh
        self.prediction_ms = prediction_ms
        
        # State for X axis
        self.Fx = None  # Filtered X position
        self.Fy = None  # Filtered Y position
        
        # History for velocity estimation
        self.history_x = deque(maxlen=10)
        self.history_y = deque(maxlen=10)
        self.timestamps = deque(maxlen=10)
        
        # Volatility tracking
        self.volatility_x = 1.0
        self.volatility_y = 1.0
        
        # State
        self.mode = "ACQUIRING"  # ACQUIRING, TRACKING, SACCADE
        self.frames_tracked = 0
        self.last_seen = 0
        
    def update(self, x, y, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        
        if self.Fx is None:
            self.Fx = x
            self.Fy = y
            self.history_x.append(x)
            self.history_y.append(y)
            self.timestamps.append(timestamp)
            self.mode = "ACQUIRING"
            self.last_seen = timestamp
            return self._make_result(x, y, 0, 0)
        
        error_x = abs(x - self.Fx)
        error_y = abs(y - self.Fy)
        
        if len(self.history_x) >= 5:
            self.volatility_x = max(1.0, np.std(list(self.history_x)[-5:]))
            self.volatility_y = max(1.0, np.std(list(self.history_y)[-5:]))
        
        saccade_x = error_x > (self.saccade_thresh * self.volatility_x)
        saccade_y = error_y > (self.saccade_thresh * self.volatility_y)
        is_saccade = saccade_x or saccade_y
        
        if is_saccade:
            P0 = self.P0_saccade
            self.mode = "SACCADE"
        else:
            P0 = self.P0_stable
            self.mode = "TRACKING"
        
        velocity_x, velocity_y = self._estimate_velocity(timestamp)
        
        dt = timestamp - self.timestamps[-1] if self.timestamps else 0.016
        boost_x = 0.3 * velocity_x * dt
        boost_y = 0.3 * velocity_y * dt
        
        self.Fx = P0 * self.Fx + (1 - P0) * (x + boost_x)
        self.Fy = P0 * self.Fy + (1 - P0) * (y + boost_y)
        
        self.history_x.append(x)
        self.history_y.append(y)
        self.timestamps.append(timestamp)
        self.frames_tracked += 1
        self.last_seen = timestamp
        
        return self._make_result(self.Fx, self.Fy, velocity_x, velocity_y)
    
    def _estimate_velocity(self, current_time):
        if len(self.history_x) < 2:
            return 0, 0
        
        n = min(5, len(self.history_x))
        
        dx = self.history_x[-1] - self.history_x[-n]
        dy = self.history_y[-1] - self.history_y[-n]
        dt = self.timestamps[-1] - self.timestamps[-n]
        
        if dt > 0:
            vx = dx / dt
            vy = dy / dt
        else:
            vx, vy = 0, 0
        
        return vx, vy
    
    def _make_result(self, fx, fy, vx, vy):
        dt_predict = self.prediction_ms / 1000.0
        pred_x = fx + vx * dt_predict
        pred_y = fy + vy * dt_predict
        
        return {
            'filtered_x': fx,
            'filtered_y': fy,
            'predicted_x': pred_x,
            'predicted_y': pred_y,
            'velocity_x': vx,
            'velocity_y': vy,
            'speed': np.sqrt(vx**2 + vy**2),
            'mode': self.mode,
            'frames_tracked': self.frames_tracked
        }
    
    def predict_position(self, ms_ahead):
        if self.Fx is None:
            return None, None
        
        vx, vy = self._estimate_velocity(time.time())
        dt = ms_ahead / 1000.0
        
        pred_x = self.Fx + vx * dt
        pred_y = self.Fy + vy * dt
        
        return pred_x, pred_y
    
    def is_tracking(self, timeout_ms=500):
        if self.Fx is None:
            return False
        return (time.time() - self.last_seen) * 1000 < timeout_ms
    
    def reset(self):
        self.Fx = None
        self.Fy = None
        self.history_x.clear()
        self.history_y.clear()
        self.timestamps.clear()
        self.mode = "ACQUIRING"
        self.frames_tracked = 0


class MosquitoDetector:
    def __init__(self, min_area=10, max_area=500):
        self.min_area = min_area
        self.max_area = max_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=50, detectShadows=False)
        
    def detect(self, frame):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        fg_mask = self.bg_subtractor.apply(gray)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area <= area <= self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2
                detections.append((cx, cy, w, h, area))
        
        return detections, fg_mask


class RobotController:
    def __init__(self):
        self.armed = False
    def move_to(self, x, y, speed=1.0):
        raise NotImplementedError
    def strike(self):
        raise NotImplementedError
    def home(self):
        raise NotImplementedError
    def arm(self):
        self.armed = True
    def disarm(self):
        self.armed = False


class SimulatedRobot(RobotController):
    def __init__(self):
        super().__init__()
        self.position = (320, 240)
        self.target = None
        
    def move_to(self, x, y, speed=1.0):
        self.target = (x, y)
        
    def get_position(self):
        if self.target:
            dx = self.target[0] - self.position[0]
            dy = self.target[1] - self.position[1]
            new_x = self.position[0] + dx * 0.2
            new_y = self.position[1] + dy * 0.2
            self.position = (new_x, new_y)
        return self.position
    
    def strike(self):
        print("🎯 STRIKE!")
        return True
    
    def home(self):
        self.target = (320, 240)


class MosquitoHunter:
    def __init__(self, camera_id=0, robot=None):
        self.camera = cv2.VideoCapture(camera_id)
        self.camera.set(cv2.CAP_PROP_FPS, 60)
        
        self.detector = MosquitoDetector()
        self.tracker = DDATracker2D(
            P0_stable=0.8, P0_saccade=0.1, saccade_thresh=4.0, prediction_ms=80)
        self.robot = robot or SimulatedRobot()
        self.strike_distance = 30
        self.min_tracking_frames = 10
        self.total_detections = 0
        self.total_strikes = 0
        self.successful_strikes = 0
        
    def run(self, display=True):
        print("\n" + "="*60)
        print("  🦟 MOSQUITO HUNTER ACTIVE")
        print("="*60)
        print("  Press 'q' to quit, 'r' to reset, 'a' to arm/disarm")
        print("="*60 + "\n")
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                break
            
            timestamp = time.time()
            detections, mask = self.detector.detect(frame)
            self.total_detections += len(detections)
            
            track_result = None
            if detections:
                best = max(detections, key=lambda d: d[4])
                cx, cy = best[0], best[1]
                track_result = self.tracker.update(cx, cy, timestamp)
            
            if track_result and self.tracker.is_tracking():
                pred_x = track_result['predicted_x']
                pred_y = track_result['predicted_y']
                self.robot.move_to(pred_x, pred_y)
                
                if self.robot.armed and track_result['frames_tracked'] >= self.min_tracking_frames:
                    robot_pos = self.robot.get_position()
                    dist = np.sqrt((robot_pos[0] - pred_x)**2 + (robot_pos[1] - pred_y)**2)
                    if dist < self.strike_distance:
                        self.robot.strike()
                        self.total_strikes += 1
                        self.tracker.reset()
            
            if display:
                vis = self._draw_visualization(frame, detections, track_result, mask)
                cv2.imshow('Mosquito Hunter', vis)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.tracker.reset()
            elif key == ord('a'):
                if self.robot.armed:
                    self.robot.disarm()
                else:
                    self.robot.arm()
        
        self.camera.release()
        cv2.destroyAllWindows()
    
    def _draw_visualization(self, frame, detections, track_result, mask):
        vis = frame.copy()
        for det in detections:
            cx, cy, w, h, area = det
            cv2.rectangle(vis, (cx - w//2, cy - h//2), (cx + w//2, cy + h//2), (0, 255, 255), 1)
        
        if track_result:
            fx, fy = int(track_result['filtered_x']), int(track_result['filtered_y'])
            px, py = int(track_result['predicted_x']), int(track_result['predicted_y'])
            cv2.circle(vis, (fx, fy), 8, (0, 255, 0), 2)
            cv2.circle(vis, (px, py), 10, (0, 0, 255), 2)
            cv2.arrowedLine(vis, (fx, fy), (px, py), (255, 0, 255), 2)
            robot_pos = self.robot.get_position()
            rx, ry = int(robot_pos[0]), int(robot_pos[1])
            cv2.drawMarker(vis, (rx, ry), (255, 255, 0), cv2.MARKER_CROSS, 20, 2)
            
            info = [f"Mode: {track_result['mode']}", f"Speed: {track_result['speed']:.1f} px/s",
                    f"Frames: {track_result['frames_tracked']}", f"Armed: {'YES' if self.robot.armed else 'NO'}"]
            for i, text in enumerate(info):
                cv2.putText(vis, text, (10, 25 + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        mask_small = cv2.resize(mask, (160, 120))
        vis[0:120, 0:160] = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        return vis


if __name__ == "__main__":
    import sys
    camera_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hunter = MosquitoHunter(camera_id=camera_id)
    hunter.run(display=True)
