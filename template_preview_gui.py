from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QListWidget, QListWidgetItem, QDialog,
                           QLineEdit, QMessageBox, QScrollArea, QFrame, QComboBox, QCheckBox, QApplication)
from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QCursor
import numpy as np
import os
from PIL import Image

try:
    import win32gui
    import win32con
    HAS_WIN32GUI = True
except ImportError:
    HAS_WIN32GUI = False
    
class SelectableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.edit_mode = False
        self.zoom_factor = 1.0
        self.original_pixmap = None
        
    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.updatePixmap()
        
    def updatePixmap(self):
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                int(self.original_pixmap.width() * self.zoom_factor),
                int(self.original_pixmap.height() * self.zoom_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)
        
    def wheelEvent(self, event):
        if self.original_pixmap:
            # Adjust zoom factor (15% per step)
            zoom_in = event.angleDelta().y() > 0
            if zoom_in:
                self.zoom_factor *= 1.15
            else:
                self.zoom_factor /= 1.15
                
            # Limit zoom to reasonable values (10% to 1000%)
            self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
            
            # Update the image
            self.updatePixmap()
            
            # Update selection if in edit mode
            if self.edit_mode and self.selection_start and self.selection_end:
                self.update()
        
    def enterEditMode(self):
        self.edit_mode = True
        self.selection_start = None
        self.selection_end = None
        self.setCursor(Qt.CrossCursor)
        
    def exitEditMode(self):
        self.edit_mode = False
        self.selection_start = None
        self.selection_end = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        
    def mousePressEvent(self, event):
        if not self.edit_mode:
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.LeftButton:
            self.selection_start = event.pos()
            self.selection_end = event.pos()
            self.is_selecting = True
            
    def mouseMoveEvent(self, event):
        if not self.edit_mode:
            super().mouseMoveEvent(event)
            return
            
        if self.is_selecting:
            self.selection_end = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if not self.edit_mode:
            super().mouseReleaseEvent(event)
            return
            
        if event.button() == Qt.LeftButton:
            self.is_selecting = False
            
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.edit_mode and self.selection_start and self.selection_end:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            
            # Draw selection rectangle
            x = min(self.selection_start.x(), self.selection_end.x())
            y = min(self.selection_start.y(), self.selection_end.y())
            w = abs(self.selection_start.x() - self.selection_end.x())
            h = abs(self.selection_start.y() - self.selection_end.y())
            painter.drawRect(x, y, w, h)
            
    def getSelectionRect(self):
        """Returns the selected rectangle"""
        if not self.selection_start or not self.selection_end:
            return None
            
        x = min(self.selection_start.x(), self.selection_end.x())
        y = min(self.selection_start.y(), self.selection_end.y())
        w = abs(self.selection_start.x() - self.selection_end.x())
        h = abs(self.selection_start.y() - self.selection_end.y())
        
        # Consider zoom factor for selection
        x = int(x / self.zoom_factor)
        y = int(y / self.zoom_factor)
        w = int(w / self.zoom_factor)
        h = int(h / self.zoom_factor)
        
        return QRect(x, y, w, h)

