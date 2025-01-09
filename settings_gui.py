import sys
import os
import json
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from template_manager import TemplateManager
from config_manager import ConfigManager

class SettingsGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Settings")
        
        # Set window icon - reuse from parent if available
        if self.parent and hasattr(self.parent, 'windowIcon') and not self.parent.windowIcon().isNull():
            self.setWindowIcon(self.parent.windowIcon())
        else:
            # Fallback: Load from file if parent icon not available
            try:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'logo.jpg')
                print("Loading settings window icon from disk:", icon_path)
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull():
                        self.setWindowIcon(QIcon(pixmap))
            except Exception as e:
                print(f"Error setting icon: {str(e)}")
            
        # Use parent's template manager if available, otherwise create new one
        self.template_manager = self.parent.bot.template_manager if self.parent and hasattr(self.parent.bot, 'template_manager') else TemplateManager()
        
        # Initialize config manager
        self.config = ConfigManager()
        
        # Set window properties
        self.setFixedSize(250, 800)  # Increase height for additional settings
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.log_paused = False  # Status for log pause
        self.paused_logs = []  # Separate list for paused logs
        self.current_profile = self.config.get_active_profile()  # Current profile
        self.selected_template_type = None  # Stores the selected template type
        
        # Initialize threshold sliders dictionary
        self.threshold_sliders = {}
        
        self.initUI()
        self.load_settings()
        self.drag_pos = None
        
        # Position above the main window
        if self.parent:
            parent_pos = self.parent.pos()
            parent_size = self.parent.size()
            settings_x = parent_pos.x() + (parent_size.width() - self.width()) // 2
            settings_y = parent_pos.y() - self.height() - 10  # 10 pixels distance upwards
            
            # Ensure the window does not go outside the screen
            screen = QApplication.primaryScreen().geometry()
            if settings_y < 0:
                settings_y = 0
            if settings_x < 0:
                settings_x = 0
            if settings_x + self.width() > screen.width():
                settings_x = screen.width() - self.width()
            
            self.move(settings_x, settings_y)
        
    def initUI(self):
        # Title text
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        
        value_font = QFont()
        value_font.setPointSize(9)
        
        # Main container with border and rounded corners
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
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
        title_label = QLabel('Settings')
        title_label.setStyleSheet("color: #e0e0e0; background: transparent;")
        title_label.setFont(title_font)
        
        # Close button
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
        
        # Content layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(4)  # Reduce spacing between elements from 8 to 4
        content_layout.setContentsMargins(4, 4, 4, 4)  # Reduce margins from 8,8,8,8 to 4,4,4,4
        
        # Style for the content widgets
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 4px;  /* Reduce margin-top from 8px to 4px */
                padding-top: 4px;  /* Reduce padding-top from 8px to 4px */
                color: #e0e0e0;
                background-color: #323232;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 3px 0px 3px;
                background-color: #323232;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 4px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 10px;
                height: 10px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                background-color: #cc7832;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QDoubleSpinBox {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 2px;
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
            QComboBox {
                padding: 10px;  /* Reduce padding for combobox */
                min-height: 18px;  /* Reduce minimum height */
            }
            QComboBox::drop-down {
                border: none;
                padding: 0px;  /* No padding for the dropdown button */
            }
        """)
        
        # Profile group (before the threshold group)
        profile_group = QGroupBox("Profiles")
        profile_group.setFont(title_font)
        profile_layout = QVBoxLayout()
        
        # Profile selection row
        profile_row = QWidget()
        profile_row_layout = QHBoxLayout(profile_row)
        profile_row_layout.setContentsMargins(0, 0, 0, 0)
        profile_row_layout.setSpacing(2)  # Reduced spacing
        
        # Create profile label
        self.profile_label = QLabel(self.current_profile)
        self.profile_label.setFont(title_font)
        profile_row_layout.addWidget(self.profile_label)
        
        # Profile combo box
        self.profile_combo = QComboBox()
        self.profile_combo.setFont(value_font)
        self.profile_combo.setFixedHeight(20)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 2px 5px;
                min-height: 20px;
            }
        """)
        self.profile_combo.currentTextChanged.connect(self.load_profile)
        profile_row_layout.addWidget(self.profile_combo)
        
        profile_layout.addWidget(profile_row)
        
        # Profile buttons row
        profile_buttons_row = QWidget()
        profile_buttons_layout = QHBoxLayout(profile_buttons_row)
        profile_buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        new_profile_btn = QPushButton("New")
        new_profile_btn.clicked.connect(self.create_new_profile)
        delete_profile_btn = QPushButton("Delete")
        delete_profile_btn.clicked.connect(self.delete_profile)
        
        profile_buttons_layout.addWidget(new_profile_btn)
        profile_buttons_layout.addWidget(delete_profile_btn)
        profile_layout.addWidget(profile_buttons_row)
        
        profile_group.setLayout(profile_layout)
        content_layout.addWidget(profile_group)
        
        # Template management group (before the threshold group)
        template_group = QGroupBox("Template Management")
        template_group.setFont(title_font)
        template_layout = QVBoxLayout()
        
        # Screenshot button
        screenshot_row = QWidget()
        screenshot_layout = QHBoxLayout(screenshot_row)
        screenshot_layout.setContentsMargins(0, 0, 0, 0)
        
        screenshot_btn = QPushButton("Screenshot")
        screenshot_btn.clicked.connect(self.take_screenshot)
        screenshot_layout.addWidget(screenshot_btn)
        
        # Preview button
        preview_btn = QPushButton("Show Templates")
        preview_btn.clicked.connect(self.preview_templates)
        screenshot_layout.addWidget(preview_btn)
        
        template_layout.addWidget(screenshot_row)
        
        template_group.setLayout(template_layout)
        content_layout.addWidget(template_group)
        
        # Threshold group
        threshold_group = QGroupBox("Detection Thresholds")
        threshold_group.setFont(title_font)
        threshold_layout = QVBoxLayout()
        
        # Spot highlight setting
        highlight_row = QWidget()
        highlight_layout = QHBoxLayout(highlight_row)
        highlight_layout.setContentsMargins(0, 0, 0, 0)
        
        highlight_title = QLabel("Spot Highlight:")
        highlight_title.setFont(title_font)
        self.highlight_checkbox = QCheckBox()
        
        highlight_layout.addWidget(highlight_title)
        highlight_layout.addStretch()
        highlight_layout.addWidget(self.highlight_checkbox)
        threshold_layout.addWidget(highlight_row)
        
        # Highlight duration
        highlight_duration_row = QWidget()
        highlight_duration_layout = QHBoxLayout(highlight_duration_row)
        highlight_duration_layout.setContentsMargins(0, 0, 0, 0)
        
        highlight_duration_title = QLabel("Highlight Duration (ms):")
        highlight_duration_title.setFont(title_font)
        self.highlight_duration_spin = QSpinBox()
        self.highlight_duration_spin.setRange(100, 2000)  # 100ms to 2 seconds
        self.highlight_duration_spin.setSingleStep(50)
        
        highlight_duration_layout.addWidget(highlight_duration_title)
        highlight_duration_layout.addStretch()
        highlight_duration_layout.addWidget(self.highlight_duration_spin)
        threshold_layout.addWidget(highlight_duration_row)
        
        # Run threshold
        run_row = QWidget()
        run_layout = QHBoxLayout(run_row)
        run_layout.setContentsMargins(0, 0, 0, 0)
        
        run_title = QLabel("Run:")
        run_title.setFont(title_font)
        self.run_spin = QDoubleSpinBox()
        self.run_spin.setRange(0.1, 1.0)
        self.run_spin.setSingleStep(0.01)
        self.run_spin.setDecimals(2)
        self.run_spin.setFixedWidth(55)  # Set fixed width
        run_test = QPushButton("Test")
        run_test.setFixedWidth(40)
        run_test.clicked.connect(lambda: self.test_threshold('run', run_test))
        
        run_layout.addWidget(run_title)
        run_layout.addStretch()
        run_layout.addWidget(self.run_spin)
        run_layout.addWidget(run_test)
        threshold_layout.addWidget(run_row)
        self.threshold_sliders['run'] = self.run_spin

        # Bag threshold
        bag_row = QWidget()
        bag_layout = QHBoxLayout(bag_row)
        bag_layout.setContentsMargins(0, 0, 0, 0)
        
        bag_title = QLabel("Bag:")
        bag_title.setFont(title_font)
        self.bag_spin = QDoubleSpinBox()
        self.bag_spin.setRange(0.1, 1.0)
        self.bag_spin.setSingleStep(0.01)
        self.bag_spin.setDecimals(2)
        self.bag_spin.setFixedWidth(55)  # Set fixed width
        bag_test = QPushButton("Test")
        bag_test.setFixedWidth(40)
        bag_test.clicked.connect(lambda: self.test_threshold('bag', bag_test))
        
        bag_layout.addWidget(bag_title)
        bag_layout.addStretch()
        bag_layout.addWidget(self.bag_spin)
        bag_layout.addWidget(bag_test)
        threshold_layout.addWidget(bag_row)
        self.threshold_sliders['bag'] = self.bag_spin

        # Kill threshold
        kill_row = QWidget()
        kill_layout = QHBoxLayout(kill_row)
        kill_layout.setContentsMargins(0, 0, 0, 0)
        
        kill_title = QLabel("Kill:")
        kill_title.setFont(title_font)
        self.kill_spin = QDoubleSpinBox()
        self.kill_spin.setRange(0.1, 1.0)
        self.kill_spin.setSingleStep(0.01)
        self.kill_spin.setDecimals(2)
        self.kill_spin.setFixedWidth(55)  # Set fixed width
        kill_test = QPushButton("Test")
        kill_test.setFixedWidth(40)
        kill_test.clicked.connect(lambda: self.test_threshold('kill', kill_test))
        
        kill_layout.addWidget(kill_title)
        kill_layout.addStretch()
        kill_layout.addWidget(self.kill_spin)
        kill_layout.addWidget(kill_test)
        threshold_layout.addWidget(kill_row)
        self.threshold_sliders['kill'] = self.kill_spin

        # Chose threshold
        chose_row = QWidget()
        chose_layout = QHBoxLayout(chose_row)
        chose_layout.setContentsMargins(0, 0, 0, 0)
        
        chose_title = QLabel("Chose:")
        chose_title.setFont(title_font)
        self.chose_spin = QDoubleSpinBox()
        self.chose_spin.setRange(0.1, 1.0)
        self.chose_spin.setSingleStep(0.01)
        self.chose_spin.setDecimals(2)
        self.chose_spin.setFixedWidth(55)  # Set fixed width
        chose_test = QPushButton("Test")
        chose_test.setFixedWidth(40)
        chose_test.clicked.connect(lambda: self.test_threshold('chose', chose_test))
        
        chose_layout.addWidget(chose_title)
        chose_layout.addStretch()
        chose_layout.addWidget(self.chose_spin)
        chose_layout.addWidget(chose_test)
        threshold_layout.addWidget(chose_row)
        self.threshold_sliders['chose'] = self.chose_spin

        # Overload threshold
        overload_row = QWidget()
        overload_layout = QHBoxLayout(overload_row)
        overload_layout.setContentsMargins(0, 0, 0, 0)
        
        overload_title = QLabel("Overload:")
        overload_title.setFont(title_font)
        self.overload_spin = QDoubleSpinBox()
        self.overload_spin.setRange(0.1, 1.0)
        self.overload_spin.setSingleStep(0.01)
        self.overload_spin.setDecimals(2)
        self.overload_spin.setFixedWidth(55)  # Set fixed width
        overload_test = QPushButton("Test")
        overload_test.setFixedWidth(40)
        overload_test.clicked.connect(lambda: self.test_threshold('overload', overload_test))
        
        overload_layout.addWidget(overload_title)
        overload_layout.addStretch()
        overload_layout.addWidget(self.overload_spin)
        overload_layout.addWidget(overload_test)
        threshold_layout.addWidget(overload_row)
        self.threshold_sliders['overload'] = self.overload_spin

        # Died threshold
        died_row = QWidget()
        died_layout = QHBoxLayout(died_row)
        died_layout.setContentsMargins(0, 0, 0, 0)
        
        died_title = QLabel("Died:")
        died_title.setFont(title_font)
        self.died_spin = QDoubleSpinBox()
        self.died_spin.setRange(0.1, 1.0)
        self.died_spin.setSingleStep(0.01)
        self.died_spin.setDecimals(2)
        self.died_spin.setFixedWidth(55)  # Set fixed width
        died_test = QPushButton("Test")
        died_test.setFixedWidth(40)
        died_test.clicked.connect(lambda: self.test_threshold('died', died_test))
        
        died_layout.addWidget(died_title)
        died_layout.addStretch()
        died_layout.addWidget(self.died_spin)
        died_layout.addWidget(died_test)
        threshold_layout.addWidget(died_row)
        self.threshold_sliders['died'] = self.died_spin

        # Map threshold
        map_row = QWidget()
        map_layout = QHBoxLayout(map_row)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        map_title = QLabel("Map:")
        map_title.setFont(title_font)
        self.map_spin = QDoubleSpinBox()
        self.map_spin.setRange(0.1, 1.0)
        self.map_spin.setSingleStep(0.01)
        self.map_spin.setDecimals(2)
        self.map_spin.setFixedWidth(55)  # Set fixed width
        map_test = QPushButton("Test")
        map_test.setFixedWidth(40)
        map_test.clicked.connect(lambda: self.test_threshold('map', map_test))
        
        map_layout.addWidget(map_title)
        map_layout.addStretch()
        map_layout.addWidget(self.map_spin)
        map_layout.addWidget(map_test)
        threshold_layout.addWidget(map_row)
        self.threshold_sliders['map'] = self.map_spin
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        threshold_layout.addWidget(save_button)
        
        threshold_group.setLayout(threshold_layout)
        content_layout.addWidget(threshold_group)
        
        # Log group
        log_group = QGroupBox("Log Display")
        log_group.setFont(title_font)
        log_layout = QVBoxLayout()
        
        # Pause button
        self.pause_button = QPushButton("Pause Log")
        self.pause_button.clicked.connect(self.toggle_log_pause)
        log_layout.addWidget(self.pause_button)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setFont(QFont("Consolas", 8))  # Monospace font
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d3d;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.log_display.setReadOnly(True)  # Read-only
        self.log_display.setMinimumHeight(150)  # Height for about 15 lines
        log_layout.addWidget(self.log_display)
        
        log_group.setLayout(log_layout)
        content_layout.addWidget(log_group)
        
        # Add everything to the container
        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)
        main_layout.addWidget(container)
        
        # Enable window movement
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent
        
    def load_settings(self):
        """Load settings from config"""
        # Ensure Default profile exists
        self.config.ensure_default_profile()
        
        # Get active profile
        self.current_profile = self.config.get_active_profile()
        
        # Load profile data
        profile = self.config.get_profile()
        if profile:
            # Load thresholds
            thresholds = profile.get('thresholds', {})
            for name, value in thresholds.items():
                if name in self.threshold_sliders:
                    self.threshold_sliders[name].setValue(value)
                    
            # Load highlight settings
            self.highlight_enabled = profile.get('show_highlight', True)
            self.highlight_duration = profile.get('highlight_duration', 750)
            
            # Update UI
            self.highlight_checkbox.setChecked(self.highlight_enabled)
            self.highlight_duration_spin.setValue(self.highlight_duration)
            
        # Update profile display
        self.profile_label.setText(self.current_profile)
        self.update_profile_combo()
    
    def save_settings(self):
        """Saves the settings"""
        if self.parent and hasattr(self.parent.bot, 'set_thresholds'):
            # Save thresholds
            thresholds = {
                'run': self.run_spin.value(),
                'bag': self.bag_spin.value(),
                'kill': self.kill_spin.value(),
                'chose': self.chose_spin.value(),
                'overload': self.overload_spin.value(),
                'died': self.died_spin.value(),
                'map': self.map_spin.value()
            }
            self.parent.bot.set_thresholds(thresholds)
            
            # Update profile data
            profile_data = {
                'show_highlight': self.highlight_checkbox.isChecked(),
                'highlight_duration': self.highlight_duration_spin.value(),
                'thresholds': thresholds
            }
            
            # Save profile with save=True, da dies eine explizite Speicheraktion ist
            self.config.set_profile(self.current_profile, profile_data, save=True)
            
            # Set active profile using the proper method
            self.config.set_active_profile(self.current_profile)
            
            # Update profile labels
            self.profile_label.setText(self.current_profile)
            if self.parent and hasattr(self.parent, 'profile_label'):
                self.parent.profile_label.setText(self.current_profile)
            
            # Update bot
            self.parent.bot.set_highlight_enabled(self.highlight_checkbox.isChecked())
            self.parent.bot.set_highlight_duration(self.highlight_duration_spin.value())
            
            # Log message for saving
            if hasattr(self.parent, 'add_log_entry'):
                self.parent.add_log_entry(f"Settings for profile '{self.current_profile}' saved")
    
    def load_profile(self, profile_name):
        """Loads a specific profile"""
        if not profile_name:
            return
            
        # Get profile data
        profile = self.config.get_profile(profile_name)
        
        if profile:
            self.current_profile = profile_name
            
            # Update profile label in main window immediately
            if self.parent and hasattr(self.parent, 'profile_label'):
                self.parent.profile_label.setText(profile_name)
            
            # Load profile values
            self.highlight_checkbox.setChecked(profile.get('show_highlight', True))
            self.highlight_duration_spin.setValue(profile.get('highlight_duration', 750))
            
            # Load thresholds
            thresholds = profile.get('thresholds', {})
            self.run_spin.setValue(thresholds.get('run', 0.6))
            self.bag_spin.setValue(thresholds.get('bag', 0.6))
            self.kill_spin.setValue(thresholds.get('kill', 0.75))
            self.chose_spin.setValue(thresholds.get('chose', 0.7))
            self.overload_spin.setValue(thresholds.get('overload', 0.7))
            self.died_spin.setValue(thresholds.get('died', 0.8))
            self.map_spin.setValue(thresholds.get('map', 0.95))
            
            # Update bot settings without saving
            if self.parent and hasattr(self.parent.bot, 'set_thresholds'):
                self.parent.bot.thresholds = thresholds.copy()  # Update thresholds directly
                self.parent.bot.highlight_enabled = profile.get('show_highlight', True)
                self.parent.bot.highlight_duration = profile.get('highlight_duration', 750)
            
            # Set as active profile using the proper method
            self.config.set_active_profile(profile_name)
    
    def create_new_profile(self):
        """Creates a new profile"""
        # Custom input dialog in dark mode
        dialog = QDialog(self)  # Parent is self (settings window)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        dialog.setFixedSize(250, 130)
        dialog.setModal(True)  # Make dialog modal
        
        # Layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container with border
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
        
        # Title bar
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
        
        # Title
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_label = QLabel('New Profile')
        title_label.setStyleSheet("color: #e0e0e0; background: transparent;")
        title_label.setFont(title_font)
        
        # Close button
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
        close_button.clicked.connect(dialog.reject)  # Changed from close to reject
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_button)
        
        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # Input field
        name_input = QLineEdit()
        name_input.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 5px;
                selection-background-color: #cc7832;
            }
        """)
        name_input.setPlaceholderText("Enter profile name")
        content_layout.addWidget(name_input)
        
        # Buttons
        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(ok_button.styleSheet())
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        content_layout.addWidget(button_row)
        
        # Add all components to container
        container_layout.addWidget(title_bar)
        container_layout.addWidget(content)
        
        # Add container to main layout
        main_layout.addWidget(container)
        
        # Button actions
        def on_ok():
            name = name_input.text().strip()
            if name:
                if self.profile_combo.findText(name) >= 0:
                    # Error message in dark mode
                    msg = QMessageBox(dialog)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Error")
                    msg.setText("A profile with this name already exists!")
                    msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
                    msg.setStyleSheet("""
                        QMessageBox {
                            background-color: #2b2b2b;
                            color: #e0e0e0;
                            border: 1px solid #3d3d3d;
                            border-radius: 8px;
                        }
                        QLabel {
                            color: #e0e0e0;
                            background: transparent;
                            padding: 10px;
                        }
                        QPushButton {
                            background-color: #3d3d3d;
                            border: none;
                            border-radius: 3px;
                            color: #e0e0e0;
                            padding: 5px 15px;
                            min-width: 60px;
                        }
                        QPushButton:hover {
                            background-color: #4d4d4d;
                        }
                        QPushButton:pressed {
                            background-color: #2d2d2d;
                        }
                    """)
                    msg.show()
                    msg_center = dialog.geometry().center()
                    msg.move(msg_center.x() - msg.width() // 2,
                            msg_center.y() - msg.height() // 2)
                    msg.exec_()
                    return
                
                # Add new profile
                self.profile_combo.addItem(name)
                self.profile_combo.setCurrentText(name)
                self.current_profile = name
                
                # Update profile label in main window immediately
                if self.parent and hasattr(self.parent, 'profile_label'):
                    self.parent.profile_label.setText(name)
                
                self.save_settings()
                dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)
        name_input.returnPressed.connect(on_ok)
        
        # Drag functionality
        dialog.drag_pos = None
        
        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                dialog.drag_pos = event.globalPos() - dialog.frameGeometry().topLeft()
                event.accept()
        
        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton and dialog.drag_pos is not None:
                dialog.move(event.globalPos() - dialog.drag_pos)
                event.accept()
        
        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent
        
        # Center on settings window
        settings_center = self.geometry().center()
        dialog.move(settings_center.x() - dialog.width() // 2,
                   settings_center.y() - dialog.height() // 2)
        
        # Execute dialog (replaces show())
        dialog.exec_()
    
    def delete_profile(self):
        """Delete the current profile"""
        if not self.current_profile:
            return
            
        if self.current_profile == "Default":
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setText("The default profile cannot be deleted!")
            msg.setWindowTitle("Cannot Delete Profile")
            msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
                QLabel {
                    color: #e0e0e0;
                    background: transparent;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    border: none;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 5px 15px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
            """)
            msg.show()
            self.ensure_dialog_visible(msg)
            msg.exec_()
            return
            
        # Ask for confirmation
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"Are you sure you want to delete the profile '{self.current_profile}'?")
        msg.setWindowTitle("Delete Profile")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
                padding: 10px;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        msg.show()
        self.ensure_dialog_visible(msg)
        if msg.exec_() == QMessageBox.Yes:
            # Delete profile
            self.config.delete_profile(self.current_profile)
            
            # Switch to Default profile
            self.profile_combo.setCurrentText("Default")
            self.load_profile("Default")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def toggle_log_pause(self):
        """Pauses or resumes the log display"""
        self.log_paused = not self.log_paused
        self.pause_button.setText("Resume Log" if self.log_paused else "Pause Log")
        
        if self.log_paused:
            # Copy current logs to the pause list
            self.paused_logs = self.parent.get_log_entries()
        else:
            # Clear the pause list
            self.paused_logs = []
            
        self.update_log_display()
        
    def update_log_display(self):
        """Updates the log display"""
        if not self.log_paused:
            # Show current logs
            logs = self.parent.get_log_entries()
        else:
            # Show paused logs
            logs = self.paused_logs
            
        # Format logs for display
        log_text = "\n".join(logs) if logs else "No logs available"
        self.log_display.setText(log_text)
        # Scroll to the end
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

    def highlight_test_button(self, button):
        """Shows a red highlight circle for the test button"""
        # Position and size of the button in screen coordinates
        button_pos = button.mapToGlobal(button.rect().topLeft())
        x = button_pos.x()
        y = button_pos.y()
        w = button.width()
        h = button.height()
        
        # Create temporary highlight window
        highlight = QWidget(None)
        highlight.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        highlight.setAttribute(Qt.WA_TranslucentBackground)
        highlight.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Set geometry with some padding
        padding = 5
        highlight.setGeometry(x - padding, y - padding, w + padding*2, h + padding*2)
        
        # Override paintEvent for the highlight
        def paintEvent(event):
            painter = QPainter(highlight)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Red circle with high opacity
            pen = QPen(QColor(255, 0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            
            # Semi-transparent fill
            painter.setBrush(QColor(255, 0, 0, 50))
            
            # Draw the filled circle
            painter.drawEllipse(5, 5, highlight.width()-10, highlight.height()-10)
            
        highlight.paintEvent = paintEvent
        highlight.show()
        
        # Timer for fading out
        QTimer.singleShot(2000, highlight.deleteLater)

    def test_threshold(self, threshold, button):
        """Tests the specified threshold"""
        if not self.parent or not hasattr(self.parent.bot, 'find_image_in_window'):
            return
            
        # Ensure the bot is initialized
        if not self.parent.bot.window_handle:
            # Try to find the window first
            if not self.parent.bot.attach_to_window():
                self.parent.add_log_entry("Error: Could not find Temtem window")
                return
                
        # Save current thresholds
        current_thresholds = {}
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                current_thresholds = config.get('thresholds', {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass
            
        # Temporarily set the new threshold
        test_thresholds = current_thresholds.copy()
        
        # Dynamically collect all matching templates
        templates_dict = {}  # Store template and name
        if threshold == 'run':
            test_thresholds['run'] = self.run_spin.value()
            # Search for all templates that start with 'run' (only files with extension)
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('run') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
        elif threshold == 'bag':
            test_thresholds['bag'] = self.bag_spin.value()
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('bag') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
        elif threshold == 'kill':
            test_thresholds['kill'] = self.kill_spin.value()
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('kill') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
        elif threshold == 'chose':
            test_thresholds['chose'] = self.chose_spin.value()
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('chose') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
        elif threshold == 'overload':
            test_thresholds['overload'] = self.overload_spin.value()
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('overload') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
        elif threshold == 'died':
            test_thresholds['died'] = self.died_spin.value()
            print(f"Current died threshold value: {self.died_spin.value()}")
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('died') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
            print(f"Found died templates: {list(templates_dict.keys())}")
            print(f"All available images: {list(self.parent.images.keys())}")
        else:  # map
            test_thresholds['map'] = self.map_spin.value()
            templates_dict = {name: img for name, img in self.parent.images.items() 
                            if name.lower().startswith('map') and any(name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])}
            
        if not templates_dict:
            self.parent.add_log_entry(f"Error: No templates found for {threshold}")
            return
            
        # Set test thresholds
        self.parent.bot.set_thresholds(test_thresholds)
        
        # Create temporary highlight window for Temtem
        highlight = QWidget(None)
        highlight.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        highlight.setAttribute(Qt.WA_TranslucentBackground)
        highlight.setAttribute(Qt.WA_ShowWithoutActivating)
        
        def paintEvent(event):
            painter = QPainter(highlight)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(255, 0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 0, 0, 50))
            painter.drawEllipse(5, 5, highlight.width()-10, highlight.height()-10)
            
        highlight.paintEvent = paintEvent
        
        # Perform tests
        found = False
        found_template_name = None
        confidence_results = []  # Store all confidence results
        
        for template_name, template in templates_dict.items():
            if template is None:
                continue
                
            try:
                # Get correct screen coordinates
                monitor = self.parent.bot.get_screen_coordinates(self.parent.bot.window_handle)
                if not monitor:
                    continue
                    
                # Capture window content using MSS
                sct = self.parent.bot._ensure_mss()
                screenshot = sct.grab(monitor)
                
                # Convert MSS screenshot to OpenCV format
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                template_cv = cv2.cvtColor(np.array(template), cv2.COLOR_RGB2BGR)
                
                # Template matching
                result = cv2.matchTemplate(screenshot_cv, template_cv, cv2.TM_SQDIFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # In TM_SQDIFF_NORMED, min_val is the best match (0 = perfect, 1 = no match)
                confidence = 1.0 - min_val
                confidence_results.append((template_name, confidence))  # Store result
                
                # Get threshold value for current template type
                threshold_val = test_thresholds.get(threshold, 0.95)  # Default to 0.95 if not found
                
                if confidence >= threshold_val:
                    # Calculate the position of the found template
                    h, w = template_cv.shape[:2]
                    x = min_loc[0] + monitor["left"]
                    y = min_loc[1] + monitor["top"]
                    
                    # Show red circle at the found position
                    padding = 10
                    highlight.setGeometry(x-padding, y-padding, w+padding*2, h+padding*2)
                    highlight.show()
                    QTimer.singleShot(2000, highlight.deleteLater)
                    
                    found = True
                    found_template_name = template_name
                    break
                    
            except Exception as e:
                self.parent.add_log_entry(f"Test error: {str(e)}")
                
        # Restore original thresholds
        self.parent.bot.set_thresholds(current_thresholds)
        
        # Show result
        if found:
            self.parent.add_log_entry(f"Test {threshold}: Template '{found_template_name}' found!")
        else:
            # Create detailed log message with confidence values
            log_message = f"Test {threshold}: No template found.\n"
            log_message += f"Confidence values:\n"
            for template_name, confidence in confidence_results:
                log_message += f"- {template_name}: {confidence:.3f}\n"
            log_message += f"Required threshold: {threshold_val:.2f}"
            self.parent.add_log_entry(log_message)
            
            # Also print to console for debugging
            print(f"\nAll confidence values for {threshold} test:")
            for template_name, confidence in confidence_results:
                print(f"{template_name}: {confidence:.3f}")
            print(f"Required threshold: {threshold_val:.2f}")

    def take_screenshot(self):
        """Opens screenshot dialog"""
        if not self.parent or not self.parent.bot.window_handle:
            error_dialog = QMessageBox(self)
            error_dialog.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setText("Please attach to Temtem first!")
            error_dialog.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                }
                QMessageBox QLabel {
                    color: #e0e0e0;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    border: none;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 5px 15px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
            """)
            error_dialog.exec_()
            return
            
        # Take screenshot
        screenshot = self.template_manager.capture_screenshot(self.parent.bot.window_handle)
        if screenshot:
            # Edit
            edited = self.template_manager.edit_template(screenshot)
            if edited:
                # Select template type
                template_types = ['map', 'run', 'bag', 'kill', 'chose', 'overload', 'died']
                type_dialog = QDialog(self)
                type_dialog.setWindowTitle("Template Type")
                type_dialog.setModal(True)
                type_dialog.setFixedWidth(300)
                type_dialog.setFixedHeight(120)
                type_dialog.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
                type_dialog.setAttribute(Qt.WA_DeleteOnClose)
                type_dialog.setStyleSheet("""
                    QDialog {
                        background-color: #2b2b2b;
                        color: #e0e0e0;
                        border: 1px solid #3d3d3d;
                        border-radius: 8px;
                    }
                    QLabel {
                        color: #e0e0e0;
                    }
                    QPushButton {
                        background-color: #3d3d3d;
                        border: none;
                        border-radius: 3px;
                        color: #e0e0e0;
                        padding: 5px 15px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #4d4d4d;
                    }
                    QPushButton:pressed {
                        background-color: #2d2d2d;
                    }
                    QComboBox {
                        background-color: #3d3d3d;
                        border: none;
                        border-radius: 3px;
                        color: #e0e0e0;
                        padding: 5px;
                    }
                    QComboBox:hover {
                        background-color: #4d4d4d;
                    }
                    QComboBox::drop-down {
                        border: none;
                    }
                    QComboBox::down-arrow {
                        image: none;
                        border: none;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #2b2b2b;
                        color: #e0e0e0;
                        selection-background-color: #4d4d4d;
                        selection-color: #e0e0e0;
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
                
                main_layout = QVBoxLayout(type_dialog)
                main_layout.setContentsMargins(0, 0, 0, 0)
                main_layout.setSpacing(0)
                
                # Title bar
                title_bar = QWidget()
                title_bar.setFixedHeight(30)
                title_layout = QHBoxLayout(title_bar)
                title_layout.setContentsMargins(10, 0, 0, 0)
                
                title_label = QLabel("Select Template Type")
                title_label.setFont(QFont("Arial", 10))
                title_layout.addWidget(title_label)
                
                close_button = QPushButton("✕")
                close_button.setObjectName("CloseButton")
                close_button.setFixedSize(30, 30)
                close_button.clicked.connect(type_dialog.reject)
                title_layout.addWidget(close_button)
                
                main_layout.addWidget(title_bar)
                
                # Content
                content = QWidget()
                content_layout = QVBoxLayout(content)
                content_layout.setContentsMargins(10, 10, 10, 10)
                content_layout.setSpacing(10)
                
                type_combo = QComboBox()
                type_combo.addItems(template_types)
                content_layout.addWidget(type_combo)
                
                ok_btn = QPushButton("OK")
                ok_btn.clicked.connect(lambda: (
                    setattr(self, 'selected_template_type', type_combo.currentText()),
                    type_dialog.accept()
                ))
                content_layout.addWidget(ok_btn)
                
                main_layout.addWidget(content)
                
                # Drag functionality
                def mousePressEvent(event):
                    if event.button() == Qt.LeftButton:
                        type_dialog.drag_pos = event.globalPos() - type_dialog.frameGeometry().topLeft()
                        event.accept()

                def mouseMoveEvent(event):
                    if event.buttons() == Qt.LeftButton and hasattr(type_dialog, 'drag_pos'):
                        type_dialog.move(event.globalPos() - type_dialog.drag_pos)
                        event.accept()
                
                title_bar.mousePressEvent = mousePressEvent
                title_bar.mouseMoveEvent = mouseMoveEvent
                
                if type_dialog.exec_() == QDialog.Accepted:
                    # Add template with the saved type
                    if self.template_manager.add_template(self.selected_template_type, edited):
                        success_msg = QMessageBox(self)
                        success_msg.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
                        success_msg.setIcon(QMessageBox.Information)
                        success_msg.setWindowTitle("Success")
                        success_msg.setText(f"Template of type '{self.selected_template_type}' has been added!")
                        success_msg.setStyleSheet("""
                            QMessageBox {
                                background-color: #2b2b2b;
                                color: #e0e0e0;
                            }
                            QMessageBox QLabel {
                                color: #e0e0e0;
                                padding: 10px;
                            }
                            QPushButton {
                                background-color: #3d3d3d;
                                border: none;
                                border-radius: 3px;
                                color: #e0e0e0;
                                padding: 5px 15px;
                                min-width: 80px;
                            }
                            QPushButton:hover {
                                background-color: #4d4d4d;
                            }
                            QPushButton:pressed {
                                background-color: #2d2d2d;
                            }
                        """)
                        success_msg.exec_()
                        
    def preview_templates(self):
        """Opens template preview"""
        from template_preview_gui import TemplatePreviewGUI
        # Load templates before preview
        self.template_manager.load_templates()
        preview = TemplatePreviewGUI(self.template_manager, self)
        preview.exec_()

    def ensure_dialog_visible(self, dialog):
        """Ensures the dialog is fully visible on screen"""
        # Get the screen geometry
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # Get the dialog geometry
        dialog_geometry = dialog.frameGeometry()
        
        # Center on parent window
        parent_center = self.geometry().center()
        dialog_geometry.moveCenter(parent_center)
        
        # Ensure dialog stays within screen bounds
        if dialog_geometry.right() > screen_geometry.right():
            dialog_geometry.moveRight(screen_geometry.right())
        if dialog_geometry.left() < screen_geometry.left():
            dialog_geometry.moveLeft(screen_geometry.left())
        if dialog_geometry.bottom() > screen_geometry.bottom():
            dialog_geometry.moveBottom(screen_geometry.bottom())
        if dialog_geometry.top() < screen_geometry.top():
            dialog_geometry.moveTop(screen_geometry.top())
            
        # Move dialog to final position
        dialog.move(dialog_geometry.topLeft())

    def update_profile_combo(self):
        """Updates the profile combo box with all available profiles"""
        # Get all profiles
        profiles = self.config.get_all_profiles()
        
        # Update combo box
        self.profile_combo.clear()
        self.profile_combo.addItems(profiles.keys())
        
        # Set current profile
        index = self.profile_combo.findText(self.current_profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SettingsGUI()
    ex.show()
    sys.exit(app.exec_()) 