import os
import re
from PIL import Image, ImageGrab
import glob
import mss
import mss.tools
import win32gui
import numpy as np
import cv2
from send2trash import send2trash
import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QShortcut, QLabel, QWidget, QLineEdit, QSpinBox, QApplication
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
import sys
import win32api
import json
from config_manager import ConfigManager


class TemplateManager:
    def __init__(self, stdout=None):
        self.templates = {}  # Will be filled dynamically
        self.img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
        self._sct = None  # MSS instance for screenshots
        self.stdout = stdout or sys.__stdout__  # Use custom stdout if provided, otherwise use system stdout
        
        # Initialize config manager
        self.config = ConfigManager()
        
    def log(self, message):
        """Writes a message to stdout"""
        self.stdout.write(message + "\n")
        self.stdout.flush()
        
    def _ensure_mss(self):
        """Ensures MSS is initialized"""
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct
        
    def get_screen_coordinates(self, window_handle):
        """Gets the correct screen coordinates for a window"""
        try:
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
            
    def capture_screenshot(self, window_handle=None, region=None):
        """Takes a screenshot

Args:
    window_handle: Optional, handle of the window for screenshot
    region: Optional, region for screenshot (x, y, width, height)

Returns:
    PIL Image or None on error
"""
        try:
            sct = self._ensure_mss()
            
            if window_handle:
                # Screenshot of specific window
                monitor = self.get_screen_coordinates(window_handle)
                if not monitor:
                    return None
                    
                if region:
                    # Adjust region to window coordinates
                    monitor["left"] += region[0]
                    monitor["top"] += region[1]
                    monitor["width"] = region[2]
                    monitor["height"] = region[3]
                    
                screenshot = sct.grab(monitor)
                
            else:
                # Screenshot of entire screen or region
                if region:
                    monitor = {"top": region[1], "left": region[0], 
                             "width": region[2], "height": region[3]}
                    screenshot = sct.grab(monitor)
                else:
                    screenshot = sct.grab(sct.monitors[0])
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return img
            
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
            
    def convert_cv_to_pixmap(self, cv_image):
        """Converts an OpenCV image to a QPixmap"""
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        h, w = rgb_image.shape[:2]
        bytes_per_line = 3 * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)
            
    def edit_template(self, image):
        """Opens a window to edit the template

Args:
    image: PIL Image or path to image
    
Returns:
    Edited PIL Image or None on cancel
"""
        try:
            # Convert to OpenCV format
            if isinstance(image, str):
                image = Image.open(image)
            if isinstance(image, Image.Image):
                image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
            # Create dialog
            self.edit_window = QDialog()
            self.edit_window.setWindowTitle("Template Editor")
            self.edit_window.setModal(True)
            self.edit_window.setAttribute(Qt.WA_DeleteOnClose)
            self.edit_window.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.edit_window.setAttribute(Qt.WA_TranslucentBackground)
                
            # Main container layout
            main_layout = QVBoxLayout(self.edit_window)
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
            title_font = QFont()
            title_font.setPointSize(9)
            title_font.setBold(True)
            title_label = QLabel('Template Editor')
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
            close_button.clicked.connect(self.edit_window.reject)
                
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            title_layout.addWidget(close_button)
                
            # Content widget
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(8, 8, 8, 8)
            content_layout.setSpacing(8)
                
            # Info text
            info_label = QLabel("Drag a rectangle to select the desired area")
            info_label.setStyleSheet("color: #e0e0e0; background: transparent;")
            info_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(info_label)
            
            # Image area with dark background
            image_widget = QLabel()
            image_widget.setStyleSheet("background-color: #1e1e1e;")
            image_widget.setAlignment(Qt.AlignCenter)
            
            # Convert image to QPixmap and scale if needed
            h, w = image.shape[:2]
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            # Scale if needed
            screen = QApplication.primaryScreen().geometry()
            max_w = int(screen.width() * 0.8)
            max_h = int(screen.height() * 0.8)
            self.scale_factor = 1.0
            if w > max_w or h > max_h:
                scaled_pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.scale_factor = min(scaled_pixmap.width() / w, scaled_pixmap.height() / h)
                pixmap = scaled_pixmap
                
            # Set widget size based on pixmap size plus padding
            padding = 20
            widget_width = pixmap.width() + padding * 2
            widget_height = pixmap.height() + padding * 2
            image_widget.setMinimumSize(widget_width, widget_height)
            image_widget.setStyleSheet(f"background-color: #1e1e1e; padding: {padding}px;")
            
            image_widget.setPixmap(pixmap)
            content_layout.addWidget(image_widget)
                
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)
                
            save_btn = QPushButton("Save (S)")
            reset_btn = QPushButton("Reset (R)")
            cancel_btn = QPushButton("Cancel (ESC)")
                
            # Style for buttons
            button_style = """
                QPushButton {
                    background-color: #3d3d3d;
                    border: none;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 4px;
                    min-height: 20px;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
                QPushButton:disabled {
                    background-color: #2d2d2d;
                    color: #808080;
                }
            """
            save_btn.setStyleSheet(button_style)
            reset_btn.setStyleSheet(button_style)
            cancel_btn.setStyleSheet(button_style)
                
            button_layout.addStretch()
            button_layout.addWidget(save_btn)
            button_layout.addWidget(reset_btn)
            button_layout.addWidget(cancel_btn)
            button_layout.addStretch()
                
            content_layout.addLayout(button_layout)
                
            # Add all layouts
            container_layout.addWidget(title_bar)
            container_layout.addWidget(content)
            main_layout.addWidget(container)
            
            # Center window on screen
            screen = QApplication.primaryScreen().geometry()
            window_width = widget_width + 40  # Add some padding
            window_height = widget_height + 120  # Add space for buttons and title
            self.edit_window.setFixedSize(window_width, window_height)
            center_x = screen.center().x() - window_width // 2
            center_y = screen.center().y() - window_height // 2
            self.edit_window.move(center_x, center_y)
            
            # Variables for selection
            self.current_image = image.copy()
            self.roi = None
            self.drawing = False
            self.start_x, self.start_y = -1, -1
            self.current_rect = None
            
            def get_image_offset(widget, pixmap):
                """Calculates the offset of the centered image"""
                # Calculate the horizontal offset for the centered image
                # Subtract the padding from the widget width to account for the available space
                available_width = widget.width() - (padding * 2)
                x_offset = (available_width - pixmap.width()) // 2
                return x_offset

            def get_image_coordinates(x, y, widget, pixmap):
                """Calculates the correct image coordinates from mouse coordinates"""
                # Calculate the offset of the centered image
                x_offset = get_image_offset(widget, pixmap)
                
                # Convert coordinates
                image_x = int((x - padding - x_offset) / self.scale_factor)
                image_y = int((y - padding) / self.scale_factor)
                
                return image_x, image_y

            def mouse_callback(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    if self.current_rect is not None:
                        return
                    self.drawing = True
                    # Calculate correct image coordinates
                    self.start_x, self.start_y = get_image_coordinates(x, y, image_widget, image_widget.pixmap())
                    
                elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
                    # Calculate correct image coordinates
                    orig_x, orig_y = get_image_coordinates(x, y, image_widget, image_widget.pixmap())
                    
                    # Draw rectangle (scaled for display)
                    temp_image = self.current_image.copy()
                    cv2.rectangle(temp_image, (self.start_x, self.start_y), (orig_x, orig_y), (0, 255, 0), 2)
                    image_widget.setPixmap(self.convert_cv_to_pixmap(temp_image))
                    
                elif event == cv2.EVENT_LBUTTONUP and self.drawing:
                    # Calculate correct image coordinates
                    current_x, current_y = get_image_coordinates(x, y, image_widget, image_widget.pixmap())
                    
                    if self.start_x != current_x and self.start_y != current_y:
                        self.drawing = False
                        orig_x = current_x
                        orig_y = current_y
                        
                        x1, x2 = min(self.start_x, orig_x), max(self.start_x, orig_x)
                        y1, y2 = min(self.start_y, orig_y), max(self.start_y, orig_y)
                        
                        if x2 > x1 and y2 > y1:
                            # Ensure coordinates are within image bounds
                            x1 = max(0, min(x1, self.current_image.shape[1]))
                            x2 = max(0, min(x2, self.current_image.shape[1]))
                            y1 = max(0, min(y1, self.current_image.shape[0]))
                            y2 = max(0, min(y2, self.current_image.shape[0]))
                            
                            self.current_rect = [x1, y1, x2, y2]
                            self.roi = self.current_image[y1:y2, x1:x2].copy()
                            temp_image = self.current_image.copy()
                            cv2.rectangle(temp_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            image_widget.setPixmap(self.convert_cv_to_pixmap(temp_image))
            
            def save_roi():
                if self.roi is not None:
                    roi_rgb = cv2.cvtColor(self.roi, cv2.COLOR_BGR2RGB)
                    self.edit_window.roi_result = Image.fromarray(roi_rgb)
                    self.edit_window.accept()
            
            def reset():
                self.roi = None
                self.current_rect = None
                image_widget.setPixmap(self.convert_cv_to_pixmap(self.current_image))
            
            save_btn.clicked.connect(save_roi)
            reset_btn.clicked.connect(reset)
            cancel_btn.clicked.connect(self.edit_window.reject)
            
            # Connect mouse events
            image_widget.mousePressEvent = lambda e: mouse_callback(cv2.EVENT_LBUTTONDOWN, e.x(), e.y(), None, None)
            image_widget.mouseMoveEvent = lambda e: mouse_callback(cv2.EVENT_MOUSEMOVE, e.x(), e.y(), None, None)
            image_widget.mouseReleaseEvent = lambda e: mouse_callback(cv2.EVENT_LBUTTONUP, e.x(), e.y(), None, None)
            
            # Shortcuts
            QShortcut(Qt.Key_S, self.edit_window, save_roi)
            QShortcut(Qt.Key_R, self.edit_window, reset)
            QShortcut(Qt.Key_Escape, self.edit_window, self.edit_window.reject)
            
            # Window drag functionality
            def mousePressEvent(event):
                if event.button() == Qt.LeftButton:
                    self.edit_window.drag_pos = event.globalPos() - self.edit_window.frameGeometry().topLeft()
                    event.accept()
            
            def mouseMoveEvent(event):
                if event.buttons() == Qt.LeftButton and hasattr(self.edit_window, 'drag_pos'):
                    self.edit_window.move(event.globalPos() - self.edit_window.drag_pos)
                    event.accept()
            
            title_bar.mousePressEvent = mousePressEvent
            title_bar.mouseMoveEvent = mouseMoveEvent
            
            # Show window
            self.edit_window.show()
            
            # Execute dialog
            if self.edit_window.exec_() == QDialog.Accepted and hasattr(self.edit_window, 'roi_result'):
                return self.edit_window.roi_result
                    
            return None
                
        except Exception as e:
            print(f"Error editing template: {e}")
            if hasattr(self, 'edit_window'):
                self.edit_window.reject()
            return None
                
    def preview_templates(self):
        """Opens a window with preview of all templates"""
        try:
            # Erstelle Fenster
            window_name = 'Template Preview'
            cv2.namedWindow(window_name)
            
            # Sammle alle Templates
            all_templates = []
            for template_type, templates in self.templates.items():
                for template in templates:
                    all_templates.append({
                        'type': template_type,
                        'name': template['name'],
                        'image': template['image']
                    })
                    
            if not all_templates:
                print("No templates to preview")
                return
                
            current_idx = 0
            max_idx = len(all_templates) - 1
            
            # Erstelle Rename Dialog
            rename_dialog = QDialog()
            rename_dialog.setWindowTitle("Rename Template")
            rename_dialog.setModal(True)
            rename_dialog.setAttribute(Qt.WA_DeleteOnClose)
            rename_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            rename_dialog.setAttribute(Qt.WA_TranslucentBackground)
            rename_dialog.setFixedSize(300, 150)
            
            # Main container layout für Rename Dialog
            main_layout = QVBoxLayout(rename_dialog)
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
            title_font = QFont()
            title_font.setPointSize(9)
            title_font.setBold(True)
            title_label = QLabel('Rename Template')
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
            close_button.clicked.connect(rename_dialog.reject)
            
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            title_layout.addWidget(close_button)
            
            # Content widget
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(20, 20, 20, 20)
            content_layout.setSpacing(10)
            
            # Name input
            from PyQt5.QtWidgets import QLineEdit
            name_input = QLineEdit()
            name_input.setStyleSheet("""
                QLineEdit {
                    background-color: #3d3d3d;
                    border: none;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 5px;
                }
            """)
            content_layout.addWidget(name_input)
            
            # Buttons
            button_layout = QHBoxLayout()
            ok_btn = QPushButton("OK")
            cancel_btn = QPushButton("Cancel")
            
            button_style = """
                QPushButton {
                    background-color: #3d3d3d;
                    border: none;
                    border-radius: 3px;
                    color: #e0e0e0;
                    padding: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
            """
            ok_btn.setStyleSheet(button_style)
            cancel_btn.setStyleSheet(button_style)
            
            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)
            content_layout.addLayout(button_layout)
            
            # Add everything to container
            container_layout.addWidget(title_bar)
            container_layout.addWidget(content)
            main_layout.addWidget(container)
            
            # Window drag functionality
            def mousePressEvent(event):
                if event.button() == Qt.LeftButton:
                    rename_dialog.drag_pos = event.globalPos() - rename_dialog.frameGeometry().topLeft()
                    event.accept()
            
            def mouseMoveEvent(event):
                if event.buttons() == Qt.LeftButton and hasattr(rename_dialog, 'drag_pos'):
                    rename_dialog.move(event.globalPos() - rename_dialog.drag_pos)
                    event.accept()
            
            title_bar.mousePressEvent = mousePressEvent
            title_bar.mouseMoveEvent = mouseMoveEvent
            
            ok_btn.clicked.connect(rename_dialog.accept)
            cancel_btn.clicked.connect(rename_dialog.reject)
            
            while True:
                template = all_templates[current_idx]
                
                # Convert to OpenCV format
                image = cv2.cvtColor(np.array(template['image']), cv2.COLOR_RGB2BGR)
                
                # Zeige Info
                info = f"Type: {template['type']} | Name: {template['name']}"
                info += " | [<-/-> Navigate | D Delete | R Rename | ESC Close]"
                
                # Füge Info zum Bild hinzu
                h, w = image.shape[:2]
                info_img = np.zeros((30, w, 3), dtype=np.uint8)
                cv2.putText(info_img, info, (5, 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Kombiniere Info und Bild
                display = np.vstack([info_img, image])
                
                cv2.imshow(window_name, display)
                key = cv2.waitKey(0) & 0xFF
                
                if key == 27:  # ESC
                    break
                elif key == 83 or key == ord('d'):  # Right arrow or 'D'
                    if current_idx < max_idx:
                        current_idx += 1
                elif key == 81 or key == ord('a'):  # Left arrow or 'A'
                    if current_idx > 0:
                        current_idx -= 1
                elif key == ord('d'):  # Delete
                    template = all_templates[current_idx]
                    if self.delete_template(template['type'], template['name']):
                        # Update the display list
                        all_templates.pop(current_idx)
                        max_idx -= 1
                        if current_idx > max_idx:
                            current_idx = max_idx
                        if max_idx < 0:
                            break
                elif key == ord('r'):  # Rename
                    template = all_templates[current_idx]
                    old_name = template['name']
                    name_input.setText(old_name)
                    name_input.selectAll()
                    
                    # Zentriere Dialog
                    screen_width = win32gui.GetSystemMetrics(0)
                    screen_height = win32gui.GetSystemMetrics(1)
                    x = (screen_width - rename_dialog.width()) // 2
                    y = (screen_height - rename_dialog.height()) // 2
                    rename_dialog.move(x, y)
                    
                    if rename_dialog.exec_() == QDialog.Accepted:
                        new_name = name_input.text().strip()
                        if new_name and new_name != old_name:
                            try:
                                old_path = os.path.join(self.img_dir, old_name)
                                new_path = os.path.join(self.img_dir, new_name)
                                os.rename(old_path, new_path)
                                template['name'] = new_name
                                # Update template in self.templates
                                for t in self.templates[template['type']]:
                                    if t['name'] == old_name:
                                        t['name'] = new_name
                                        break
                            except Exception as e:
                                print(f"Error renaming file: {e}")
            
            cv2.destroyWindow(window_name)
            
        except Exception as e:
            print(f"Error previewing templates: {e}")
            
    def __del__(self):
        """Cleanup MSS when object is destroyed"""
        if self._sct:
            self._sct.close()

    def load_templates(self):
        """Loads all templates from the img folder"""
        if not os.path.exists(self.img_dir):
            print(f"Warning: Image directory not found at {self.img_dir}")
            return False
            
        # Clear existing templates
        self.templates.clear()
            
        # Collect all template types from filenames
        template_types = set()
        for filename in os.listdir(self.img_dir):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            # Extract template type from filename
            base_name = os.path.splitext(filename)[0].lower()  # Remove file extension correctly
            template_type = ''.join(c for c in base_name if not c.isdigit())
            template_type = template_type.rstrip('_')  # Remove trailing underscores
            
            if template_type:
                template_types.add(template_type)
                
        # Initialize dictionary with found types
        for template_type in template_types:
            self.templates[template_type] = []
            
        # Load all images
        for filename in os.listdir(self.img_dir):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            try:
                # Determine template type from filename
                base_name = os.path.splitext(filename)[0].lower()  # Remove file extension correctly
                template_type = ''.join(c for c in base_name if not c.isdigit())
                template_type = template_type.rstrip('_')  # Remove trailing underscores
                
                if template_type in self.templates:
                    img_path = os.path.join(self.img_dir, filename)
                    # Load image and convert to RGB for consistency
                    image = Image.open(img_path).convert('RGB')
                    self.templates[template_type].append({
                        'name': filename,
                        'image': image
                    })
                    print(f"Loaded {template_type} template: {filename}")
                    
            except Exception as e:
                print(f"Error loading template {filename}: {str(e)}")
                
        # Load required template types from config
        required_types = self.get_required_template_types()
        missing_types = [t for t in required_types if t not in self.templates or not self.templates[t]]
        
        if missing_types:
            print(f"Warning: Missing required template types: {', '.join(missing_types)}")
            print("Note: You can add templates through the Template Manager in Settings")
            return False
            
        return True

    def get_required_template_types(self):
        """Loads the required template types from the config"""
        # Get required templates from config or use default list
        return self.config.get('required_templates', ['map', 'run', 'bag', 'kill', 'chose', 'overload'])

    def set_required_template_types(self, types):
        """Saves the required template types in the config"""
        try:
            # Save required templates with save=True
            self.config.set('required_templates', list(types), save=True)
            return True
        except Exception as e:
            print(f"Error saving required template types: {e}")
            return False

    def get_templates(self, template_type):
        """Returns all templates of a specific type"""
        return [t['image'] for t in self.templates.get(template_type, [])]
        
    def get_template_names(self, template_type):
        """Returns the names of all templates of a specific type"""
        return [t['name'] for t in self.templates.get(template_type, [])]
        
    def add_template(self, template_type, image, name=None):
        """Adds a new template and saves it

Args:
    template_type: Type of template (map, run, etc.)
    image: PIL Image or path to image
    name: Optional, name for the template (will be auto-generated if not provided)
    
Returns:
    bool: True if successful, False if not
"""
        if template_type not in self.templates:
            # Create new template group if it doesn't exist yet
            self.templates[template_type] = []
            
        try:
            # Convert to RGB for consistency
            if isinstance(image, str):  # If a path was provided
                image = Image.open(image).convert('RGB')
            elif isinstance(image, Image.Image):
                image = image.convert('RGB')
            else:
                print("Error: Invalid image format")
                return False
                
            # Generate filename if none provided
            if not name:
                # Find next available name
                counter = 1
                while True:
                    test_name = f"{template_type}{counter}.png"
                    if not os.path.exists(os.path.join(self.img_dir, test_name)):
                        name = test_name
                        break
                    counter += 1
                
            # Save image
            save_path = os.path.join(self.img_dir, name)
            image.save(save_path)
            
            # Add to templates
            self.templates[template_type].append({
                'name': name,
                'image': image
            })
            
            print(f"Added new {template_type} template: {name}")
            return True
            
        except Exception as e:
            print(f"Error adding template: {str(e)}")
            return False
            
    def remove_template(self, template_type, name):
        """Removes a template from the list (without deleting the file)"""
        if template_type not in self.templates:
            print(f"[REMOVE] Error: Unknown template type {template_type}")
            return False
            
        try:
            # Find template
            template_list = self.templates[template_type]
            template_idx = None
            for i, t in enumerate(template_list):
                if t['name'] == name:
                    template_idx = i
                    break
                    
            if template_idx is None:
                print(f"[REMOVE] Error: Template {name} not found")
                return False
                
            # Remove from list
            self.templates[template_type].pop(template_idx)
            
            print(f"[REMOVE] Removed {template_type} template: {name} from list")
            return True
            
        except Exception as e:
            print(f"[REMOVE] Error removing template from list: {e}")
            return False

    def delete_template(self, template_type, name):
        """Deletes a template (moves the file to recycle bin and removes it from the list)"""
        try:
            file_path = os.path.join(self.img_dir, name)
            self.log(f"[DELETE] Attempting to delete file: {file_path}")
            
            if not os.path.exists(file_path):
                self.log(f"[DELETE] File not found: {file_path}")
                return False

            # Close image handle if it exists
            for template in self.templates[template_type]:
                if template['name'] == name:
                    try:
                        if template['image']:
                            template['image'].close()
                            template['image'] = None
                            self.log(f"[DELETE] Closed image handle for {name}")
                    except Exception as e:
                        self.log(f"[DELETE] Warning: Could not close image handle: {e}")
                    break

            # Force Python garbage collection before file operations
            import gc
            gc.collect()
            self.log(f"[DELETE] Ran garbage collection")

            # First remove from template list
            if not self.remove_template(template_type, name):
                self.log(f"[DELETE] Failed to remove {name} from template list")
                return False

            # Move to recycle bin using send2trash
            try:
                self.log(f"[DELETE] Moving {file_path} to recycle bin...")
                send2trash(file_path)
                self.log(f"[DELETE] Successfully moved {name} to recycle bin")
                return True

            except Exception as e:
                error_msg = f"[DELETE] Error moving file to recycle bin: {e}"
                self.log(error_msg)
                import traceback
                self.log(traceback.format_exc())
                # Add template back to list since deletion failed
                template = {'name': name, 'image': Image.open(file_path).convert('RGB')}
                self.templates[template_type].append(template)
                return False

        except Exception as e:
            error_msg = f"[DELETE] Error during delete operation: {e}"
            self.log(error_msg)
            import traceback
            self.log(traceback.format_exc())
            return False

    def rename_template(self, template_type, old_name, new_name):
        """Renames a template

Args:
    template_type: Type of template (map, run, etc.)
    old_name: Old name of the template
    new_name: New name of the template
    
Returns:
    bool: True if successful, False if not
"""
        try:
            self.log(f"[RENAME] Attempting to rename template from {old_name} to {new_name}")
            
            old_path = os.path.join(self.img_dir, old_name)
            new_path = os.path.join(self.img_dir, new_name)
            
            if not os.path.exists(old_path):
                self.log(f"[RENAME] Source file not found: {old_path}")
                return False
                
            if os.path.exists(new_path):
                self.log(f"[RENAME] Target file already exists: {new_path}")
                return False
                
            # Find template in the list
            template_found = False
            for template in self.templates[template_type]:
                if template['name'] == old_name:
                    # Close image file before renaming
                    try:
                        if template['image']:
                            template['image'].close()
                            template['image'] = None
                            self.log(f"[RENAME] Closed image handle for {old_name}")
                    except Exception as e:
                        self.log(f"[RENAME] Warning: Could not close image handle: {e}")
                    
                    template_found = True
                    break
                    
            if not template_found:
                self.log(f"[RENAME] Template not found in list: {old_name}")
                return False
                
            # Force garbage collection
            import gc
            gc.collect()
            self.log(f"[RENAME] Ran garbage collection")
            
            # Rename file
            try:
                os.rename(old_path, new_path)
                self.log(f"[RENAME] Successfully renamed file from {old_name} to {new_name}")
                
                # Update template in the list
                for template in self.templates[template_type]:
                    if template['name'] == old_name:
                        template['name'] = new_name
                        # Load image again
                        template['image'] = Image.open(new_path).convert('RGB')
                        break
                        
                return True
                
            except Exception as e:
                error_msg = f"[RENAME] Error renaming file: {e}"
                self.log(error_msg)
                import traceback
                self.log(traceback.format_exc())
                return False
                
        except Exception as e:
            error_msg = f"[RENAME] Error during rename operation: {e}"
            self.log(error_msg)
            import traceback
            self.log(traceback.format_exc())
            return False