class TemplatePreviewGUI(QDialog):
    def __init__(self, template_manager, parent=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.current_template = None
        self.setWindowTitle('Template Manager')
        self.setFixedSize(800, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Dark Mode Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
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
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
            QListWidget {
                background-color: #323232;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4d4d4d;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
            QScrollArea {
                background-color: #323232;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
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
            QLineEdit {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 5px;
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
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                selection-background-color: #4d4d4d;
            }
        """)
        
        self.drag_pos = None
        self.initUI()
        
    def initUI(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Custom title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setObjectName("TitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        
        # Title
        title_label = QLabel("Template Manager")
        title_label.setFont(QFont("Arial", 10))
        title_layout.addWidget(title_label)
        
        # Close button
        close_button = QPushButton("✕")
        close_button.setObjectName("CloseButton")
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        
        layout.addWidget(title_bar)
        
        # Content Layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # Upper area: Template list and info/preview
        upper_layout = QHBoxLayout()
        
        # Left side: List
        list_label = QLabel("Templates:")
        list_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(250)
        self.list_widget.currentItemChanged.connect(self.on_template_selected)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(list_label)
        left_layout.addWidget(self.list_widget)
        upper_layout.addLayout(left_layout)
        
        # Right side: Info and preview
        right_layout = QVBoxLayout()
        
        # Info Label
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("padding: 5px;")
        right_layout.addWidget(self.info_label)
        
        # Edit buttons (disabled by default)
        edit_buttons_layout = QHBoxLayout()
        
        self.save_edit_btn = QPushButton("Save")
        self.crop_preview_btn = QPushButton("Crop Preview")
        self.reset_edit_btn = QPushButton("Reset")
        self.cancel_edit_btn = QPushButton("Cancel")
        
        self.save_edit_btn.clicked.connect(self.save_selection)
        self.crop_preview_btn.clicked.connect(self.show_crop_preview)
        self.reset_edit_btn.clicked.connect(self.reset_selection)
        self.cancel_edit_btn.clicked.connect(self.cancel_edit)
        
        self.save_edit_btn.setEnabled(False)
        self.crop_preview_btn.setEnabled(False)
        self.reset_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        
        edit_buttons_layout.addWidget(self.save_edit_btn)
        edit_buttons_layout.addWidget(self.crop_preview_btn)
        edit_buttons_layout.addWidget(self.reset_edit_btn)
        edit_buttons_layout.addWidget(self.cancel_edit_btn)
        
        right_layout.addLayout(edit_buttons_layout)
        
        # Scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Container for image
        self.image_container = SelectableImageLabel()
        self.image_container.setAlignment(Qt.AlignCenter)
        self.image_container.setStyleSheet("background-color: #1e1e1e; padding: 10px;")
        scroll_area.setWidget(self.image_container)
        
        right_layout.addWidget(scroll_area)
        upper_layout.addLayout(right_layout)
        
        content_layout.addLayout(upper_layout)
        
        # Lower area: Buttons
        button_layout = QHBoxLayout()
        
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self.rename_template)
        self.rename_btn.setEnabled(False)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_template)
        self.edit_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_template)
        self.delete_btn.setEnabled(False)
        
        button_layout.addWidget(self.rename_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        
        content_layout.addLayout(button_layout)
        
        layout.addWidget(content_widget)
        
        # Load templates
        self.load_templates()
        
        # Enable window movement
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent
        
    def load_templates(self):
        """Loads all templates into the list"""
        self.list_widget.clear()
        
        # Load all templates from the manager
        all_templates = self.template_manager.templates
        
        # Add templates grouped by type to the list
        for template_type in sorted(all_templates.keys()):
            # Add type header
            type_item = QListWidgetItem(f"▼ {template_type}")
            type_item.setFont(QFont("Arial", 10, QFont.Bold))
            type_item.setData(Qt.UserRole, None)  # No template data for header
            self.list_widget.addItem(type_item)
            
            # Add templates of this type
            templates = all_templates[template_type]
            for template in sorted(templates, key=lambda x: x['name']):
                item = QListWidgetItem(f"    {template['name']}")
                item.setData(Qt.UserRole, {
                    'type': template_type,
                    'name': template['name'],
                    'image': template['image']
                })
                self.list_widget.addItem(item)
        
    def on_template_selected(self, current, previous):
        """Called when a template is selected"""
        if not current or not current.data(Qt.UserRole):
            # If no item selected or it's a header
            self.current_template = None
            self.rename_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            # Edit buttons remain disabled when no template is selected
            self.save_edit_btn.setEnabled(False)
            self.crop_preview_btn.setEnabled(False)
            self.reset_edit_btn.setEnabled(False)
            self.cancel_edit_btn.setEnabled(False)
            self.info_label.clear()
            self.image_container.clear()
            return
            
        template = current.data(Qt.UserRole)
        self.current_template = template
        
        # Enable only the main buttons
        self.rename_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
        # Edit buttons remain disabled until "Edit" is clicked
        self.save_edit_btn.setEnabled(False)
        self.crop_preview_btn.setEnabled(False)
        self.reset_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        
        # Update Info
        self.info_label.setText(f"Type: {template['type']}\nName: {template['name']}")
        
        # Update Image
        try:
            image = template['image']
            # Convert PIL Image to QPixmap
            img_array = np.array(image)
            height, width, channels = img_array.shape
            bytes_per_line = channels * width
            qt_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale the image if it's too large
            max_size = QSize(500, 400)
            if pixmap.width() > max_size.width() or pixmap.height() > max_size.height():
                pixmap = pixmap.scaled(max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Save the original pixmap
            self.original_preview_pixmap = pixmap
            self.image_container.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading template image: {str(e)}")
            self.image_container.clear()
        
    def rename_template(self):
        """Opens dialog to rename the template"""
        if not self.current_template:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Rename Template")
        dialog.setModal(True)
        dialog.setFixedWidth(300)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Dark Mode Style for the dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
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
            QLineEdit {
                background-color: #3d3d3d;
                border: none;
                border-radius: 3px;
                color: #e0e0e0;
                padding: 5px;
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
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Custom title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setObjectName("TitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        
        # Title
        title_label = QLabel("Rename Template")
        title_label.setFont(QFont("Arial", 10))
        title_layout.addWidget(title_label)
        
        # Close button
        close_button = QPushButton("✕")
        close_button.setObjectName("CloseButton")
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(dialog.reject)
        title_layout.addWidget(close_button)
        
        layout.addWidget(title_bar)
        
        # Content Layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # Input field
        name_label = QLabel("New name:")
        content_layout.addWidget(name_label)
        
        name_input = QLineEdit()
        name_input.setText(self.current_template['name'])
        content_layout.addWidget(name_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        content_layout.addLayout(button_layout)
        
        layout.addWidget(content_widget)
        
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
        
        if dialog.exec_() == QDialog.Accepted:
            new_name = name_input.text().strip()
            if new_name and new_name != self.current_template['name']:
                try:
                    if self.template_manager.rename_template(
                        self.current_template['type'],
                        self.current_template['name'],
                        new_name
                    ):
                        # Update the list
                        current_item = self.list_widget.currentItem()
                        current_item.setText(f"  {new_name}")
                        template_data = current_item.data(Qt.UserRole)
                        template_data['name'] = new_name
                        
                        # Reload the image
                        img_path = os.path.join(self.template_manager.img_dir, new_name)
                        template_data['image'] = Image.open(img_path).convert('RGB')
                        current_item.setData(Qt.UserRole, template_data)
                        
                        # Update the preview
                        self.on_template_selected(current_item, None)
                        
                        # Dark Mode MessageBox for success
                        msg = QMessageBox(self)
                        msg.setWindowTitle("Success")
                        msg.setText("Template has been renamed")
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
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
                        msg.exec_()
                    else:
                        # Dark Mode MessageBox for error
                        msg = QMessageBox(self)
                        msg.setWindowTitle("Error")
                        msg.setText("Template could not be renamed.\nPlease check the logs for details.")
                        msg.setIcon(QMessageBox.Warning)
                        msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
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
                        msg.exec_()
                except Exception as e:
                    # Dark Mode MessageBox for exception
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Error")
                    msg.setText(f"Error while renaming: {str(e)}")
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
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
                    msg.exec_()
        
    def delete_template(self):
        """Deletes the selected template"""
        if not self.current_template:
            return
            
        reply = QMessageBox.question(self, 'Delete Template', 
            f"Do you really want to delete the template '{self.current_template['name']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                if self.template_manager.delete_template(
                    self.current_template['type'], 
                    self.current_template['name']
                ):
                    # Remove from list
                    self.list_widget.takeItem(self.list_widget.currentRow())
                    QMessageBox.information(self, "Success", 
                        "Template has been deleted", 
                        QMessageBox.Ok)
            except Exception as e:
                QMessageBox.warning(self, "Error", 
                    f"Error while deleting: {str(e)}", 
                    QMessageBox.Ok) 

    def edit_template(self):
        """Starts edit mode for the template"""
        if not self.current_template:
            return
            
        # Enable edit buttons
        self.save_edit_btn.setEnabled(True)
        self.crop_preview_btn.setEnabled(True)
        self.reset_edit_btn.setEnabled(True)
        self.cancel_edit_btn.setEnabled(True)
        
        # Disable other buttons
        self.edit_btn.setEnabled(False)
        self.rename_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        # Start edit mode
        self.image_container.enterEditMode()
            
    def save_selection(self):
        """Saves the selected area"""
        rect = self.image_container.getSelectionRect()
        if not rect:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Please select an area.")
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            msg.setStyleSheet(self.styleSheet())
            msg.exec_()
            return
            
        # Convert QRect to PIL Box
        pixmap = self.image_container.pixmap()
        scale_x = self.current_template['image'].width / pixmap.width()
        scale_y = self.current_template['image'].height / pixmap.height()
        
        box = (
            int(rect.x() * scale_x),
            int(rect.y() * scale_y),
            int((rect.x() + rect.width()) * scale_x),
            int((rect.y() + rect.height()) * scale_y)
        )
        
        # Crop image
        edited_image = self.current_template['image'].crop(box)
        
        # Save the edited image
        img_path = os.path.join(self.template_manager.img_dir, self.current_template['name'])
        edited_image.save(img_path)
        
        # Update the template
        self.current_template['image'] = edited_image
        current_item = self.list_widget.currentItem()
        current_item.setData(Qt.UserRole, self.current_template)
        
        # End edit mode
        self.end_edit_mode()
        
        # Update the preview
        self.on_template_selected(current_item, None)
        
        # Success message
        msg = QMessageBox(self)
        msg.setWindowTitle("Success")
        msg.setText("Selection has been saved")
        msg.setIcon(QMessageBox.Information)
        msg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        msg.setStyleSheet(self.styleSheet())
        msg.exec_()
            
    def reset_selection(self):
        """Resets the selection"""
        self.image_container.selection_start = None
        self.image_container.selection_end = None
        # Restore the original pixmap
        if hasattr(self, 'original_preview_pixmap'):
            self.image_container.setPixmap(self.original_preview_pixmap)
        self.image_container.update()
            
    def cancel_edit(self):
        """Cancels the edit"""
        self.end_edit_mode()
        
    def end_edit_mode(self):
        """Ends edit mode"""
        self.image_container.exitEditMode()
        
        # Disable edit buttons
        self.save_edit_btn.setEnabled(False)
        self.crop_preview_btn.setEnabled(False)
        self.reset_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        
        # Enable normal buttons if a template is selected
        if self.current_template:
            self.edit_btn.setEnabled(True)
            self.rename_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept() 

    def show_crop_preview(self):
        """Shows a preview of the selected area"""
        if not self.current_template:
            return
            
        # Check if a selection exists
        if not self.image_container.selection_start or not self.image_container.selection_end:
            return
            
        try:
            # Get the current pixmap
            current_pixmap = self.image_container.pixmap()
            if not current_pixmap:
                return
                
            # Calculate scaling between original and displayed image
            scale_x = self.current_template['image'].width / current_pixmap.width()
            scale_y = self.current_template['image'].height / current_pixmap.height()
            
            # Get the selection coordinates
            x1 = min(self.image_container.selection_start.x(), self.image_container.selection_end.x())
            y1 = min(self.image_container.selection_start.y(), self.image_container.selection_end.y())
            x2 = max(self.image_container.selection_start.x(), self.image_container.selection_end.x())
            y2 = max(self.image_container.selection_start.y(), self.image_container.selection_end.y())
            
            # Create a QRect for the crop area
            crop_rect = QRect(x1, y1, x2 - x1, y2 - y1)
            
            # Crop the area from the pixmap
            cropped_pixmap = current_pixmap.copy(crop_rect)
            
            # Scale the image if it's too large
            max_size = QSize(500, 400)
            if cropped_pixmap.width() > max_size.width() or cropped_pixmap.height() > max_size.height():
                cropped_pixmap = cropped_pixmap.scaled(max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Update the preview image
            self.image_container.setPixmap(cropped_pixmap)
            
        except Exception as e:
            print(f"Error creating preview: {str(e)}")
            QMessageBox.warning(self, "Error", 
                f"Error creating preview: {str(e)}", 
                QMessageBox.Ok) 