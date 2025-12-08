
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
        """
        Update tracker with new observation.
        
        Args:
            x, y: Observed position (pixels)
            timestamp: Time of observation (seconds). If None, uses current time.
            
        Returns:
            dict with:
                - filtered_x, filtered_y: Smoothed current position
                - predicted_x, predicted_y: Where target will be in prediction_ms
                - velocity_x, velocity_y: Estimated velocity (pixels/sec)
                - mode: Current tracking mode
        """
        if timestamp is None:
            timestamp = time.time()
        
        # First observation - initialize
        if self.Fx is None:
            self.Fx = x
            self.Fy = y
            self.history_x.append(x)
            self.history_y.append(y)
            self.timestamps.append(timestamp)
            self.mode = "ACQUIRING"
            self.last_seen = timestamp
            return self._make_result(x, y, 0, 0)
        
        # Calculate errors
        error_x = abs(x - self.Fx)
        error_y = abs(y - self.Fy)
        
        # Update volatility estimates
        if len(self.history_x) >= 5:
            self.volatility_x = max(1.0, np.std(list(self.history_x)[-5:]))
            self.volatility_y = max(1.0, np.std(list(self.history_y)[-5:]))
        
        # Detect saccade (sudden movement)
        saccade_x = error_x > (self.saccade_thresh * self.volatility_x)
        saccade_y = error_y > (self.saccade_thresh * self.volatility_y)
        is_saccade = saccade_x or saccade_y
        
        # Choose smoothing factor based on mode
        if is_saccade:
            P0 = self.P0_saccade  # Fast response
            self.mode = "SACCADE"
        else:
            P0 = self.P0_stable   # Smooth tracking
            self.mode = "TRACKING"
        
        # Calculate velocity (for prediction)
        velocity_x, velocity_y = self._estimate_velocity(timestamp)
        
        # Apply DDA filter with derivative boost
        dt = timestamp - self.timestamps[-1] if self.timestamps else 0.016
        boost_x = 0.3 * velocity_x * dt  # Predictive component
        boost_y = 0.3 * velocity_y * dt
        
        # Update filtered position
        self.Fx = P0 * self.Fx + (1 - P0) * (x + boost_x)
        self.Fy = P0 * self.Fy + (1 - P0) * (y + boost_y)
        
        # Store history
        self.history_x.append(x)
        self.history_y.append(y)
        self.timestamps.append(timestamp)
        self.frames_tracked += 1
        self.last_seen = timestamp
        
        return self._make_result(self.Fx, self.Fy, velocity_x, velocity_y)
    
    def _estimate_velocity(self, current_time):
        """Estimate current velocity from recent history"""
        if len(self.history_x) < 2:
            return 0, 0
        
        # Use last few points for velocity estimation
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
        """Create result dictionary with predictions"""
        # Predict future position
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
        """Predict where target will be in ms_ahead milliseconds"""
        if self.Fx is None:
            return None, None
        
        vx, vy = self._estimate_velocity(time.time())
        dt = ms_ahead / 1000.0
        
        pred_x = self.Fx + vx * dt
        pred_y = self.Fy + vy * dt
        
        return pred_x, pred_y
    
    def is_tracking(self, timeout_ms=500):
        """Check if we're actively tracking (seen target recently)"""
        if self.Fx is None:
            return False
        return (time.time() - self.last_seen) * 1000 < timeout_ms
    
    def reset(self):
        """Reset tracker state"""
        self.Fx = None
        self.Fy = None
        self.history_x.clear()
        self.history_y.clear()
        self.timestamps.clear()
        self.mode = "ACQUIRING"
        self.frames_tracked = 0


# ═══════════════════════════════════════════════════════════════════════════════
# MOSQUITO DETECTOR - Simple blob detection
# ═══════════════════════════════════════════════════════════════════════════════
class MosquitoDetector:
    """
    Detects small dark objects (mosquitos) against lighter background.
    Uses background subtraction + blob detection.
    """
    
    def __init__(self, min_area=10, max_area=500):
        self.min_area = min_area
        self.max_area = max_area
        
        # Background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100,
            varThreshold=50,
            detectShadows=False
        )
        
    def detect(self, frame):
        """
        Detect mosquito candidates in frame.
        
        Returns:
            List of (x, y, w, h, area) for each detection
        """
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(gray)
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
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


# ═══════════════════════════════════════════════════════════════════════════════
# ROBOT CONTROLLER INTERFACE (Abstract - implement for your hardware)
# ═══════════════════════════════════════════════════════════════════════════════
class RobotController:
    """
    Abstract interface for robot control.
    Implement this for your specific hardware.
    """
    
    def __init__(self):
        self.armed = False
        
    def move_to(self, x, y, speed=1.0):
        """Move end effector to position (x, y)"""
        raise NotImplementedError
    
    def strike(self):
        """Execute strike/capture action"""
        raise NotImplementedError
    
    def home(self):
        """Return to home position"""
        raise NotImplementedError
    
    def arm(self):
        """Arm the system"""
        self.armed = True
    
    def disarm(self):
        """Disarm the system"""
        self.armed = False


class SimulatedRobot(RobotController):
    """Simulated robot for testing"""
    
    def __init__(self):
        super().__init__()
        self.position = (320, 240)  # Start at center
        self.target = None
        
    def move_to(self, x, y, speed=1.0):
        # Simulate movement with some lag
        self.target = (x, y)
        # In real implementation, this would send commands to motors
        
    def get_position(self):
        # Simulate gradual movement toward target
        if self.target:
            dx = self.target[0] - self.position[0]
            dy = self.target[1] - self.position[1]
            # Move 20% of distance per call (simulates motor response)
            new_x = self.position[0] + dx * 0.2
            new_y = self.position[1] + dy * 0.2
            self.position = (new_x, new_y)
        return self.position
    
    def strike(self):
        print("🎯 STRIKE!")
        return True
    
    def home(self):
        self.target = (320, 240)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TRACKING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
