"""
Chzzk Chat Analyzer - Main Entry Point
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import get_stylesheet


def main():
    """Main application entry point"""
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Chzzk Clip Moment Catcher")
    app.setOrganizationName("ChzzkClipMomentCatcher")
    app.setApplicationVersion("1.0.0")
    
    # Apply stylesheet
    app.setStyleSheet(get_stylesheet())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
