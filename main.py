import cv2  
import mediapipe as mp  
import time
import subprocess
from pathlib import Path
import sys
from pushbullet import Pushbullet
import os
import numpy as np
from collections import deque

# ============================================
# 🔧 FIX FOR PYINSTALLER - MUST BE AT THE VERY TOP
# ============================================
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = sys._MEIPASS
    os.environ['MEDIAPIPE_MODEL_PATH'] = os.path.join(base_path, 'mediapipe')
    
    # Critical fix for MediaPipe paths
    import mediapipe as mp
    # Store original path
    original_path = mp.__path__[0]
    # Redirect to temp folder
    mp.__path__ = [os.path.join(base_path, 'mediapipe')]
    
    # Also fix the solution_base module
    try:
        from mediapipe.python import solution_base
        if hasattr(solution_base, '__path__'):
            solution_base.__path__ = [os.path.join(base_path, 'mediapipe', 'python')]
    except:
        pass
    
    print(f"📦 Running in packaged mode. Base path: {base_path}")
else:
    # Running as script
    base_path = os.path.abspath(".")
    print(f"💻 Running in development mode. Base path: {base_path}")

# ============================================
# ⚙️ CONFIGURATION - EDIT ONLY THIS SECTION!
# ============================================
PUSHBULLET_API_KEY = os.environ.get("PUSHBULLET_API_KEY", "").strip() or None

# Video settings
TIMER_DURATION = 2.0  # Seconds before punishment

# Detection settings - Auto-calibrated, but these are fallbacks
LOOKING_DOWN_THRESHOLD = 0.25  # Will be auto-calibrated
DEBOUNCE_THRESHOLD = 0.45      # More forgiving during punishment

# Accuracy settings
USE_CALIBRATION = True          # Auto-calibrate for your face
SMOOTHING_FRAMES = 7            # Frames to average (higher = smoother but slower)
HEAD_POSE_CHECK = True          # Check head position to avoid false positives
USE_MULTI_METRIC = True         # Use multiple eye measurements
MIN_CONFIDENCE = 0.2            # Minimum confidence for detection
CALIBRATION_SAMPLES = 50        # Number of frames to collect during calibration
# ============================================

