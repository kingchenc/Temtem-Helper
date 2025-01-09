import sys
import subprocess
import json
import os
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QWidget, QLabel, QGroupBox, QComboBox, QMessageBox,
                           QFileDialog, QRadioButton, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
from autolevel import AutoLeveler
import win32api
import win32gui

class AutoLevelGUI(QMainWindow):
    # Signal for log updates
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.battle_count = 0
        self.start_time = None
        self.first_start_time = None  # Stores the very first start time
        self.total_runtime = 0  # Stores the total runtime
        self.loading_movement_mode = False  # Flag to block events during loading
        self.bot = AutoLeveler()
        self.bot.gui = self  # Set GUI reference in bot
        self.images = {}  # Dictionary to store loaded images
        self.settings_window = None  # Stores reference to settings window
        
        # Log system
        self.log_entries = []  # List for last 15 logs
        self.max_logs = 100  # Maximum number of logs
        
        # Connect log signal
        self.log_signal.connect(self._add_log_entry)
        
        # Initialize highlight system
        self.bot.setup_highlight()
        
        self.load_images()  # Load images at startup
        
        # Group templates by type
        template_groups = {}
        for filename, image in self.images.items():
            # Only process filenames with extension
            if not any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                continue
                
            # Extract template type from filename
            base_name = os.path.splitext(filename.lower())[0]  # Remove file extension correctly
            template_type = ''.join(c for c in base_name if not c.isdigit())
            template_type = template_type.rstrip('_')  # Remove trailing underscores
            
            if template_type not in template_groups:
                template_groups[template_type] = []
                
            template_groups[template_type].append({
                'name': filename,
                'image': image
            })
        
        # Set templates in bot
        self.bot.set_templates(template_groups)
        
        # Set up print redirection
        sys.stdout = self
        
        # Set window icon
        try:
            from PyQt5.QtGui import QIcon, QPixmap
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'logo.jpg')
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    self.setWindowIcon(QIcon(pixmap))
                    # Set taskbar icon for Windows
                    import ctypes
                    myappid = 'temtem.bot.v1'  # Arbitrary string
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                else:
                    print("Failed to load icon: Pixmap is null")
            else:
                print(f"Icon file not found at {icon_path}")
        except Exception as e:
            print(f"Error setting icon: {str(e)}")
        
        self.initUI()
        
        # Load saved settings
        self.load_movement_mode()  # Load saved movement direction
        
        # Set active profile in GUI
        active_profile = self.bot.config.get_active_profile()
        if active_profile:
            self.profile_label.setText(active_profile)
        
        # Timer for auto-attach at startup
        QTimer.singleShot(0, self.try_auto_attach)
        
    def load_images(self):
        """Loads all images from the img folder"""
        self.images = {}
        img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
        msg = f"Loading images from directory: {img_dir}"
        print(msg)
        self.add_log_entry(msg)
        
        if not os.path.exists(img_dir):
            msg = f"Warning: Image directory {img_dir} does not exist!"
            print(msg)
            self.add_log_entry(msg)
            return
            
        for filename in os.listdir(img_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img_path = os.path.join(img_dir, filename)
                    # Load image and convert to RGB to ensure consistency
                    image = Image.open(img_path).convert('RGB')
                    # Store only with the full filename (including extension)
                    self.images[filename] = image
                    msg = f"Loaded image: {filename}"
                    print(msg)
                    self.add_log_entry(msg)
                except Exception as e:
                    msg = f"Error loading image {filename}: {str(e)}"
                    print(msg)
                    self.add_log_entry(msg)
                    
        msg = f"Total images loaded: {len(self.images)}"
        print(msg)
        self.add_log_entry(msg)
        msg = f"Available image keys: {list(self.images.keys())}"
        print(msg)
        self.add_log_entry(msg)
        
    def initUI(self):
        # Main window settings
        self.setWindowTitle('Temtem Bot')
        self.setFixedSize(250, 666)  # +40px height for settings button
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # Remove standard title bar
        self.setAttribute(Qt.WA_TranslucentBackground)  # Enable transparent background
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main container with border and rounded corners
        container = QWidget()
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Custom title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setObjectName("TitleBar")
        title_bar.setStyleSheet("""
            QWidget#TitleBar {
                background-color: #323232;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 5, 0)
        title_layout.setSpacing(0)
        
        # Title text
        title_label = QLabel('Temtem Bot')
        title_label.setStyleSheet("color: #e0e0e0; background: transparent;")
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Close Button
        close_button = QPushButton('✕')
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("CloseButton")
        close_button.setStyleSheet("""
            QPushButton#CloseButton {
                background-color: transparent;
                color: #e0e0e0;
                border: none;
                font-size: 14px;
                padding: 0;
                margin: 0;
                border-top-right-radius: 8px;
            }
            QPushButton#CloseButton:hover {
                background-color: #cc3333;
            }
        """)
        close_button.clicked.connect(self.close)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_button)
        
        # Content Layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # Style for content widgets
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: #e0e0e0;
                background-color: #323232;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 3px 0px 3px;
                background-color: #323232;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }
            QRadioButton {
                color: #e0e0e0;
                spacing: 4px;
                background: transparent;
            }
            QRadioButton::indicator {
                width: 10px;
                height: 10px;
            }
            QRadioButton::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QRadioButton::indicator:checked {
                background-color: #cc7832;  /* Orange instead of blue */
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QRadioButton:disabled {
                color: #666666;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox::down-arrow:disabled {
                image: none;
                border: none;
            }
            QMessageBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                min-width: 80px;
            }
            QFileDialog {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QFileDialog QLabel {
                color: #e0e0e0;
            }
        """)

        # Add title bar and content to container
        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)
        
        # Add container to main layout
        main_layout.addWidget(container)

        # Enable window movement
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent
        self.drag_pos = None

        # Font for better readability
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        
        value_font = QFont()
        value_font.setPointSize(9)

        # From here add all widgets to content_layout instead of layout

        # Movement Group
        movement_group = QGroupBox("Movement")
        movement_group.setFont(title_font)
        movement_group.setFixedHeight(100)  # Set fixed height for the entire group
        movement_layout = QVBoxLayout()
        
        # Radio Buttons for movement direction
        self.move_ad = QRadioButton("Only Left/Right (A/D)")
        self.move_sw = QRadioButton("Only Up/Down (S/W)")
        self.move_both = QRadioButton("Both Directions")
        self.move_both.setChecked(True)  # Default: Both directions
        
        # Connect radio buttons to actions
        self.move_ad.toggled.connect(lambda: self.on_movement_changed("ad"))
        self.move_sw.toggled.connect(lambda: self.on_movement_changed("sw"))
        self.move_both.toggled.connect(lambda: self.on_movement_changed("both"))
        
        movement_layout.addWidget(self.move_ad)
        movement_layout.addWidget(self.move_sw)
        movement_layout.addWidget(self.move_both)
        
        movement_group.setLayout(movement_layout)
        content_layout.addWidget(movement_group)
        
        # Mode Group
        modus_group = QGroupBox("Mode")
        modus_group.setFont(title_font)
        modus_group.setFixedHeight(60)  # Set fixed height for the entire group
        modus_layout = QVBoxLayout()
        modus_layout.setContentsMargins(4, 4, 4, 8)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto Level")
        self.mode_combo.setFont(value_font)
        modus_layout.addWidget(self.mode_combo)
        
        modus_group.setLayout(modus_layout)
        content_layout.addWidget(modus_group)
        
        # Statistics Group
        stats_group = QGroupBox("Statistics")
        stats_group.setFont(title_font)
        stats_layout = QVBoxLayout()
        
        # Timer (horizontal)
        timer_row = QWidget()
        timer_layout = QHBoxLayout(timer_row)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        
        timer_title = QLabel("Runtime:")
        timer_title.setFont(title_font)
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(value_font)
        self.timer_label.setAlignment(Qt.AlignRight)
        
        timer_layout.addWidget(timer_title)
        timer_layout.addWidget(self.timer_label)
        stats_layout.addWidget(timer_row)
        
        # Battle counter (horizontal)
        battles_row = QWidget()
        battles_layout = QHBoxLayout(battles_row)
        battles_layout.setContentsMargins(0, 0, 0, 0)
        
        battles_title = QLabel("Battles:")
        battles_title.setFont(title_font)
        self.battle_label = QLabel("0")
        self.battle_label.setFont(value_font)
        self.battle_label.setAlignment(Qt.AlignRight)
        
        battles_layout.addWidget(battles_title)
        battles_layout.addWidget(self.battle_label)
        stats_layout.addWidget(battles_row)
        
        # Battles per hour (horizontal)
        bph_row = QWidget()
        bph_layout = QHBoxLayout(bph_row)
        bph_layout.setContentsMargins(0, 0, 0, 0)
        
        bph_title = QLabel("Battles per hour:")
        bph_title.setFont(title_font)
        self.battles_per_hour_label = QLabel("0.0")
        self.battles_per_hour_label.setFont(value_font)
        self.battles_per_hour_label.setAlignment(Qt.AlignRight)
        
        bph_layout.addWidget(bph_title)
        bph_layout.addWidget(self.battles_per_hour_label)
        stats_layout.addWidget(bph_row)
        
        # Monitor Label
        monitor_row = QWidget()
        monitor_layout = QHBoxLayout(monitor_row)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        
        monitor_title = QLabel("Monitor:")
        monitor_title.setFont(title_font)
        self.monitor_label = QLabel("Not connected")
        self.monitor_label.setFont(value_font)
        self.monitor_label.setAlignment(Qt.AlignRight)
        
        monitor_layout.addWidget(monitor_title)
        monitor_layout.addWidget(self.monitor_label)
        stats_layout.addWidget(monitor_row)
        
        # Profile Label
        profile_row = QWidget()
        profile_layout = QHBoxLayout(profile_row)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        
        profile_title = QLabel("Profile:")
        profile_title.setFont(title_font)
        self.profile_label = QLabel("Default")
        self.profile_label.setFont(value_font)
        self.profile_label.setAlignment(Qt.AlignRight)
        
        profile_layout.addWidget(profile_title)
        profile_layout.addWidget(self.profile_label)
        stats_layout.addWidget(profile_row)
        
        stats_group.setLayout(stats_layout)
        content_layout.addWidget(stats_group)
        
        # Control Group
        control_group = QGroupBox("Controls")
        control_group.setFont(title_font)
        control_layout = QVBoxLayout()
        
        # The buttons
        self.start_button = QPushButton('Start')
        self.start_button.setFont(value_font)
        self.start_button.clicked.connect(self.toggle_bot)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton('Stop')
        self.stop_button.setFont(value_font)
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.attach_button = QPushButton('Attach to Temtem')
        self.attach_button.setFont(value_font)
        self.attach_button.clicked.connect(self.attach_to_temtem)
        control_layout.addWidget(self.attach_button)
        
        self.settings_button = QPushButton('Settings')
        self.settings_button.setFont(value_font)
        self.settings_button.clicked.connect(self.show_settings)
        control_layout.addWidget(self.settings_button)
        
        control_group.setLayout(control_layout)
        content_layout.addWidget(control_group)
        
        # Status Group
        status_group = QGroupBox("Status")
        status_group.setFont(title_font)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(0)  # No spacing between elements
        status_layout.setContentsMargins(4, 8, 4, 4)  # Adjusted inner margins
        
        # Status Label (horizontal)
        status_row = QWidget()
        status_layout_row = QHBoxLayout(status_row)
        status_layout_row.setContentsMargins(0, 0, 0, 0)
        status_layout_row.setSpacing(2)  # Minimal spacing between status and value
        
        status_title = QLabel("Status:")
        status_title.setFont(title_font)
        self.status_label = QLabel("Ready")
        self.status_label.setFont(value_font)
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        status_layout_row.addWidget(status_title)
        status_layout_row.addWidget(self.status_label)
        status_layout_row.addStretch()
        
        # Print messages label directly under status
        self.print_label = QLabel("")
        self.print_label.setFont(QFont("", 8))  # Smaller font for print messages
        self.print_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.print_label.setWordWrap(True)
        self.print_label.setContentsMargins(15, 10, 0, 0)  # Indentation from left
        self.print_label.setMinimumWidth(200)
        
        # Add status and print to status layout
        status_layout.addWidget(status_row)
        status_layout.addWidget(self.print_label)
        status_layout.addStretch()  # Add stretch at the end
        
        status_group.setLayout(status_layout)
        content_layout.addWidget(status_group)
        
        # Timer for statistics updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)
        
        self.show()
    
    def update_stats(self):
        """Updates the statistics display"""
        if not self.bot.running:
            self.status_label.setText("Stopped")
            if self.start_time:  # When stopped, add the last runtime to total time
                self.total_runtime += (datetime.now() - self.start_time).total_seconds()
                self.start_time = None
            return
            
        # Update Timer
        if self.start_time:
            current_runtime = self.total_runtime + (datetime.now() - self.start_time).total_seconds()
            hours = int(current_runtime // 3600)
            minutes = int((current_runtime % 3600) // 60)
            seconds = int(current_runtime % 60)
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Update battles per hour
            hours_total = current_runtime / 3600.0
            if hours_total > 0:
                battles_per_hour = self.battle_count / hours_total
                self.battles_per_hour_label.setText(f"{battles_per_hour:.1f}")
        
        # Detailed status without timestamp
        if self.bot.current_state == "map":
            self.set_status_text("On map")
        elif self.bot.in_battle:
            self.set_status_text("In battle")
        elif self.bot.current_state == "unknown":
            self.set_status_text("Unknown")
        elif self.bot.current_state == "error":
            self.set_status_text("Error")
    
    def set_status_text(self, text):
        """Sets the status text and removes line breaks"""
        # Remove all line breaks and multiple spaces
        text = ' '.join(text.split())
        self.status_label.setText(text)
    
    def toggle_bot(self):
        if not self.bot.running:
            self.start_bot()
        else:
            self.stop_bot()
    
    def start_bot(self):
        if not self.bot.running:
            # Try to attach if not already attached
            if not self.bot.window_handle:
                self.attach_to_temtem()
                if not self.bot.window_handle:
                    return
            else:
                self.dock_gui()
            
            # First check the old required_images for compatibility
            required_types = ['map', 'run', 'bag', 'kill', 'chose', 'overload']
            
            # Group templates by type
            template_groups = {}
            msg = "\nLoading templates:"
            print(msg)
            self.add_log_entry(msg)
            for filename, image in self.images.items():
                # Only process filenames with extension
                if not any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                    continue
                    
                # Extract template type from filename
                base_name = os.path.splitext(filename.lower())[0]  # Remove file extension correctly
                template_type = ''.join(c for c in base_name if not c.isdigit())
                template_type = template_type.rstrip('_')  # Remove trailing underscores
                
                msg = f"File: {filename} -> Type: {template_type}"
                print(msg)
                self.add_log_entry(msg)
                
                if template_type not in template_groups:
                    template_groups[template_type] = []
                    
                template_groups[template_type].append({
                    'name': filename,
                    'image': image
                })
            
            msg = f"\nRequired types: {required_types}"
            print(msg)
            self.add_log_entry(msg)
            msg = f"Found types: {list(template_groups.keys())}"
            print(msg)
            self.add_log_entry(msg)
            
            # Check required template types
            missing_types = [t for t in required_types if t not in template_groups]
            if missing_types:
                error_msg = f"Error: Missing template types: {', '.join(missing_types)}"
                print(error_msg)
                self.add_log_entry(error_msg)
                self.set_status_text(error_msg)
                return
            
            # If no died templates were found, output a warning
            if 'died' not in template_groups:
                msg = "Warning: No died templates found - death detection disabled"
                print(msg)
                self.add_log_entry(msg)
                template_groups['died'] = []  # Empty list for died templates
                
            self.bot.set_templates(template_groups)
            
            # Set start time only if it's the first start
            if not self.first_start_time:
                self.first_start_time = datetime.now()
            self.start_time = datetime.now()
            
            # Lock the movement radio buttons and mode
            self.move_ad.setEnabled(False)
            self.move_sw.setEnabled(False)
            self.move_both.setEnabled(False)
            self.mode_combo.setEnabled(False)  # Lock the mode
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.attach_button.setEnabled(False)  # Disable the attach button at start
            self.set_status_text("Running...")
            self.bot.start(battle_callback=self.on_battle_detected)
    
    def stop_bot(self):
        """Stops the bot immediately, regardless of current state"""
        if self.bot.running:
            self.bot.stop()  # Stops the bot immediately
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.set_status_text("Stopped")
            
            # Unlock the movement radio buttons and mode
            self.move_ad.setEnabled(True)
            self.move_sw.setEnabled(True)
            self.move_both.setEnabled(True)
            self.mode_combo.setEnabled(True)  # Unlock the mode
            
            # Enable re-attach button when bot is stopped
            self.attach_button.setEnabled(True)
            if self.bot.window_handle:
                self.attach_button.setText("Re-attach to Temtem")
                self.dock_gui()
    
    def on_battle_detected(self):
        """Called when a battle is detected"""
        self.battle_count += 1
        self.battle_label.setText(str(self.battle_count))
        
    def get_temtem_path(self):
        """Gets Temtem path from config or asks user to select it"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('temtem_path')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def save_temtem_path(self, path):
        """Saves Temtem path to config"""
        self.bot.config.save_temtem_path(path)
            
    def launch_temtem(self):
        """Launches Temtem"""
        temtem_path = self.get_temtem_path()
        
        if not temtem_path or not os.path.exists(temtem_path):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Temtem Path")
            msg.setText("Please select the Temtem.exe file.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
            temtem_path = QFileDialog.getOpenFileName(
                self,
                "Select Temtem.exe",
                "C:/Program Files (x86)/Steam/steamapps/common/Temtem",
                "Temtem.exe"
            )[0]
            
            if not temtem_path:
                return
            
            self.save_temtem_path(temtem_path)
        
        try:
            subprocess.Popen(temtem_path)
            self.status_label.setText("Starting Temtem...")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not start Temtem: {str(e)}", QMessageBox.Ok)

    def dock_gui(self):
        """Docks the GUI to the left or right of the Temtem window"""
        if not self.bot.window_handle:
            return
            
        try:
            # Get Temtem window position and size
            temtem_rect = win32gui.GetWindowRect(self.bot.window_handle)
            screen_width = win32api.GetSystemMetrics(0)  # Screen width
            
            # GUI size
            gui_width = self.width()
            gui_height = self.height()
            
            # Check if there's enough space on the right
            if temtem_rect[2] + gui_width <= screen_width:
                # Dock to right
                self.move(temtem_rect[2], temtem_rect[1])
            else:
                # Dock to left
                self.move(temtem_rect[0] - gui_width, temtem_rect[1])
        except Exception as e:
            print(f"Error docking GUI: {e}")

    def attach_to_temtem(self):
        """Handles attaching to the Temtem window"""
        try:
            if self.bot.attach_to_window():
                # Get monitor info
                monitor = win32api.MonitorFromWindow(self.bot.window_handle)
                monitors = win32api.EnumDisplayMonitors()
                monitor_number = 1  # Default to 1 if we can't determine
                
                # Try to find the monitor number
                for i, m in enumerate(monitors):
                    if m[0] == monitor:
                        monitor_number = i + 1
                        break
                
                self.monitor_label.setText(f"Monitor {monitor_number}")
                self.set_status_text("Attached to Temtem")
                # Change button text after first attach
                self.attach_button.setText("Re-attach to Temtem")
                # Only disable the button if the bot is running
                if self.bot.running:
                    self.attach_button.setEnabled(False)
                # Dock GUI
                self.dock_gui()
            else:
                msg = QMessageBox(self)
                msg.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Would you like to start Temtem or try again?")
                msg.setFixedWidth(400)
                msg.setStandardButtons(QMessageBox.NoButton)  # Disable standard buttons like OK
                
                # Create custom title bar
                title_bar = QWidget(msg)
                title_bar.setObjectName("TitleBar")
                title_bar.setFixedHeight(30)
                title_layout = QHBoxLayout(title_bar)
                title_layout.setContentsMargins(10, 0, 0, 0)
                title_layout.setSpacing(0)
                
                title_label = QLabel("Error")
                title_label.setFont(QFont("Arial", 10, QFont.Bold))  # Bold for title
                title_label.setStyleSheet("color: #e0e0e0; background: transparent;")
                title_layout.addWidget(title_label)
                title_layout.addStretch()
                
                close_button = QPushButton("✕")
                close_button.setObjectName("CloseButton")
                close_button.setFixedSize(30, 30)
                close_button.setFont(QFont("Arial", 10, QFont.Bold))  # Bold for X button
                close_button.clicked.connect(msg.reject)
                title_layout.addWidget(close_button)
                
                # Add title bar to message box layout
                layout = msg.layout()
                if layout is not None:
                    layout.setContentsMargins(0, 0, 0, 0)
                    # QGridLayout uses addWidget with row, column
                    layout.addWidget(title_bar, 0, 0, 1, layout.columnCount())
                    # Container for content
                    content = QWidget()
                    content_layout = QVBoxLayout(content)
                    content_layout.setContentsMargins(20, 20, 20, 10)  # Reduced bottom margin
                    content_layout.setSpacing(15)
                    
                    # Text and icon in horizontal layout
                    text_row = QWidget()
                    text_layout = QHBoxLayout(text_row)
                    text_layout.setContentsMargins(0, 0, 0, 0)
                    text_layout.setSpacing(10)
                    
                    # Icon
                    icon_label = QLabel()
                    icon_label.setFixedSize(32, 32)
                    icon_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            padding: 0px;
                        }
                    """)
                    icon = msg.iconPixmap()
                    if icon:
                        icon_label.setPixmap(icon)
                    text_layout.addWidget(icon_label)
                    
                    # Text
                    text_label = QLabel(msg.text())
                    text_label.setFont(QFont("Arial", 10, QFont.Bold))  # Font set to Bold
                    text_label.setWordWrap(False)  # No line wrapping
                    text_label.setStyleSheet("""
                        QLabel {
                            color: rgba(255, 255, 255, 0.85);
                            background: transparent;
                            padding: 0px;
                        }
                    """)
                    text_layout.addWidget(text_label)
                    text_layout.addStretch()
                    
                    # Vertical alignment with icon
                    text_layout.setAlignment(Qt.AlignVCenter)
                    
                    content_layout.addWidget(text_row)
                    
                    # Buttons in horizontal layout
                    button_row = QWidget()
                    button_layout = QHBoxLayout(button_row)
                    button_layout.setContentsMargins(0, 0, 0, 0)
                    button_layout.setSpacing(10)
                    
                    start_button = QPushButton("Start Temtem")
                    retry_button = QPushButton("Try Again")
                    cancel_button = QPushButton("Cancel")
                    
                    # Set font for all buttons
                    for button in [start_button, retry_button, cancel_button]:
                        button.setFont(QFont("Arial", 10, QFont.Bold))  # Bold for buttons
                    
                    button_layout.addWidget(start_button)
                    button_layout.addWidget(retry_button)
                    button_layout.addWidget(cancel_button)
                    
                    content_layout.addWidget(button_row)
                    layout.addWidget(content, 1, 0, 1, layout.columnCount())
                    
                    # Button connections
                    start_button.clicked.connect(lambda: msg.done(QMessageBox.ActionRole))
                    retry_button.clicked.connect(lambda: msg.done(QMessageBox.ActionRole + 1))
                    cancel_button.clicked.connect(msg.reject)
                    
                    # Store buttons for result checking
                    msg.custom_buttons = {
                        start_button: QMessageBox.ActionRole,
                        retry_button: QMessageBox.ActionRole + 1,
                        cancel_button: QMessageBox.RejectRole
                    }
                
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #2b2b2b;
                        color: rgba(255, 255, 255, 0.85);
                        border: 1px solid #3d3d3d;
                        border-radius: 10px;
                    }
                    QWidget {
                        background-color: #2b2b2b;
                        color: rgba(255, 255, 255, 0.85);
                    }
                    QPushButton {
                        background-color: #323232;
                        border: 1px solid #3d3d3d;
                        border-radius: 5px;
                        color: rgba(255, 255, 255, 0.85);
                        padding: 5px 15px;
                        min-width: 120px;
                        min-height: 32px;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                        border: 1px solid #4d4d4d;
                    }
                    QPushButton:pressed {
                        background-color: #2d2d2d;
                    }
                    #TitleBar {
                        background-color: #323232;
                        border-top-left-radius: 9px;
                        border-top-right-radius: 9px;
                        border-bottom: 1px solid #3d3d3d;
                    }
                    #CloseButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 0px;
                        color: rgba(255, 255, 255, 0.85);
                        padding: 5px;
                        min-width: 30px;
                        min-height: 0px;
                    }
                    #CloseButton:hover {
                        background-color: #c42b1c;
                    }
                """)
                
                # Drag functionality
                def mousePressEvent(event):
                    if event.button() == Qt.LeftButton:
                        msg.drag_pos = event.globalPos() - msg.frameGeometry().topLeft()
                        event.accept()

                def mouseMoveEvent(event):
                    if event.buttons() == Qt.LeftButton and hasattr(msg, 'drag_pos'):
                        msg.move(event.globalPos() - msg.drag_pos)
                        event.accept()
                
                title_bar.mousePressEvent = mousePressEvent
                title_bar.mouseMoveEvent = mouseMoveEvent
                
                result = msg.exec_()
                
                # Handle custom button results
                clicked_button = None
                for button, role in msg.custom_buttons.items():
                    if result == role:
                        clicked_button = button
                        break
                
                if clicked_button == start_button:
                    self.launch_temtem()
                elif clicked_button == retry_button:
                    self.attach_to_temtem()
                
                self.set_status_text("Temtem not found")
        except AttributeError:
            msg = QMessageBox(self)
            msg.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Temtem could not be found.")
            msg.setInformativeText("Would you like to start Temtem or try again?")
            
            # Create custom title bar
            title_bar = QWidget(msg)
            title_bar.setObjectName("TitleBar")
            title_bar.setFixedHeight(30)
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 0, 0, 0)
            
            title_label = QLabel("Error")
            title_label.setFont(QFont("Arial", 10))
            title_layout.addWidget(title_label)
            
            close_button = QPushButton("✕")
            close_button.setObjectName("CloseButton")
            close_button.setFixedSize(30, 30)
            close_button.clicked.connect(msg.reject)
            title_layout.addWidget(close_button)
            
            # Add title bar to message box layout
            layout = msg.layout()
            if layout is not None:
                layout.setContentsMargins(0, 0, 0, 10)
                layout.insertWidget(0, title_bar)
            
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #e0e0e0;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #323232;
                    border: 1px solid #3d3d3d;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 5px 15px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
                #qt_msgbox_label { 
                    color: #e0e0e0;
                }
                #qt_msgboxex_icon_label {
                    padding: 0px;
                }
                QMessageBox QWidget {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                }
                #TitleBar {
                    background-color: #323232;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                #CloseButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 0px;
                    color: #e0e0e0;
                    padding: 5px;
                    min-width: 30px;
                }
                #CloseButton:hover {
                    background-color: #c42b1c;
                }
            """)
            
            # Drag functionality
            def mousePressEvent(event):
                if event.button() == Qt.LeftButton:
                    msg.drag_pos = event.globalPos() - msg.frameGeometry().topLeft()
                    event.accept()

            def mouseMoveEvent(event):
                if event.buttons() == Qt.LeftButton and hasattr(msg, 'drag_pos'):
                    msg.move(event.globalPos() - msg.drag_pos)
                    event.accept()
            
            title_bar.mousePressEvent = mousePressEvent
            title_bar.mouseMoveEvent = mouseMoveEvent
            
            start_button = msg.addButton("Start Temtem", QMessageBox.ActionRole)
            retry_button = msg.addButton("Try again", QMessageBox.ActionRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            
            msg.exec_()
            
            if msg.clickedButton() == start_button:
                self.launch_temtem()
            elif msg.clickedButton() == retry_button:
                self.attach_to_temtem()
            
            self.set_status_text("Temtem not found")

    def load_movement_mode(self):
        """Loads the movement mode from config"""
        self.loading_movement_mode = True  # Block events
        try:
            mode = self.bot.config.get('movement_mode', 'both')
            
            # Update radio buttons without triggering save
            self.movement_mode = mode
            if mode == 'ad':
                self.move_ad.setChecked(True)
            elif mode == 'sw':
                self.move_sw.setChecked(True)
            else:
                self.move_both.setChecked(True)
        finally:
            self.loading_movement_mode = False  # Always unblock events
            
    def on_movement_changed(self, mode):
        """Called when movement direction changes"""
        if self.loading_movement_mode:  # Skip during loading
            return
        if self.bot and mode != self.bot.movement_mode:
            self.bot.set_movement_mode(mode)  # This already saves the config

    def write(self, text):
        """Called when print is used"""
        if text.strip():  # Ignore empty lines
            try:
                # Try output to terminal if available
                if hasattr(sys, '__stdout__') and sys.__stdout__:
                    # Ensure text ends with newline
                    if not text.endswith('\n'):
                        text += '\n'
                    sys.__stdout__.write(text)
                    sys.__stdout__.flush()
            except (AttributeError, IOError):
                pass  # Ignore errors if no stdout available
            
            # Formatting for GUI
            import re
            message = text.strip()
            # Remove handle IDs (numbers in square brackets)
            message = re.sub(r'\[\d+\.\d+\]', '', message)  # Removes [numbers.numbers]
            
            # Remove all line breaks and multiple spaces
            message = ' '.join(message.split())
            message = message.replace('\n', '').replace('\r', '')
            
            # Check if message already starts with a time
            if not re.match(r'\[\d{2}:\d{2}:\d{2}\]', message):
                current_time = datetime.now().strftime("%H:%M:%S")
                message = f"[{current_time}] {message.strip()}"
            
            self.print_label.setText(message)
            
    def flush(self):
        """Required for print redirection"""
        try:
            if hasattr(sys, '__stdout__') and sys.__stdout__:
                sys.__stdout__.flush()
        except (AttributeError, IOError):
            pass  # Ignore errors if no stdout available

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def load_highlight_setting(self):
        """Loads the setting for the green circle from config"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('show_highlight', True)  # Default: True
        except (FileNotFoundError, json.JSONDecodeError):
            return True
            
    def save_highlight_setting(self, show_highlight):
        """Saves the setting for the green circle to config"""
        self.bot.config.save_highlight_setting(show_highlight)

    def show_settings(self):
        """Opens the settings window"""
        if self.settings_window is None:
            from settings_gui import SettingsGUI
            self.settings_window = SettingsGUI(self)
            # Delete reference when window is closed
            self.settings_window.closeEvent = lambda event: self.on_settings_closed(event)
            self.settings_window.show()
        else:
            # If already open, bring to foreground
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            
    def on_settings_closed(self, event):
        """Called when settings window is closed"""
        self.settings_window = None
        event.accept()

    def try_auto_attach(self):
        """Tries to automatically attach to Temtem on startup"""
        if not self.bot.window_handle:  # Only if not already attached
            try:
                if self.bot.attach_to_window():
                    # Get monitor info
                    monitor = win32api.MonitorFromWindow(self.bot.window_handle)
                    monitors = win32api.EnumDisplayMonitors()
                    monitor_number = 1  # Default to 1 if we can't determine
                    
                    # Try to find the monitor number
                    for i, m in enumerate(monitors):
                        if m[0] == monitor:
                            monitor_number = i + 1
                            break
                    
                    self.monitor_label.setText(f"Monitor {monitor_number}")
                    self.set_status_text("Attached to Temtem")
                    # Change button text after first attach
                    self.attach_button.setText("Re-attach to Temtem")
                    # Only disable the button if the bot is running
                    if self.bot.running:
                        self.attach_button.setEnabled(False)
                    # Dock GUI
                    self.dock_gui()
                else:
                    msg = "Temtem not found - Starting without connection"
                    print(msg)
                    self.add_log_entry(msg)
            except Exception as e:
                msg = f"Auto-attach error: {e}"
                print(msg)
                self.add_log_entry(msg)

    def add_log_entry(self, message):
        """Adds a new log entry via the signal"""
        self.log_signal.emit(message)
        
    def _add_log_entry(self, message):
        """Actual implementation of log addition (executed in GUI thread)"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = f"[{timestamp}] {message}"
        
        # Add new entry and keep only newest max_logs
        self.log_entries.append(entry)
        if len(self.log_entries) > self.max_logs:
            self.log_entries.pop(0)
            
        # Update Settings GUI if open
        if self.settings_window and hasattr(self.settings_window, 'update_log_display'):
            self.settings_window.update_log_display()
            
    def get_log_entries(self):
        """Returns the current log entries"""
        return self.log_entries.copy()  # Return copy to ensure thread safety

    def on_highlight_changed(self, state):
        """Called when highlight setting changes"""
        show_highlight = bool(state)
        self.save_highlight_setting(show_highlight)
        self.bot.set_highlight_enabled(show_highlight)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AutoLevelGUI()
    sys.exit(app.exec_()) 