class MosquitoHunter:
    """
    Complete mosquito tracking and interception system.
    """
    
    def __init__(self, camera_id=0, robot=None):
        self.camera = cv2.VideoCapture(camera_id)
        self.camera.set(cv2.CAP_PROP_FPS, 60)  # Request 60fps if available
        
        self.detector = MosquitoDetector()
        self.tracker = DDATracker2D(
            P0_stable=0.8,
            P0_saccade=0.1,
            saccade_thresh=4.0,
            prediction_ms=80  # Predict 80ms ahead (compensate for system latency)
        )
        
        self.robot = robot or SimulatedRobot()
        
        # Strike parameters
        self.strike_distance = 30  # pixels - how close before striking
        self.min_tracking_frames = 10  # Need this many frames before striking
        
        # Stats
        self.total_detections = 0
        self.total_strikes = 0
        self.successful_strikes = 0
        
    def run(self, display=True):
        """Main tracking loop"""
        
        print("\n" + "="*60)
        print("  🦟 MOSQUITO HUNTER ACTIVE")
        print("="*60)
        print("  Press 'q' to quit")
        print("  Press 'r' to reset tracker")
        print("  Press 'a' to arm/disarm")
        print("="*60 + "\n")
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                break
            
            timestamp = time.time()
            
            # Detect mosquitos
            detections, mask = self.detector.detect(frame)
            self.total_detections += len(detections)
            
            # Track the largest/closest detection
            track_result = None
            if detections:
                # Pick the largest detection
                best = max(detections, key=lambda d: d[4])
                cx, cy = best[0], best[1]
                
                # Update tracker
                track_result = self.tracker.update(cx, cy, timestamp)
            
            # Robot control
            if track_result and self.tracker.is_tracking():
                # Move robot to PREDICTED position (not current!)
                pred_x = track_result['predicted_x']
                pred_y = track_result['predicted_y']
                
                self.robot.move_to(pred_x, pred_y)
                
                # Check if we can strike
                if self.robot.armed and track_result['frames_tracked'] >= self.min_tracking_frames:
                    robot_pos = self.robot.get_position()
                    dist = np.sqrt((robot_pos[0] - pred_x)**2 + (robot_pos[1] - pred_y)**2)
                    
                    if dist < self.strike_distance:
                        self.robot.strike()
                        self.total_strikes += 1
                        self.tracker.reset()  # Reset after strike
            
            # Visualization
            if display:
                vis = self._draw_visualization(frame, detections, track_result, mask)
                cv2.imshow('Mosquito Hunter', vis)
            
            # Key handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.tracker.reset()
                print("  🔄 Tracker reset")
            elif key == ord('a'):
                if self.robot.armed:
                    self.robot.disarm()
                    print("  🔓 System DISARMED")
                else:
                    self.robot.arm()
                    print("  🔒 System ARMED")
        
        self.camera.release()
        cv2.destroyAllWindows()
        
        self._print_stats()
    
    def _draw_visualization(self, frame, detections, track_result, mask):
        """Draw tracking visualization"""
        vis = frame.copy()
        
        # Draw all detections
        for det in detections:
            cx, cy, w, h, area = det
            cv2.rectangle(vis, (cx - w//2, cy - h//2), (cx + w//2, cy + h//2), (0, 255, 255), 1)
        
        # Draw tracking info
        if track_result:
            fx, fy = int(track_result['filtered_x']), int(track_result['filtered_y'])
            px, py = int(track_result['predicted_x']), int(track_result['predicted_y'])
            
            # Filtered position (where it is NOW)
            cv2.circle(vis, (fx, fy), 8, (0, 255, 0), 2)
            cv2.putText(vis, "NOW", (fx + 10, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Predicted position (where it WILL BE)
            cv2.circle(vis, (px, py), 10, (0, 0, 255), 2)
            cv2.putText(vis, "PRED", (px + 10, py), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            # Velocity vector
            cv2.arrowedLine(vis, (fx, fy), (px, py), (255, 0, 255), 2)
            
            # Robot position
            robot_pos = self.robot.get_position()
            rx, ry = int(robot_pos[0]), int(robot_pos[1])
            cv2.drawMarker(vis, (rx, ry), (255, 255, 0), cv2.MARKER_CROSS, 20, 2)
            
            # Info panel
            info = [
                f"Mode: {track_result['mode']}",
                f"Speed: {track_result['speed']:.1f} px/s",
                f"Frames: {track_result['frames_tracked']}",
                f"Armed: {'YES' if self.robot.armed else 'NO'}"
            ]
            for i, text in enumerate(info):
                cv2.putText(vis, text, (10, 25 + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw mask in corner
        mask_small = cv2.resize(mask, (160, 120))
        mask_color = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        vis[0:120, 0:160] = mask_color
        
        return vis
    
    def _print_stats(self):
        print("\n" + "="*60)
        print("  📊 SESSION STATS")
        print("="*60)
        print(f"  Total detections: {self.total_detections}")
        print(f"  Strike attempts:  {self.total_strikes}")
        print("="*60 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    
    # Camera ID (0 = default webcam, 1 = USB camera, etc.)
    camera_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    # Create and run the hunter
    hunter = MosquitoHunter(camera_id=camera_id)
    hunter.run(display=True)
