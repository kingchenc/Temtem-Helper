import pyautogui
import time
import threading
import win32gui
import pywintypes
import numpy as np
import win32api
import cv2
from datetime import datetime
import os
import random
import mss
import mss.tools
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor
import json
import win32con
from config_manager import ConfigManager

class HighlightSignal(QObject):
    highlight = pyqtSignal(tuple)  # (x, y, w, h)

class HighlightWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.WindowTransparentForInput  # Allows clicks through the window
        )
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
    def show_highlight(self, pos):
        x, y, w, h = pos
        # Draw larger circle
        padding = 10
        self.setGeometry(x-padding, y-padding, w+padding*2, h+padding*2)
        self.show()
        # Use the configured duration from the bot
        if hasattr(self.parent(), 'highlight_duration'):
            duration = self.parent().highlight_duration
        else:
            duration = 750  # Fallback to default
        self.hide_timer.start(duration)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Brighter green circle with more opacity
        pen = QPen(QColor(0, 255, 0, 255))  # Full opacity
        pen.setWidth(3)  # Thicker line
        painter.setPen(pen)
        
        # Fill with semi-transparent green
        painter.setBrush(QColor(0, 255, 0, 50))
        
        # Draw the filled circle
        painter.drawEllipse(5, 5, self.width()-10, self.height()-10)

