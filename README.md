# File Sorter Application

This application is a PyQt5-based GUI tool for sorting and managing files within a directory. It allows users to scan a directory, view files in categorized tabs (All Files, Images, Videos, Documents, Other), preview files (images and video thumbnails), open files, and delete files (either permanently or by moving them to the recycle bin). The application uses multi-threading for scanning and updating the file list to keep the UI responsive.

## Features

*   **Directory Scanning:** Scans a selected directory and all its subdirectories.
*   **Categorized Tabs:** Displays files in separate tabs based on their type:
    *   All Files
    *   Images (jpg, jpeg, png, gif, bmp, webp)
    *   Videos (mp4, avi, mov, mkv, wmv)
    *   Documents (pdf, docx, txt, xlsx, pptx)
    *   Other Files
*   **File Preview:**
    *   Displays thumbnails for images.
    *   Generates thumbnails for videos (at approximately 1/3 of the video duration).
    *   Shows generic icons for documents and other file types.
*   **File Information:** Shows file name, type, size (in MB), and full path. For single file selections, it also shows the last modified date and time.
*   **Multiple Selection:** Allows selecting multiple files for batch operations.
*   **File Operations:**
    *   **Open:** Opens selected files using the system's default application.  Context-aware open buttons are shown for images and documents when appropriate.
    *   **Delete:** Provides options to either move selected files to the recycle bin or permanently delete them. A confirmation dialog is shown before deletion.
*   **Sorting:** Allows sorting files by name, type, and size within each tab.
*   **Status Bar:** Displays overall directory statistics, including the total number of files, total size, and counts for each file category.
* **Progress Dialogs**: Shows progress during the file scanning and table updating operations.
* **Error Handling**: Catches file access errors and displays warnings for files that could not be deleted.
* **Multi-threaded Operations**: Uses `QThread` for background file scanning and table updates, preventing UI freezes.

## Requirements

This application requires the following Python packages:

*   PyQt5 >= 5.15.0
*   send2trash >= 1.8.0
*   opencv-python >= 4.8.0

These can be installed using pip:

```bash
pip install -r requirements.txt