def get_base_path():
    """Get the base path whether running as script or exe"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(".")

def get_assets_folder():
    """Get or create assets folder"""
    base = get_base_path()
    assets_path = os.path.join(base, "assets")
    
    # Create if missing
    if not os.path.exists(assets_path):
        try:
            os.makedirs(assets_path)
            print(f"📁 Created 'assets' folder at: {assets_path}")
        except:
            pass
    
    return assets_path

def find_punishment_video():
    """Find any MP4 video in assets folder"""
    assets_path = get_assets_folder()
    
    if not os.path.exists(assets_path):
        return None
    
    mp4_files = [f for f in os.listdir(assets_path) if f.lower().endswith(".mp4")]
    
    if not mp4_files:
        return None
    
    return os.path.join(assets_path, mp4_files[0])

class DoomscrollDetector:
    def __init__(self, pushbullet_api_key=None):
        print("🚀 Initializing Doomscroll Blocker with Enhanced Accuracy...")
        
        # Print paths for debugging
        if getattr(sys, 'frozen', False):
            print(f"📦 Temp path: {sys._MEIPASS}")
            print(f"📁 Assets will be saved to: {get_base_path()}")
        
        # MediaPipe face mesh with maximum accuracy settings
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            refine_landmarks=True,           # For iris tracking
            max_num_faces=1,
            min_detection_confidence=0.7,    # Higher confidence threshold
            min_tracking_confidence=0.7,      # Better tracking
            static_image_mode=False
        )
        
        # Timer settings
        self.timer = TIMER_DURATION
        self.looking_down_threshold = LOOKING_DOWN_THRESHOLD
        self.debounce_threshold = DEBOUNCE_THRESHOLD
        
        # Video path
        video_file = find_punishment_video()
        if video_file:
            self.video_path = Path(video_file)
            print(f"🎬 Found video: {self.video_path.name}")
        else:
            self.video_path = None
            print("⚠️ No video found in assets folder")
            print(f"📁 Please put an MP4 file in: {get_assets_folder()}")
        
        # State tracking
        self.doomscroll = None
        self.video_playing = False
        self.video_process = None
        self.last_notification_time = 0
        self.notification_cooldown = 10
        
        # ACCURACY IMPROVEMENTS
        
        # 1. Smoothing buffer
        self.eye_ratio_history = deque(maxlen=SMOOTHING_FRAMES)
        self.eye_ratio_confidence = deque(maxlen=SMOOTHING_FRAMES)
        
        # 2. Head pose tracking
        self.head_pose_history = deque(maxlen=10)
        self.calibrated_head_level = None
        
        # 3. Performance tracking
        self.false_positive_count = 0
        self.true_positive_count = 0
        
        # 4. Adaptive threshold
        self.current_threshold = self.looking_down_threshold
        self.threshold_history = deque(maxlen=20)
        
        # Pushbullet setup
        self.use_pushbullet = bool(pushbullet_api_key) and pushbullet_api_key != "YOUR_API_KEY_HERE"
        if self.use_pushbullet:
            try:
                print("📱 Connecting to Pushbullet...")
                self.pb = Pushbullet(pushbullet_api_key)
                devices = self.pb.devices
                print(f"✅ Connected to Pushbullet! ({len(devices)} devices)")
                
                self.send_phone_notification(
                    "📱 Doomscroll Blocker Connected",
                    "Enhanced accuracy mode active!"
                )
            except Exception as e:
                print(f"❌ Pushbullet connection failed: {e}")
                self.use_pushbullet = False
        
        # Platform detection
        self.is_windows = sys.platform == 'win32'
        self.is_mac = sys.platform == 'darwin'
        
        print("🎯 Ready to track eyes with enhanced accuracy!")
    
    def calculate_eye_ratio_advanced(self, landmarks):
        """Calculate eye ratio using multiple metrics for maximum accuracy"""
        points = landmarks.landmark
        
        # Get all relevant landmarks
        # Left eye
        left_eye_top = points[159]      # Upper eyelid
        left_eye_bottom = points[145]    # Lower eyelid
        left_eye_outer = points[33]      # Outer corner
        left_eye_inner = points[133]     # Inner corner
        
        # Right eye
        right_eye_top = points[386]
        right_eye_bottom = points[374]
        right_eye_outer = points[263]
        right_eye_inner = points[362]
        
        # Iris centers
        l_iris = points[468]
        r_iris = points[473]
        
        # Additional iris points for better accuracy
        l_iris_left = points[469]
        l_iris_right = points[470]
        r_iris_left = points[474]
        r_iris_right = points[475]
        
        # Calculate eye openness
        left_eye_openness = abs(left_eye_top.y - left_eye_bottom.y)
        right_eye_openness = abs(right_eye_top.y - right_eye_bottom.y)
        
        # METRIC 1: Iris vertical position relative to eye socket
        l_ratio1 = (l_iris.y - left_eye_bottom.y) / (left_eye_top.y - left_eye_bottom.y + 1e-6)
        r_ratio1 = (r_iris.y - right_eye_bottom.y) / (right_eye_top.y - right_eye_bottom.y + 1e-6)
        
        # METRIC 2: Distance from top of eye
        l_ratio2 = 1.0 - (left_eye_top.y - l_iris.y) / (left_eye_top.y - left_eye_bottom.y + 1e-6)
        r_ratio2 = 1.0 - (right_eye_top.y - r_iris.y) / (right_eye_top.y - right_eye_bottom.y + 1e-6)
        
        # METRIC 3: Iris diameter ratio (smaller when looking down due to perspective)
        l_iris_diameter = abs(l_iris_left.x - l_iris_right.x)
        r_iris_diameter = abs(r_iris_left.x - r_iris_right.x)
        left_eye_width = abs(left_eye_outer.x - left_eye_inner.x)
        right_eye_width = abs(right_eye_outer.x - right_eye_inner.x)
        
        l_ratio3 = l_iris_diameter / (left_eye_width + 1e-6)
        r_ratio3 = r_iris_diameter / (right_eye_width + 1e-6)
        
        # METRIC 4: Iris position relative to eye corners (for side glances)
        l_ratio4 = (l_iris.x - left_eye_inner.x) / (left_eye_width + 1e-6)
        r_ratio4 = (r_iris.x - right_eye_inner.x) / (right_eye_width + 1e-6)
        
        # Combine all metrics with weighted average
        # Give more weight to vertical measurements (ratios 1 and 2)
        weights = [0.3, 0.3, 0.2, 0.2]  # Total = 1.0
        
        left_combined = (l_ratio1 * weights[0] + l_ratio2 * weights[1] + 
                        l_ratio3 * weights[2] + (1.0 - abs(l_ratio4 - 0.5) * 2) * weights[3])
        
        right_combined = (r_ratio1 * weights[0] + r_ratio2 * weights[1] + 
                         r_ratio3 * weights[2] + (1.0 - abs(r_ratio4 - 0.5) * 2) * weights[3])
        
        # Calculate confidence based on eye openness and symmetry
        left_confidence = min(1.0, left_eye_openness * 10)
        right_confidence = min(1.0, right_eye_openness * 10)
        
        # Average both eyes with confidence weighting
        total_confidence = left_confidence + right_confidence
        if total_confidence > 0:
            eye_ratio = (left_combined * left_confidence + right_combined * right_confidence) / total_confidence
            confidence = (left_confidence + right_confidence) / 2
        else:
            eye_ratio = (left_combined + right_combined) / 2
            confidence = 0.1
        
        return eye_ratio, confidence
    
    def calculate_head_pose(self, landmarks):
        """Calculate head pose to filter false positives"""
        points = landmarks.landmark
        
        # Key points
        nose_tip = points[1]
        chin = points[152]
        forehead = points[10]
        left_eye = points[33]
        right_eye = points[263]
        left_ear = points[234]
        right_ear = points[454]
        
        # Vertical head angle (looking up/down)
        head_vertical = (nose_tip.y - chin.y) / (forehead.y - chin.y + 1e-6)
        
        # Horizontal head angle (looking left/right)
        eye_center_x = (left_eye.x + right_eye.x) / 2
        head_horizontal = (nose_tip.x - eye_center_x) / (right_ear.x - left_ear.x + 1e-6)
        
        # Head tilt
        head_tilt = abs(left_eye.y - right_eye.y)
        
        # Check if head is turned significantly
        head_turned = abs(head_horizontal) > 0.1
        
        # Check if looking too far up/down (false positive)
        extreme_vertical = abs(head_vertical) > 0.3
        
        return {
            'vertical': head_vertical,
            'horizontal': head_horizontal,
            'tilt': head_tilt,
            'turned': head_turned,
            'extreme': extreme_vertical
        }
    
    def calibrate(self, cam):
        """Auto-calibrate thresholds for current user"""
        print("\n📏 AUTO-CALIBRATION MODE")
        print("=" * 50)
        print("Step 1: Look STRAIGHT AHEAD at the screen")
        print("Keep your normal posture for 3 seconds...")
        
        straight_samples = []
        straight_confidences = []
        
        for i in range(CALIBRATION_SAMPLES):
            ret, frame = cam.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)
                
                if results and results.multi_face_landmarks:
                    eye_ratio, confidence = self.calculate_eye_ratio_advanced(results.multi_face_landmarks[0])
                    if confidence > MIN_CONFIDENCE:
                        straight_samples.append(eye_ratio)
                        straight_confidences.append(confidence)
                        
                        # Show progress
                        progress = int((i / CALIBRATION_SAMPLES) * 30)
                        bar = "█" * progress + "░" * (30 - progress)
                        print(f"\r[{bar}] {int((i/CALIBRATION_SAMPLES)*100)}%", end="")
            
            time.sleep(0.03)  # ~30fps sampling
        
        print("\n\nStep 2: Look DOWN at your phone")
        print("Keep looking down for 3 seconds...")
        
        down_samples = []
        down_confidences = []
        
        for i in range(CALIBRATION_SAMPLES):
            ret, frame = cam.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)
                
                if results and results.multi_face_landmarks:
                    eye_ratio, confidence = self.calculate_eye_ratio_advanced(results.multi_face_landmarks[0])
                    if confidence > MIN_CONFIDENCE:
                        down_samples.append(eye_ratio)
                        down_confidences.append(confidence)
                        
                        progress = int((i / CALIBRATION_SAMPLES) * 30)
                        bar = "█" * progress + "░" * (30 - progress)
                        print(f"\r[{bar}] {int((i/CALIBRATION_SAMPLES)*100)}%", end="")
            
            time.sleep(0.03)
        
        print("\n\n📊 CALIBRATION RESULTS:")
        print("=" * 50)
        
        if straight_samples and down_samples:
            # Calculate weighted averages
            avg_straight = np.average(straight_samples, weights=straight_confidences)
            avg_down = np.average(down_samples, weights=down_confidences)
            
            # Calculate standard deviations
            std_straight = np.std(straight_samples)
            std_down = np.std(down_samples)
            
            # Set threshold optimally (midpoint minus a bias)
            # Bias slightly toward straight to reduce false positives
            bias = 0.1 * (avg_straight - avg_down)
            calibrated_threshold = (avg_straight + avg_down) / 2 - bias
            
            # Calculate separation quality
            separation = (avg_straight - avg_down) / (std_straight + std_down + 1e-6)
            
            print(f"Looking straight: {avg_straight:.3f} ± {std_straight:.3f}")
            print(f"Looking down:     {avg_down:.3f} ± {std_down:.3f}")
            print(f"Separation quality: {separation:.2f} (higher is better)")
            print(f"Recommended threshold: {calibrated_threshold:.3f}")
            
            if separation > 2.0:
                print("✅ Excellent separation! Detection will be very accurate.")
            elif separation > 1.0:
                print("👍 Good separation. Detection should work well.")
            else:
                print("⚠️ Poor separation. Try adjusting lighting or camera position.")
            
            return calibrated_threshold
        
        print("⚠️ Calibration failed. Using default threshold.")
        return self.looking_down_threshold
    
    def send_phone_notification(self, title, message):
        """Send notification to phone via Pushbullet"""
        if not self.use_pushbullet:
            return
        
        current_time = time.time()
        if current_time - self.last_notification_time < self.notification_cooldown:
            return
        
        try:
            self.pb.push_note(title, message)
            self.last_notification_time = current_time
            print(f"📤 Sent: {title}")
        except Exception as e:
            print(f"❌ Notification failed: {e}")
    
    def play_video(self):
        """Play punishment video"""
        if not self.video_path or not self.video_path.exists():
            print(f"❌ Video not found")
            return
        
        absolute_path = str(self.video_path)
        
        try:
            if self.is_mac:
                script = f'''
                tell application "QuickTime Player"
                    activate
                    try
                        close every document
                    end try
                    open POSIX file "{absolute_path}"
                    play front document
                end tell
                '''
                self.video_process = subprocess.Popen(
                    ["osascript", "-e", script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif self.is_windows:
                players = [
                    ["C:\\Program Files\\VideoLAN\\VLC\\vlc.exe", 
                     "--fullscreen", "--video-on-top", "--play-and-exit", absolute_path],
                    ["C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
                     "--fullscreen", "--play-and-exit", absolute_path],
                    ["wmplayer", absolute_path]
                ]
                
                for player in players:
                    try:
                        self.video_process = subprocess.Popen(
                            player,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        print(f"▶️ Playing with: {player[0]}")
                        break
                    except:
                        continue
                
                if not self.video_process:
                    os.startfile(absolute_path)
                    print("▶️ Opening with default player")
            
            self.video_playing = True
            print("🎬 PUNISHMENT VIDEO PLAYING!")
            
            self.send_phone_notification(
                "⚠️ DOOMSCROLLING DETECTED!",
                f"Punishment video playing! Look up now!"
            )
            
        except Exception as e:
            print(f"❌ Error playing video: {e}")
    
    def close_video(self):
        """Stop punishment video"""
        if self.video_playing:
            print("🛑 Stopping video...")
            
            if self.video_process:
                try:
                    self.video_process.terminate()
                    self.video_process.wait(timeout=1)
                except:
                    try:
                        self.video_process.kill()
                    except:
                        pass
            
            if self.is_mac:
                script = '''
                tell application "QuickTime Player"
                    if (count of documents) > 0 then
                        close front document saving no
                    end if
                end tell
                '''
                subprocess.run(["osascript", "-e", script], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self.is_windows:
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "vlc.exe", "/T"], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
            
            self.video_playing = False
            self.video_process = None
            
            self.send_phone_notification(
                "✅ BACK TO WORK!",
                "Good job! You're looking up again."
            )
    
    def draw_ui_advanced(self, frame, eye_ratio, confidence, head_pose, timer_active, timer_progress):
        """Draw enhanced UI with accuracy metrics"""
        h, w = frame.shape[:2]
        
        # Status bar
        status_bar_height = 120  # Taller for more info
        cv2.rectangle(frame, (0, 0), (w, status_bar_height), (40, 40, 40), -1)
        cv2.rectangle(frame, (0, status_bar_height), (w, status_bar_height), (80, 80, 80), 2)
        
        # Status text
        if self.video_playing:
            status = "⚠️ PUNISHMENT ACTIVE!"
            color = (0, 0, 255)
        elif timer_active:
            status = "⚠️ Looking down!"
            color = (0, 165, 255)
        else:
            status = "✅ Good posture!"
            color = (0, 255, 0)
        
        cv2.putText(frame, status, (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)
        
        # Eye ratio with confidence
        if eye_ratio is not None:
            threshold = self.current_threshold
            ratio_color = (0, 255, 0) if eye_ratio > threshold else (0, 0, 255)
            
            cv2.putText(frame, f"Eye Ratio: {eye_ratio:.3f}", (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, ratio_color, 2)
            
            # Confidence bar
            bar_x, bar_y = 20, 80
            bar_width = 200
            bar_height = 10
            
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                         (50, 50, 50), -1)
            conf_width = int(bar_width * confidence)
            conf_color = (0, 255, 0) if confidence > 0.7 else (0, 255, 255) if confidence > 0.4 else (0, 0, 255)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + conf_width, bar_y + bar_height),
                         conf_color, -1)
            
            cv2.putText(frame, f"Conf: {confidence:.2f}", (230, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Head pose info
        if head_pose and HEAD_POSE_CHECK:
            head_status = ""
            head_color = (255, 255, 255)
            
            if head_pose['extreme']:
                head_status = "Head tilted - check posture"
                head_color = (0, 165, 255)
            elif head_pose['turned']:
                head_status = "Head turned - face camera"
                head_color = (255, 255, 0)
            else:
                head_status = "Good head position"
                head_color = (0, 255, 0)
            
            cv2.putText(frame, head_status, (20, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, head_color, 1)
        
        # Timer progress
        if timer_active:
            bar_width = 300
            bar_height = 25
            bar_x = w - bar_width - 20
            bar_y = 25
            
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                         (50, 50, 50), -1)
            
            progress_width = int(bar_width * timer_progress)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height),
                         (0, 0, 255), -1)
            
            # Border
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                         (200, 200, 200), 1)
            
            time_left = self.timer * (1 - timer_progress)
            cv2.putText(frame, f"{time_left:.1f}s", (bar_x + bar_width + 10, bar_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Phone status
        phone_status = "📱 Connected" if self.use_pushbullet else "📱 Not connected"
        phone_color = (0, 255, 255) if self.use_pushbullet else (100, 100, 100)
        cv2.putText(frame, phone_status, (w - 200, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, phone_color, 1)
        
        # Instructions
        cv2.putText(frame, "Q:Quit T:Test R:Reset C:Recalibrate", 
                   (w//2 - 200, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run(self):
        """Main camera loop with enhanced accuracy"""
        # Check video
        if not self.video_path or not self.video_path.exists():
            print(f"\n❌ ERROR: No video found in assets folder!")
            print(f"📁 Please put an MP4 file in: {get_assets_folder()}")
            input("Press Enter to exit...")
            return
        
        # Open webcam
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            print("❌ ERROR: Could not open webcam")
            input("Press Enter to exit...")
            return
        
        # Auto-calibrate if enabled
        if USE_CALIBRATION:
            self.current_threshold = self.calibrate(cam)
            self.looking_down_threshold = self.current_threshold
        else:
            self.current_threshold = self.looking_down_threshold
        
        print("\n" + "="*60)
        print("🚀 DOOMSCROLL BLOCKER - ENHANCED ACCURACY EDITION")
        print("="*60)
        print(f"📱 Phone notifications: {'✅' if self.use_pushbullet else '❌'}")
        print(f"🎯 Detection threshold: {self.current_threshold:.3f}")
        print(f"🔄 Smoothing frames: {SMOOTHING_FRAMES}")
        print(f"📊 Multi-metric: {'✅' if USE_MULTI_METRIC else '❌'}")
        print(f"👤 Head pose check: {'✅' if HEAD_POSE_CHECK else '❌'}")
        print(f"🎬 Video: {self.video_path.name}")
        print("="*60)
        print("\nControls: Q=Quit, T=Test notification, R=Reset, C=Recalibrate")
        print("\nStarting in 3 seconds...")
        time.sleep(3)
        
        try:
            while True:
                ret, frame = cam.read()
                if not ret:
                    print("❌ Camera error")
                    break
                
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]  # Get dimensions at start of loop
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)
                
                current_time = time.time()
                
                if results and results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0]
                    
                    # Calculate advanced metrics
                    eye_ratio, confidence = self.calculate_eye_ratio_advanced(landmarks)
                    
                    # Add to history for smoothing
                    if confidence > MIN_CONFIDENCE:
                        self.eye_ratio_history.append(eye_ratio)
                        self.eye_ratio_confidence.append(confidence)
                    
                    # Get smoothed value
                    if len(self.eye_ratio_history) > 0:
                        # Weighted average by confidence
                        weights = list(self.eye_ratio_confidence)
                        weights = [w / sum(weights) for w in weights]
                        smoothed_ratio = np.average(self.eye_ratio_history, weights=weights)
                    else:
                        smoothed_ratio = eye_ratio
                    
                    # Calculate head pose
                    head_pose = self.calculate_head_pose(landmarks) if HEAD_POSE_CHECK else None
                    
                    # Determine if looking down
                    is_looking_down = False
                    
                    if self.video_playing:
                        # More forgiving during punishment
                        is_looking_down = smoothed_ratio < self.debounce_threshold
                    else:
                        # Normal mode with head pose validation
                        is_looking_down = smoothed_ratio < self.current_threshold
                        
                        if HEAD_POSE_CHECK and head_pose:
                            # If head is turned or tilted, might be false positive
                            if head_pose['turned'] or head_pose['extreme']:
                                # Require stronger evidence
                                is_looking_down = is_looking_down and smoothed_ratio < (self.current_threshold * 0.8)
                    
                    # Timer logic
                    timer_active = False
                    timer_progress = 0.0
                    
                    if is_looking_down and confidence > MIN_CONFIDENCE:
                        if self.doomscroll is None:
                            self.doomscroll = current_time
                            print(f"👀 Looking down! Ratio: {smoothed_ratio:.3f}")
                        
                        elapsed = current_time - self.doomscroll
                        timer_progress = min(elapsed / self.timer, 1.0)
                        timer_active = True
                        
                        if elapsed >= self.timer and not self.video_playing:
                            self.play_video()
                            self.true_positive_count += 1
                    else:
                        if self.doomscroll is not None:
                            print(f"✅ Looking up! Ratio: {smoothed_ratio:.3f}")
                            self.doomscroll = None
                            
                            # If we were in timer but not punishment, might be false positive
                            if timer_active and not self.video_playing:
                                self.false_positive_count += 1
                        
                        if self.video_playing:
                            self.close_video()
                    
                    # Draw enhanced UI
                    frame = self.draw_ui_advanced(frame, smoothed_ratio, confidence, 
                                                 head_pose, timer_active, timer_progress)
                
                else:
                    # No face detected
                    self.doomscroll = None
                    if self.video_playing:
                        self.close_video()
                    
                    # Now w and h are defined
                    cv2.putText(frame, "No face detected - Adjust camera", 
                               (w//2 - 200, h//2),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                # Show frame
                cv2.imshow('Doomscroll Blocker - Enhanced Accuracy', frame)
                
                # Handle keys
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:
                    print("\n🛑 Quitting...")
                    break
                elif key == ord('t'):
                    if self.use_pushbullet:
                        self.send_phone_notification("📱 Test Notification", 
                                                    "Your Doomscroll Blocker is working!")
                    else:
                        print("❌ Phone notifications not enabled!")
                elif key == ord('r'):
                    self.doomscroll = None
                    print("🔄 Timer reset")
                elif key == ord('c'):
                    print("📏 Recalibrating...")
                    new_threshold = self.calibrate(cam)
                    if new_threshold:
                        self.current_threshold = new_threshold
                        self.looking_down_threshold = new_threshold
                        print(f"✅ New threshold: {new_threshold:.3f}")
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user (Ctrl+C)")
        
        finally:
            # Cleanup
            if self.video_playing:
                self.close_video()
            
            cam.release()
            cv2.destroyAllWindows()
            
            # Show stats
            print("\n📊 ACCURACY STATISTICS")
            print("="*50)
            total = self.true_positive_count + self.false_positive_count
            if total > 0:
                accuracy = (self.true_positive_count / total) * 100
                print(f"True positives: {self.true_positive_count}")
                print(f"False positives: {self.false_positive_count}")
                print(f"Accuracy: {accuracy:.1f}%")
            else:
                print("No detection events recorded")
            
            if self.use_pushbullet:
                try:
                    self.send_phone_notification("👋 Doomscroll Blocker Offline", 
                                                "Eye tracking has been stopped.")
                except:
                    pass
            
            print("\n👋 Goodbye! Stay productive!")


def main():
    print("\n" + "⭐"*60)
    print("DOOMSCROLL BLOCKER - ENHANCED ACCURACY EDITION")
    print("⭐"*60)
    
    # Check dependencies
    try:
        import numpy as np
    except ImportError:
        print("\n❌ Missing numpy! Please install:")
        print("pip install numpy")
        input("Press Enter to exit...")
        return
    
    # Notifications are optional; never embed a token in source or builds.
    if not PUSHBULLET_API_KEY or PUSHBULLET_API_KEY == "YOUR_API_KEY_HERE":
        print("Phone notifications disabled. Set PUSHBULLET_API_KEY to enable them.")
        detector = DoomscrollDetector()
    else:
        detector = DoomscrollDetector(PUSHBULLET_API_KEY)

    # Run the detector
    detector.run()


if __name__ == '__main__':
    # Check all dependencies
    missing = []
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    try:
        import mediapipe as mp
    except ImportError:
        missing.append("mediapipe")
    
    try:
        from pushbullet import Pushbullet
    except ImportError:
        missing.append("pushbullet.py")
    
    try:
        import numpy as np
    except ImportError:
        missing.append("numpy")
    
    if missing:
        print("\n❌ Missing dependencies!")
        print("Please install the following packages:")
        for pkg in missing:
            print(f"  pip install {pkg}")
        input("\nPress Enter to exit...")
        exit(1)
    
    main()