class AutoLeveler:
    def __init__(self):
        self.running = False
        self.battle_callback = None
        self.thread = None
        self.window_handle = None
        
        # Template storage - dynamic lists per type
        self.templates = {
            'map': [],
            'run': [],
            'bag': [],
            'kill': [],
            'chose': [],
            'overload': [],
            'died': []
        }
        
        # Initialize thread local storage
        self._thread_local = threading.local()
        
        # Initialize config manager first
        self.config = ConfigManager()
        
        # Initialize with values from config
        self.thresholds = {}
        profile = self.config.get_profile()
        if profile:
            self.thresholds = profile.get('thresholds', {}).copy()
            self.highlight_enabled = profile.get('show_highlight', True)
            self.highlight_duration = profile.get('highlight_duration', 750)
        else:
            self.highlight_enabled = True
            self.highlight_duration = 750
            
        # Get movement mode directly from config without triggering save
        self.movement_mode = self.config.get('movement_mode', 'both')
        
        # Rest of initialization
        self.last_state_change = time.time()
        self.current_state = "unknown"
        self.in_battle = False
        self.current_attack = 1
        self.attack_count = 0  # Counts how many times the current attack was used
        self.movement_direction = 0
        self.last_direction_change = time.time()
        self.pressed_keys = set()
        self.death_retry_count = 0
        
        # Highlight system
        self.highlight_signal = HighlightSignal()
        self.highlight_window = None
        
        # Create debug folder
        try:
            os.makedirs('debug', exist_ok=True)
        except Exception as e:
            msg = f"Could not create debug directory: {e}"
            print(msg)
            if hasattr(self, 'gui'):
                self.gui.add_log_entry(msg)
                
        # Load active profile settings
        self.load_thresholds()
        
    def load_thresholds(self):
        """Loads the threshold values from the config"""
        # Get active profile
        profile = self.config.get_profile()
        
        if profile:
            # Update thresholds from profile
            self.thresholds = profile.get('thresholds', {}).copy()
                    
            # Set highlight settings from profile
            self.highlight_enabled = profile.get('show_highlight', True)
            self.highlight_duration = profile.get('highlight_duration', 750)
            
            # Update profile label in GUI if it exists
            if hasattr(self, 'gui') and hasattr(self.gui, 'profile_label'):
                self.gui.profile_label.setText(self.config.get_active_profile())

    def save_thresholds(self):
        """Saves the threshold values to the config"""
        # Get current profile
        profile = self.config.get_profile()
        
        # Only save if values actually changed
        if (profile.get('show_highlight') != self.highlight_enabled or
            profile.get('highlight_duration') != self.highlight_duration or
            profile.get('thresholds') != self.thresholds):
            
            profile_data = {
                'show_highlight': self.highlight_enabled,
                'highlight_duration': self.highlight_duration,
                'thresholds': self.thresholds.copy()
            }
            self.config.set_profile(self.config.get_active_profile(), profile_data, save=True)

    def set_thresholds(self, thresholds):
        """Sets new threshold values"""
        self.thresholds.update(thresholds)
        self.save_thresholds()

    def set_movement_mode(self, mode):
        """Sets the movement mode (ad/sw/both)"""
        if self.movement_mode != mode:
            self.movement_mode = mode
            self.config.set('movement_mode', mode, save=True)

    def set_highlight_enabled(self, enabled):
        """Enables or disables the highlight system"""
        self.highlight_enabled = enabled
        if not enabled and self.highlight_window:
            self.highlight_window.hide()
        
        # Save setting through config manager
        self.config.save_highlight_setting(enabled)

    def set_highlight_duration(self, duration):
        """Sets the display duration of the highlight"""
        self.highlight_duration = duration
        if self.highlight_window:
            self.highlight_window.hide_timer.setInterval(duration)
        
        # Save setting through config manager
        self.config.save_highlight_duration(duration)

    def setup_highlight(self):
        """Initializes the highlight system in the main thread"""
        app = QApplication.instance()
        if app and self.highlight_window is None:
            self.highlight_window = HighlightWindow()
            self.highlight_signal.highlight.connect(
                self.highlight_window.show_highlight,
                type=Qt.QueuedConnection
            )

    def highlight_match(self, x, y, w, h):
        """Shows a green circle at the found position"""
        try:
            if not self.highlight_enabled:
                return
                
            if self.highlight_window is None:
                self.setup_highlight()
            if self.highlight_window:
                self.highlight_signal.highlight.emit((x, y, w, h))
        except Exception as e:
            print(f"Error showing highlight: {e}")

    def _ensure_mss(self):
        """Ensures MSS is initialized in the current thread"""
        if not hasattr(self._thread_local, 'sct'):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct

    def get_screen_coordinates(self, window_handle):
        """Gets the correct screen coordinates for a window, accounting for multiple monitors"""
        try:
            # Get the monitor info
            monitor = win32api.MonitorFromWindow(window_handle)
            monitor_info = win32api.GetMonitorInfo(monitor)
            monitor_area = monitor_info['Monitor']
            
            # Get the window rect
            window_rect = win32gui.GetWindowRect(window_handle)
            client_rect = win32gui.GetClientRect(window_handle)
            
            # Convert client coordinates to screen coordinates
            left, top = win32gui.ClientToScreen(window_handle, (0, 0))
            right, bottom = win32gui.ClientToScreen(window_handle, (client_rect[2], client_rect[3]))
            
            # Create monitor dict for MSS
            monitor = {
                "top": top,
                "left": left,
                "width": right - left,
                "height": bottom - top
            }
            
            return monitor
            
        except Exception as e:
            print(f"Error getting screen coordinates: {e}")
            return None
        
    def attach_to_window(self):
        """Finds and attaches to the Temtem window"""
        try:
            def window_enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    # Only search for the exact window title "Temtem"
                    if window_title == "Temtem":
                        print(f"Found Temtem game window")
                        results.append(hwnd)
                return True

            print("Searching for Temtem window...")
            results = []
            win32gui.EnumWindows(window_enum_callback, results)
            
            if results:
                self.window_handle = results[0]
                # Bring window to foreground
                try:
                    win32gui.ShowWindow(self.window_handle, 9)  # SW_RESTORE
                    win32gui.SetForegroundWindow(self.window_handle)
                except Exception as e:
                    print(f"Warning: Could not bring window to foreground: {e}")
                    
                # Verify window is valid
                try:
                    rect = win32gui.GetWindowRect(self.window_handle)
                    if rect[0] < -10000 or rect[1] < -10000 or rect[2] > 10000 or rect[3] > 10000:
                        print("Invalid window coordinates, trying next window...")
                        return False
                except:
                    print("Could not get window coordinates")
                    return False
                    
                print(f"Successfully attached to Temtem game window")
                return True
                
            print("No Temtem game window found")
            return False
            
        except pywintypes.error as e:
            print(f"Error searching for the Temtem window: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False
        
    def start(self, battle_callback=None):
        """Starts the Auto-Leveler
        
        Args:
            battle_callback: Function that is called when a battle is detected
        """
        self.running = True
        self.battle_callback = battle_callback
        
        # PyAutoGUI configuration
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        
        # Start thread
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stops the Auto-Leveler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)  # Wait a maximum of 1 second for the thread to end
            
        # Release all keys
        for key in ['a', 'd', 'w', 's']:  # Add all possible keys
            try:
                pyautogui.keyUp(key)
            except:
                pass
        
        # Reset all status variables
        self.in_battle = False
        self.current_state = "unknown"
        self.current_attack = 1
        self.attack_count = 0  # Counts how many times the current attack was used
        self.death_retry_count = 0
        
    def send_key_to_window(self, key, hold=False, release=False):
        """Sends a keystroke safely to the Temtem window
        
        Args:
            key: The key to send
            hold: Hold the key down
            release: Release the key
        """
        if not self.window_handle:
            return
            

        try:
            # Save the current active window
            current_window = win32gui.GetForegroundWindow()
            
            # Activate Temtem window
            win32gui.SetForegroundWindow(self.window_handle)
            time.sleep(0.03)
            
            # Send key
            if release:
                pyautogui.keyUp(key)
            elif hold:
                pyautogui.keyDown(key)
            else:
                pyautogui.press(key)
            
            # Restore the original window
            if current_window != self.window_handle:
                win32gui.SetForegroundWindow(current_window)
                
        except Exception as e:
            print(f"Error sending key: {e}")
            
    def handle_battle(self):
        """Handles battle actions"""
        # Check for death first
        if self.check_for_death():
            return

        # Check if we should still run
        if not self.running:
            return

        # Double check if we're really in battle (not on map)
        for template in self.templates['map']:
            if self.find_image_in_window(template['image']):
                msg = "On map - not executing battle action"
                print(msg)
                self.gui.add_log_entry(msg)
                return
            
        # Check if we can execute an action
        if not self.can_battle_action():
            msg = "Cannot execute battle action - waiting for battle UI..."
            print(msg)
            self.gui.add_log_entry(msg)
            # Wait up to 5 seconds for battle UI
            start_time = time.time()
            while time.time() - start_time < 5:
                # Check if we should still run
                if not self.running:
                    return

                # Check for chose button while waiting
                if self.check_for_chose():
                    msg = "Found and handled chose button"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    return
                    
                # Check if we can now execute an action and are not on map
                if self.can_battle_action():
                    map_visible = False
                    for template in self.templates['map']:
                        if self.find_image_in_window(template['image']):
                            map_visible = True
                            break
                    if not map_visible:
                        msg = "Battle UI visible - executing action"
                        print(msg)
                        self.gui.add_log_entry(msg)
                        break
                time.sleep(0.1)
            else:
                msg = "Battle UI not found after timeout"
                print(msg)
                self.gui.add_log_entry(msg)
                return

        # Check if we should still run
        if not self.running:
            return

        # Execute current attack
        msg = f"Battle action: pressing {self.current_attack} then f (Attack {self.attack_count + 1}/5)"
        print(msg)
        self.gui.add_log_entry(msg)
        self.send_key_to_window(str(self.current_attack))
        time.sleep(1.0)  # Longer pause after number

        # Check if we should still run
        if not self.running:
            return
        
        # Then F to confirm
        self.send_key_to_window('f')
        time.sleep(1.0)  # Longer pause after F for animation
        
        # Check if we should still run
        if not self.running:
            return

        # Wait and check for kill button
        self.check_for_kill()
        
        # Check if we should still run
        if not self.running:
            return

        # Increment attack counter
        self.attack_count += 1
        
        # Switch attack after 5 uses
        if self.attack_count >= 5:
            self.attack_count = 0  # Reset counter
            self.current_attack = 2 if self.current_attack == 1 else 1  # Switch attack
            msg = f"Switching to attack {self.current_attack} for next 5 turns"
            print(msg)
            self.gui.add_log_entry(msg)

        # Wait up to 5 seconds for next possible action
        msg = "Waiting for next possible action..."
        print(msg)
        self.gui.add_log_entry(msg)
        action_start = time.time()
        while time.time() - action_start < 5:  # Maximum 5 seconds wait
            # Check if we should still run
            if not self.running:
                return

            if self.can_battle_action():  # If Run or Bag is visible again
                msg = "Can execute next action"
                print(msg)
                self.gui.add_log_entry(msg)
                # Execute next action immediately
                self.handle_battle()
                return
            time.sleep(0.1)
        msg = "No next action possible yet"
        print(msg)
        self.gui.add_log_entry(msg)
        
    def _run(self):
        """Main bot loop"""
        # Initialize MSS in this thread
        sct = self._ensure_mss()
        
        horizontal_keys = ['a', 'd']  # Left/Right
        vertical_keys = ['s', 'w']    # Down/Up
        cnt = 0
        last_color = None
        last_state = None
        current_key = None  # Stores currently pressed key
        
        while self.running:
            try:
                # Check if we should still run
                if not self.running:
                    if current_key:  # Release current key
                        self.send_key_to_window(current_key, release=True)
                    break
                
                # Check status
                current_state = self.get_game_state()
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Status update when something changes
                if current_state != last_state:
                    if current_state == "map":
                        msg = "On map"
                        print(msg)
                        self.gui.add_log_entry(msg)
                    elif current_state == "battle":
                        msg = "In battle"
                        print(msg)
                        self.gui.add_log_entry(msg)
                        # Release all keys immediately when battle starts
                        if current_key:
                            self.send_key_to_window(current_key, release=True)
                            current_key = None
                        # Only execute battle action if we're really in battle
                        if self.can_battle_action():
                            # Check we're not on map
                            map_visible = False
                            for template in self.templates['map']:
                                if self.find_image_in_window(template['image']):
                                    map_visible = True
                                    break
                            if not map_visible:
                                self.handle_battle()
                    elif current_state == "died":
                        msg = "Died - attempting revival"
                        print(msg)
                        self.gui.add_log_entry(msg)
                        # Release all keys
                        if current_key:
                            self.send_key_to_window(current_key, release=True)
                            current_key = None
                        # Execute revival sequence
                        self.check_for_death()
                    elif current_state == "battle_loading":
                        msg = "Loading battle action..."
                        print(msg)
                        self.gui.add_log_entry(msg)
                    elif current_state == "loading":
                        msg = "Loading..."
                        print(msg)
                        self.gui.add_log_entry(msg)
                    else:
                        msg = "Status unknown"
                        print(msg)
                        self.gui.add_log_entry(msg)
                        # Release keys on unknown status too
                        if current_key:
                            self.send_key_to_window(current_key, release=True)
                            current_key = None
                    last_state = current_state
                    self.current_state = current_state
                
                # Continuous checks based on current state
                if current_state == "battle":
                    # Check we're not on map
                    map_visible = False
                    for template in self.templates['map']:
                        if self.find_image_in_window(template['image']):
                            map_visible = True
                            break
                    if not map_visible:
                        # Check for kill button first
                        if self.check_for_kill():
                            pass
                        # Then check if we can do a battle action
                        elif self.can_battle_action():
                            self.handle_battle()
                elif current_state == "died":
                    # Continuously try to revive
                    self.check_for_death()
                
                # Movement only when on map
                if current_state == "map":
                    # Change direction every 5-10 seconds in "both" mode
                    current_time = time.time()
                    if self.movement_mode == "both" and current_time - self.last_direction_change > random.uniform(5, 10):
                        self.movement_direction = random.randint(0, 1)  # Random horizontal or vertical
                        self.last_direction_change = current_time
                        if current_key:  # Release current key
                            self.send_key_to_window(current_key, release=True)
                            current_key = None
                    
                    # Choose key set based on movement mode
                    if self.movement_mode == "ad" or (self.movement_mode == "both" and self.movement_direction == 0):
                        keys = horizontal_keys
                    else:  # "sw" or (both and direction == 1)
                        keys = vertical_keys
                    
                    # Press new key
                    new_key = keys[cnt % 2]
                    if new_key != current_key:
                        if current_key:  # Release old key
                            self.send_key_to_window(current_key, release=True)
                        self.send_key_to_window(new_key, hold=True)
                        current_key = new_key
                        cnt += 1
                
                # Battle detection with relative coordinates
                try:
                    monitor = self.get_screen_coordinates(self.window_handle)
                    if monitor:
                        # Screenshot with MSS
                        screenshot = sct.grab(monitor)
                        
                        # Position for battle detection (95% width, 5% height)
                        pixel_x = int(monitor["width"] * 0.95)
                        pixel_y = int(monitor["height"] * 0.05)
                        
                        # Check color at position
                        color = screenshot.pixel(pixel_x, pixel_y)[:3]  # RGB without Alpha
                        
                        if last_color != color:
                            if color == (60, 232, 234):  # Battle ended
                                self.in_battle = False
                                msg = "Battle ended"
                                print(msg)
                                self.gui.add_log_entry(msg)
                                if self.battle_callback:
                                    self.battle_callback()
                            elif current_state == "unknown" and not self.in_battle:
                                self.in_battle = True
                                msg = "Battle started"
                                print(msg)
                                self.gui.add_log_entry(msg)
                                # Release keys immediately when battle is detected
                                if current_key:
                                    self.send_key_to_window(current_key, release=True)
                                    current_key = None
                        last_color = color
                except Exception as e:
                    msg = f"Error checking battle state: {e}"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    # Release keys on errors too
                    if current_key:
                        self.send_key_to_window(current_key, release=True)
                        current_key = None
                
                # Minimal delay for system stability
                time.sleep(0.01)
                
            except Exception as e:
                msg = f"Error: {str(e)}"
                print(msg)
                self.gui.add_log_entry(msg)
                # Release keys on errors too
                if current_key:
                    self.send_key_to_window(current_key, release=True)
                    current_key = None
                time.sleep(0.5)
                
    def get_game_state(self):
        """Gets the current game state"""
        try:
            # Check if we're on the map
            for template in self.templates['map']:
                if self.find_image_in_window(template['image']):
                    msg = "On map"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    self.in_battle = False
                    return "map"
                    
            # If map not found, check for all other states
            # Check for death first (highest priority)
            for template in self.templates['died']:
                if self.find_image_in_window(template['image']):
                    msg = f"Death detected ({template['name']})"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    return "died"
                    
            # Check for battle UI
            if self.can_battle_action():
                msg = "In battle"
                print(msg)
                self.gui.add_log_entry(msg)
                self.in_battle = True
                return "battle"
                
            # Check for kill button
            for template in self.templates['kill']:
                if self.find_image_in_window(template['image']):
                    msg = "Kill button detected"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    self.in_battle = True
                    return "battle"
                    
            # Check for chose button
            for template in self.templates['chose']:
                if self.find_image_in_window(template['image']):
                    msg = "Chose dialog detected"
               #     print(msg)
                    self.gui.add_log_entry(msg)
                    self.in_battle = True
                    # Handle the chose dialog
                    self.check_for_chose()
                    return "battle"
                    
            # Check for overload button
            for template in self.templates['overload']:
                if self.find_image_in_window(template['image']):
                    msg = "Overload dialog detected"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    self.in_battle = True
                    # Handle the overload dialog
                    self.check_for_overload()
                    return "battle"
                    
            # More detailed status for unknown state
            if self.in_battle:
                msg = "Loading battle..."
                print(msg)
                self.gui.add_log_entry(msg)
                return "battle_loading"
            
            # If no specific state found, return loading
            msg = "Loading..."
            print(msg)
            self.gui.add_log_entry(msg)
            return "loading"
            
        except Exception as e:
            msg = f"Error getting game state: {e}"
            print(msg)
            self.gui.add_log_entry(msg)
            return "error"
        
    def find_image_in_window(self, template_image):
        """Searches for the template image in the Temtem window using OpenCV"""
        if not self.window_handle:
            print("Not attached to Temtem window")
            return False
            
        try:
            # Get correct screen coordinates
            monitor = self.get_screen_coordinates(self.window_handle)
            if not monitor:
                return False
                
            try:
                # Capture window content using MSS
                sct = self._ensure_mss()
                screenshot = sct.grab(monitor)
                
                # Convert MSS screenshot to OpenCV format
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                template_cv = cv2.cvtColor(np.array(template_image), cv2.COLOR_RGB2BGR)
                
                # Template matching with TM_SQDIFF_NORMED (lower value means better match)
                result = cv2.matchTemplate(screenshot_cv, template_cv, cv2.TM_SQDIFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # Bei TM_SQDIFF_NORMED ist min_val der beste Match (0 = perfekt, 1 = keine Übereinstimmung)
                confidence = 1.0 - min_val
                
                # Find template type and name
                template_type = None
                template_name = None
                for t_type, templates in self.templates.items():
                    for template in templates:
                        if template['image'] is template_image:
                            template_type = t_type
                            template_name = template['name']
                            break
                    if template_type:
                        break
                
                # Get threshold based on template type
                threshold = self.thresholds.get(template_type, 0.95)  # Default to 0.95 if not found
                
                if confidence >= threshold:
                    # Calculate position of found template
                    h, w = template_cv.shape[:2]
                    x = min_loc[0] + monitor["left"]
                    y = min_loc[1] + monitor["top"]
                    
                    # Log the find with confidence
                    if hasattr(self, 'gui'):
                        self.gui.add_log_entry(f"{template_name} gefunden ({confidence:.2f})")
                    
                    # Show highlight
                    self.highlight_match(x, y, w, h)
                    return True
                return False
                    
            except Exception as e:
                import traceback
                msg = f"Screenshot/matching error: {str(e)}"
                print(msg)
                self.gui.add_log_entry(msg)
                print(traceback.format_exc())
                self.gui.add_log_entry(traceback.format_exc())
                return False
            
        except Exception as e:
            import traceback
            msg = f"Error during image recognition: {str(e)}"
            print(msg)
            self.gui.add_log_entry(msg)
            print("Full error:")
            print(traceback.format_exc())
            self.gui.add_log_entry("Full error:")
            self.gui.add_log_entry(traceback.format_exc())
            return False
        
    def set_templates(self, template_groups):
        """Sets templates for all types based on the template groups
        
        Args:
            template_groups: Dictionary with template types as keys and lists of template dicts as values
                           Each template dict should have 'name' and 'image' keys
        """
        # Clear existing templates
        self.templates = {
            'map': [],
            'run': [],
            'bag': [],
            'kill': [],
            'chose': [],
            'overload': [],
            'died': []
        }
        
        # Add new templates
        for template_type, templates in template_groups.items():
            if template_type in self.templates:
                self.templates[template_type].extend(templates)

    def can_battle_action(self):
        """Checks if we can take a battle action (Run or Bag button visible)"""
        # Check for run button
        for template in self.templates['run']:
            if self.find_image_in_window(template['image']):
                return True
        
        # Check for bag button
        for template in self.templates['bag']:
            if self.find_image_in_window(template['image']):
                return True
        
        return False
            
    def check_for_kill(self):
        """Checks if any kill button is visible"""
        if not self.running:
            return False
        
        for template in self.templates['kill']:
            if self.find_image_in_window(template['image']):
                if not self.running:
                    return False
                print("Kill button found - sending F")
                self.send_key_to_window('f')
                return True
        
        return False
           
    def check_for_chose(self):
        """Checks if the chose button is visible"""
        if not self.running:
            return False
        
        # Track chose dialogs in last 20 seconds
        current_time = time.time()
        if not hasattr(self, 'chose_detections'):
            self.chose_detections = []
        
        # Remove old detections
        self.chose_detections = [t for t in self.chose_detections if current_time - t < 20]
        
        for template in self.templates['chose']:
            if self.find_image_in_window(template['image']):
                if not self.running:
                    return False
                    
                # Add detection time
                self.chose_detections.append(current_time)
                msg = f"Chose dialog detected (Total in last 20s: {len(self.chose_detections)})"
                print(msg)
                self.gui.add_log_entry(msg)
                
                # If we detect too many chose dialogs in short time, something is stuck
                if len(self.chose_detections) >= 5:
                    msg = "Chose dialog stuck - using right-click fallback"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    
                    # Try right click up to 3 times
                    for attempt in range(3):
                        if self.send_mouse_click(right_click=True):
                            # Wait a bit and check if dialog is gone
                            time.sleep(0.5)
                            if not self.find_image_in_window(template['image']):
                                msg = "Fallback successful - dialog cleared"
                                print(msg)
                                self.gui.add_log_entry(msg)
                                self.chose_detections = []
                                return True
                            else:
                                msg = f"Fallback attempt {attempt + 1} failed - dialog still present"
                                print(msg)
                                self.gui.add_log_entry(msg)
                                time.sleep(0.5)  # Wait before next attempt
                    
                    msg = "All fallback attempts failed"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    return False
                
                # Normal case - try F key
                print("Chose button found - sending F")
                self.send_key_to_window('f')
                
                # Wait a bit and verify the dialog is gone
                time.sleep(0.5)
                if not self.find_image_in_window(template['image']):
                    msg = "F key successful - dialog cleared"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    return True
                else:
                    msg = "F key failed - dialog still present"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    return False
        
        return False
        
    def check_for_overload(self):
        """Checks if the overload button is visible"""
        if not self.running:
            return False
        
        for template in self.templates['overload']:
            if self.find_image_in_window(template['image']):
                if not self.running:
                    return False
                print("Overload button found - sending 6")
                self.send_key_to_window('6')
                return True
        
        return False
        
    def check_for_death(self):
        """Checks if the died screen is visible and handles it"""
        if not self.running:
            return False
        
        for template in self.templates['died']:
            if self.find_image_in_window(template['image']):
                if not self.running:
                    return False
                print("Death detected - attempting recovery")
                self.death_retry_count += 1
                
                # Try recovery sequence up to 5 times
                if self.death_retry_count <= 5:
                    print(f"Death recovery attempt {self.death_retry_count}/5")
                    self.gui.add_log_entry(f"Death recovery attempt {self.death_retry_count}/5")
                    # Press W then F
                    self.send_key_to_window('w')
                    if not self.running:
                        return False
                    time.sleep(0.2)
                    if not self.running:
                        return False
                    self.send_key_to_window('f')
                    time.sleep(0.2)
                    return True
                else:
                    msg = "Max death retries reached"
                    print(msg)
                    self.gui.add_log_entry(msg)
                    self.death_retry_count = 0
                    return False
        
        # Reset counter if we're not dead
        self.death_retry_count = 0
        return False
       
    def set_highlight_enabled(self, enabled):
        """Enables or disables the highlight system"""
        self.highlight_enabled = enabled
        if not enabled and self.highlight_window:
            self.highlight_window.hide()

    def set_highlight_duration(self, duration):
        """Sets the display duration of the highlight"""
        self.highlight_duration = duration
        if self.highlight_window:
            self.highlight_window.hide_timer.setInterval(duration)

    def send_mouse_click(self, right_click=False):
        """Sends a mouse click to the Temtem window
        
        Args:
            right_click: If True, sends right click instead of left click
        """
        try:
            if not self.window_handle:
                return False
                
            # Get window position
            monitor = self.get_screen_coordinates(self.window_handle)
            if not monitor:
                return False
                
            # Calculate center of window
            x = monitor["left"] + monitor["width"] // 2
            y = monitor["top"] + monitor["height"] // 2
            
            # Set cursor position
            win32api.SetCursorPos((x, y))
            
            # Send click
            if right_click:
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            
            return True
            
        except Exception as e:
            print(f"Error sending mouse click: {e}")
            return False

    def __del__(self):
        """Cleanup MSS when object is destroyed"""
        if hasattr(self._thread_local, 'sct'):
            self._thread_local.sct.close()
