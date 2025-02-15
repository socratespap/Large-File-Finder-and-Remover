import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog,
                           QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                           QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
                           QFrame, QScrollArea, QMessageBox, QProgressDialog)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon, QImage
from send2trash import send2trash
import cv2
import numpy as np

class SizeTableWidgetItem(QTableWidgetItem):
    def __init__(self, size_in_bytes):
        self.size_in_bytes = size_in_bytes
        size_in_mb = size_in_bytes / (1024 * 1024)
        super().__init__(f"{size_in_mb:.2f} MB")

    def __lt__(self, other):
        if isinstance(other, SizeTableWidgetItem):
            return self.size_in_bytes < other.size_in_bytes
        return super().__lt__(other)

class FileScanner(QThread):
    progress = pyqtSignal(int)  # Signal for progress updates
    finished = pyqtSignal(list, dict, int)  # Signal for scan completion
    
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.chunk_size = 100
        
    def run(self):
        files_info = []
        total_size = 0
        file_counts = {'images': 0, 'videos': 0, 'documents': 0, 'other': 0}
        
        # First count total files
        total_files = sum(len(files) for _, _, files in os.walk(self.path))
        processed_files = 0
        
        # Now process files in chunks
        current_chunk = []
        for root, _, files in os.walk(self.path):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    ext = os.path.splitext(file)[1].lower()
                    
                    # Update statistics
                    total_size += size
                    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
                        file_counts['images'] += 1
                    elif ext in {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}:
                        file_counts['videos'] += 1
                    elif ext in {'.pdf', '.docx', '.txt', '.xlsx', '.pptx'}:
                        file_counts['documents'] += 1
                    else:
                        file_counts['other'] += 1
                    
                    current_chunk.append((file, ext, size, file_path))
                    
                    # When chunk is full, sort and extend to main list
                    if len(current_chunk) >= self.chunk_size:
                        current_chunk.sort(key=lambda x: x[0].lower())
                        files_info.extend(current_chunk)
                        current_chunk = []
                    
                    processed_files += 1
                    progress = (processed_files * 100) // total_files
                    self.progress.emit(progress)
                    
                except (OSError, PermissionError):
                    continue
        
        # Add remaining files
        if current_chunk:
            current_chunk.sort(key=lambda x: x[0].lower())
            files_info.extend(current_chunk)
        
        self.finished.emit(files_info, file_counts, total_size)

class TableUpdater(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, files_info, tables, file_extensions):
        super().__init__()
        self.files_info = files_info
        self.tables = tables
        self.file_extensions = file_extensions
        self.chunk_size = 100
        
    def run(self):
        total_files = len(self.files_info)
        processed_files = 0
        
        for i in range(0, total_files, self.chunk_size):
            chunk = self.files_info[i:i + self.chunk_size]
            
            # Process each file in the chunk
            for file, ext, size, file_path in chunk:
                # Update all files table
                row = self.tables['all'].rowCount()
                self.tables['all'].insertRow(row)
                self.tables['all'].setItem(row, 0, QTableWidgetItem(file))
                self.tables['all'].setItem(row, 1, QTableWidgetItem(ext))
                self.tables['all'].setItem(row, 2, SizeTableWidgetItem(size))
                self.tables['all'].setItem(row, 3, QTableWidgetItem(file_path))
                
                # Update category-specific tables
                if ext in self.file_extensions['image']:
                    self._add_to_images_table(file, size, file_path)
                elif ext in self.file_extensions['video']:
                    self._add_to_videos_table(file, size, file_path)
                elif ext in self.file_extensions['doc']:
                    self._add_to_docs_table(file, ext, size, file_path)
                else:
                    self._add_to_other_table(file, ext, size, file_path)
                
                processed_files += 1
                progress = (processed_files * 100) // total_files
                self.progress.emit(progress)
        
        self.finished.emit()
    
    def _add_to_images_table(self, file, size, file_path):
        row = self.tables['images'].rowCount()
        self.tables['images'].insertRow(row)
        self.tables['images'].setItem(row, 0, QTableWidgetItem(file))
        self.tables['images'].setItem(row, 1, SizeTableWidgetItem(size))
        self.tables['images'].setItem(row, 2, QTableWidgetItem(file_path))
    
    def _add_to_videos_table(self, file, size, file_path):
        row = self.tables['videos'].rowCount()
        self.tables['videos'].insertRow(row)
        self.tables['videos'].setItem(row, 0, QTableWidgetItem(file))
        self.tables['videos'].setItem(row, 1, SizeTableWidgetItem(size))
        self.tables['videos'].setItem(row, 2, QTableWidgetItem(file_path))
    
    def _add_to_docs_table(self, file, ext, size, file_path):
        row = self.tables['docs'].rowCount()
        self.tables['docs'].insertRow(row)
        self.tables['docs'].setItem(row, 0, QTableWidgetItem(file))
        self.tables['docs'].setItem(row, 1, QTableWidgetItem(ext))
        self.tables['docs'].setItem(row, 2, SizeTableWidgetItem(size))
        self.tables['docs'].setItem(row, 3, QTableWidgetItem(file_path))
    
    def _add_to_other_table(self, file, ext, size, file_path):
        row = self.tables['other'].rowCount()
        self.tables['other'].insertRow(row)
        self.tables['other'].setItem(row, 0, QTableWidgetItem(file))
        self.tables['other'].setItem(row, 1, QTableWidgetItem(ext))
        self.tables['other'].setItem(row, 2, SizeTableWidgetItem(size))
        self.tables['other'].setItem(row, 3, QTableWidgetItem(file_path))

class FileSorterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Sorter")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create horizontal layout for main content
        content_layout = QHBoxLayout()
        
        # Left panel for file listing
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create top panel with button and label
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        self.select_button = QPushButton("Select Directory")
        self.select_button.clicked.connect(self.select_directory)
        self.path_label = QLabel("No directory selected")
        
        top_layout.addWidget(self.select_button)
        top_layout.addWidget(self.path_label)
        top_layout.addStretch()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tables for each tab
        self.all_files_table = self.create_table(["Name", "Type", "Size", "Path"])
        self.images_table = self.create_table(["Name", "Size", "Path"])
        self.videos_table = self.create_table(["Name", "Size", "Path"])
        self.docs_table = self.create_table(["Name", "Type", "Size", "Path"])
        self.other_files_table = self.create_table(["Name", "Type", "Size", "Path"])
        
        # Add tables to tabs
        self.tabs.addTab(self.all_files_table, "All Files")
        self.tabs.addTab(self.images_table, "Images")
        self.tabs.addTab(self.videos_table, "Videos")
        self.tabs.addTab(self.docs_table, "Documents")
        self.tabs.addTab(self.other_files_table, "Other Files")
        
        # Add widgets to left layout
        left_layout.addWidget(top_panel)
        left_layout.addWidget(self.tabs)
        
        # Right panel for preview
        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_panel)
        
        # Preview widgets
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setMinimumHeight(200)
        
        self.file_title = QLabel()
        self.file_title.setWordWrap(True)
        self.file_datetime = QLabel()
        self.file_size = QLabel()
        self.file_type = QLabel()
        
        # Multi-selection buttons
        self.open_images_button = QPushButton("Open Selected Images")
        self.open_images_button.clicked.connect(lambda: self.open_selected_files(self.image_extensions))
        self.open_images_button.hide()
        
        self.open_documents_button = QPushButton("Open Selected Documents")
        self.open_documents_button.clicked.connect(lambda: self.open_selected_files(self.doc_extensions))
        self.open_documents_button.hide()
        
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_files)
        self.delete_button.hide()
        
        # Play button for single video preview
        self.play_button = QPushButton("Play in External Player")
        self.play_button.clicked.connect(self.play_video)
        self.play_button.hide()
        
        # Add preview widgets to right layout
        right_layout.addWidget(self.preview_image)
        right_layout.addWidget(self.file_title)
        right_layout.addWidget(self.file_datetime)
        right_layout.addWidget(self.file_size)
        right_layout.addWidget(self.file_type)
        right_layout.addWidget(self.play_button)
        right_layout.addWidget(self.open_images_button)
        right_layout.addWidget(self.open_documents_button)
        right_layout.addWidget(self.delete_button)
        right_layout.addStretch()
        
        # Add panels to content layout
        content_layout.addWidget(left_panel, stretch=2)
        content_layout.addWidget(right_panel, stretch=1)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        # Add status label at bottom
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        self.doc_extensions = {'.pdf', '.docx', '.txt', '.xlsx', '.pptx'}

    def create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)  # Allow multiple selection
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.itemSelectionChanged.connect(self.update_preview)
        table.setSortingEnabled(True)
        # Add keypress event for delete key
        table.keyPressEvent = lambda event: self.handle_key_press(event, table)
        return table
        
    def handle_key_press(self, event, table):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_files()
        else:
            # Call the parent class's keyPressEvent for other keys
            QTableWidget.keyPressEvent(table, event)
        
    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.path_label.setText(dir_path)
            self.scan_directory(dir_path)

    def scan_directory(self, path):
        # Clear all tables
        for table in [self.all_files_table, self.images_table, self.videos_table, self.docs_table, self.other_files_table]:
            table.setRowCount(0)
            table.setSortingEnabled(False)  # Disable sorting while loading
        
        # Create progress dialog for file scanning
        scan_progress = QProgressDialog("Scanning files...", "Cancel", 0, 100, self)
        scan_progress.setWindowModality(Qt.WindowModal)
        scan_progress.setAutoClose(True)
        scan_progress.show()
        
        # Create and start file scanner thread
        self.scanner = FileScanner(path)
        self.scanner.progress.connect(scan_progress.setValue)
        self.scanner.finished.connect(lambda files_info, file_counts, total_size: 
            self.on_scan_complete(files_info, file_counts, total_size, path))
        self.scanner.start()
    
    def on_scan_complete(self, files_info, file_counts, total_size, path):
        # Create progress dialog for table updates
        update_progress = QProgressDialog("Updating tables...", "Cancel", 0, 100, self)
        update_progress.setWindowModality(Qt.WindowModal)
        update_progress.setAutoClose(True)
        update_progress.show()
        
        # Create tables dict for the updater
        tables = {
            'all': self.all_files_table,
            'images': self.images_table,
            'videos': self.videos_table,
            'docs': self.docs_table,
            'other': self.other_files_table
        }
        
        # Create file extensions dict
        extensions = {
            'image': self.image_extensions,
            'video': self.video_extensions,
            'doc': self.doc_extensions
        }
        
        # Create and start table updater thread
        self.updater = TableUpdater(files_info, tables, extensions)
        self.updater.progress.connect(update_progress.setValue)
        self.updater.finished.connect(lambda: self.on_update_complete(file_counts, total_size))
        self.updater.start()
    
    def on_update_complete(self, file_counts, total_size):
        # Re-enable sorting
        for table in [self.all_files_table, self.images_table, self.videos_table, self.docs_table, self.other_files_table]:
            table.setSortingEnabled(True)
        
        # Update status label
        total_files = sum(file_counts.values())
        status_text = (
            f"Directory Statistics: {total_files:,} files ({total_size / (1024*1024*1024):.2f} GB) | "
            f"Images: {file_counts['images']:,} | "
            f"Videos: {file_counts['videos']:,} | "
            f"Documents: {file_counts['documents']:,} | "
            f"Other: {file_counts['other']:,}"
        )
        self.status_label.setText(status_text)

    def update_preview(self):
        current_table = self.tabs.currentWidget()
        selected_items = current_table.selectedItems()
        
        if not selected_items:
            self.clear_preview()
            return
        
        # Get number of selected rows (divide by column count to get actual row count)
        selected_rows = len(selected_items) // current_table.columnCount()
        
        # Show delete button for any number of selected files
        self.delete_button.setVisible(True)
        
        # Handle multiple selection
        if selected_rows > 1:
            self.show_multiple_selection_preview(current_table, selected_items)
            return
            
        # Single file preview
        row = current_table.row(selected_items[0])
        file_path = current_table.item(row, current_table.columnCount() - 1).text()
        
        if not os.path.exists(file_path):
            self.clear_preview()
            return
            
        # Get file info
        file_stats = os.stat(file_path)
        size_mb = file_stats.st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(file_stats.st_mtime)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Update file info
        self.file_title.setText(f"Name: {os.path.basename(file_path)}")
        self.file_datetime.setText(f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.file_size.setText(f"Size: {size_mb:.2f} MB")
        self.file_type.setText(f"Type: {file_ext}")
        
        # Handle preview and buttons based on file type
        if file_ext in self.image_extensions:
            self.show_image_preview(file_path)
            self.open_images_button.setVisible(True)
            self.open_documents_button.hide()
        elif file_ext in self.video_extensions:
            self.show_video_preview(file_path)
            self.open_images_button.hide()
            self.open_documents_button.hide()
        else:
            self.show_file_icon(file_ext)
            self.open_images_button.hide()
            self.open_documents_button.setVisible(True)
            
    def show_multiple_selection_preview(self, table, selected_items):
        # Clear single-file preview elements
        self.preview_image.clear()
        self.play_button.hide()
        
        # Get unique selected rows
        selected_rows = set()
        file_types = {'images': 0, 'videos': 0, 'documents': 0, 'other': 0}
        selected_files = []
        
        for item in selected_items:
            row = table.row(item)
            if row not in selected_rows:
                selected_rows.add(row)
                file_path = table.item(row, table.columnCount() - 1).text()
                if os.path.exists(file_path):
                    selected_files.append(file_path)
                    ext = os.path.splitext(file_path)[1].lower()
                    
                    if ext in self.image_extensions:
                        file_types['images'] += 1
                    elif ext in self.video_extensions:
                        file_types['videos'] += 1
                    elif ext in self.doc_extensions:
                        file_types['documents'] += 1
                    else:
                        file_types['other'] += 1
        
        # Calculate total size
        total_size = sum(os.path.getsize(f) for f in selected_files if os.path.exists(f))
        
        # Update preview info for multiple files
        self.file_title.setText(f"Selected: {len(selected_rows)} files")
        self.file_size.setText(f"Total Size: {total_size / (1024 * 1024):.2f} MB")
        self.file_type.setText(f"Types: {file_types['images']} images, {file_types['videos']} videos, "
                             f"{file_types['documents']} documents, {file_types['other']} other")
        self.file_datetime.clear()
        
        # Show/hide appropriate buttons based on selection
        non_zero_types = sum(1 for count in file_types.values() if count > 0)
        
        # Only show type-specific buttons if all selected files are of the same type
        if non_zero_types == 1:
            self.open_images_button.setVisible(file_types['images'] > 0)
            self.open_documents_button.setVisible(file_types['documents'] > 0 or file_types['other'] > 0)
        else:
            self.open_images_button.hide()
            self.open_documents_button.hide()
            
        self.delete_button.setVisible(True)
        
    def open_selected_files(self, filter_extensions=None):
        current_table = self.tabs.currentWidget()
        selected_items = current_table.selectedItems()
        
        if not selected_items:
            return
            
        # Get unique selected rows
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(current_table.row(item))
            
        # Open each selected file
        for row in selected_rows:
            file_path = current_table.item(row, current_table.columnCount() - 1).text()
            if not os.path.exists(file_path):
                continue
                
            if filter_extensions:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in filter_extensions:
                    continue
                    
            os.startfile(file_path)

    def show_image_preview(self, file_path):
        self.play_button.hide()
        pixmap = QPixmap(file_path)
        scaled_pixmap = pixmap.scaled(QSize(280, 280), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_image.setPixmap(scaled_pixmap)
        
    def get_video_thumbnail(self, video_path):
        try:
            # Open the video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            # Get total frames
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                return None

            # Seek to a frame about 1/3 through the video
            target_frame = total_frames // 3
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            # Read the frame
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return None

            # Convert frame from BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Resize frame while maintaining aspect ratio
            height, width = frame_rgb.shape[:2]
            max_size = 256
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))

            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))

            # Convert numpy array to QImage
            height, width, channel = frame_resized.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame_resized.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error generating video thumbnail: {str(e)}")
            return None

    def show_video_preview(self, file_path):
        # Try to get video thumbnail
        thumbnail = self.get_video_thumbnail(file_path)
        
        if thumbnail:
            self.preview_image.setPixmap(thumbnail)
        else:
            # Fallback to generic icon if thumbnail generation fails
            self.preview_image.setPixmap(QIcon.fromTheme("video-x-generic").pixmap(128, 128))
            
        self.play_button.show()
        self.play_button.setProperty("file_path", file_path)
        
    def show_file_icon(self, file_ext):
        self.play_button.hide()
        icon_name = "text-x-generic"
        if file_ext in {'.pdf'}:
            icon_name = "application-pdf"
        elif file_ext in {'.docx', '.doc'}:
            icon_name = "application-msword"
        elif file_ext in {'.xlsx', '.xls'}:
            icon_name = "application-vnd.ms-excel"
        self.preview_image.setPixmap(QIcon.fromTheme(icon_name).pixmap(128, 128))
        
    def clear_preview(self):
        self.preview_image.clear()
        self.file_title.clear()
        self.file_datetime.clear()
        self.file_size.clear()
        self.file_type.clear()
        self.play_button.hide()
        self.open_images_button.hide()
        self.open_documents_button.hide()
        self.delete_button.hide()
        self.status_label.clear()

    def play_video(self):
        file_path = self.play_button.property("file_path")
        if file_path and os.path.exists(file_path):
            os.startfile(file_path)

    def delete_selected_files(self):
        current_table = self.tabs.currentWidget()
        selected_items = current_table.selectedItems()
        
        if not selected_items:
            return
            
        # Get unique selected rows and file paths
        selected_rows = set()
        file_paths = []
        for item in selected_items:
            row = current_table.row(item)
            if row not in selected_rows:
                selected_rows.add(row)
                file_path = current_table.item(row, current_table.columnCount() - 1).text()
                if os.path.exists(file_path):
                    file_paths.append(file_path)
        
        if not file_paths:
            return
            
        # Ask user for confirmation and deletion method
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"Are you sure you want to delete {len(file_paths)} file(s)?")
        msg.setInformativeText("Choose deletion method:")
        msg.setWindowTitle("Confirm Deletion")
        
        # Add buttons for different deletion methods
        recycle_button = msg.addButton("Move to Recycle Bin", QMessageBox.ActionRole)
        permanent_button = msg.addButton("Delete Permanently", QMessageBox.ActionRole)
        cancel_button = msg.addButton("Cancel", QMessageBox.RejectRole)
        
        msg.exec_()
        
        clicked_button = msg.clickedButton()
        
        if clicked_button == cancel_button:
            return
            
        try:
            # Clear selection before deleting to prevent crashes
            current_table.clearSelection()
            
            # Delete files based on selected method
            failed_files = []
            for file_path in file_paths:
                try:
                    if clicked_button == recycle_button:
                        # Normalize path for send2trash
                        normalized_path = os.path.normpath(file_path)
                        send2trash(normalized_path)
                    elif clicked_button == permanent_button:
                        os.remove(file_path)
                except Exception as e:
                    failed_files.append((file_path, str(e)))
            
            # Show errors if any files failed to delete
            if failed_files:
                error_msg = QMessageBox()
                error_msg.setIcon(QMessageBox.Warning)
                error_msg.setWindowTitle("Deletion Warnings")
                error_msg.setText(f"Failed to delete {len(failed_files)} file(s):")
                error_details = "\n".join([f"{path}: {error}" for path, error in failed_files])
                error_msg.setDetailedText(error_details)
                error_msg.exec_()
            
            # Refresh the directory after deletion
            current_path = self.path_label.text()
            if current_path and os.path.exists(current_path):
                self.scan_directory(current_path)
                
        except Exception as e:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setText("Error during deletion process")
            error_msg.setInformativeText(str(e))
            error_msg.setWindowTitle("Error")
            error_msg.exec_()
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileSorterApp()
    window.show()
    sys.exit(app.exec_())
