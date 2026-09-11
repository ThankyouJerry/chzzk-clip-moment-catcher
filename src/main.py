"""
Chzzk Chat Analyzer - Main Entry Point
"""
import csv
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication

from core.analyzer import ChatAnalyzer
from ui.main_window import MainWindow
from ui.styles import get_stylesheet
from version import APP_NAME, APP_VERSION


def run_functional_smoke_test() -> int:
    """Exercise frozen CSV loading, analysis, and export without opening a window."""
    with TemporaryDirectory(prefix="clip-moment-smoke-") as directory:
        root = Path(directory)
        source = root / "chat.csv"
        rows = []
        for minute, count in enumerate((2, 2, 8, 2, 2)):
            for index in range(count):
                rows.append({
                    "재생시간": f"00:{minute:02d}:{index:02d}",
                    "닉네임": f"사용자{index % 5}",
                    "id": f"user-{index % 5}",
                    "메시지": "ㅋㅋ",
                })
        with source.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("재생시간", "닉네임", "id", "메시지"))
            writer.writeheader()
            writer.writerows(rows)

        analyzer = ChatAnalyzer()
        analyzer.load_csv(source)
        result = analyzer.analyze_chat_density(1, sensitivity=3)
        if result["status"] != "ok" or not result["events"]:
            raise RuntimeError("functional smoke analysis produced no event")
        output = root / "markers.fcpxml"
        analyzer.export_fcpxml(output, "density", fps=30)
        if ET.parse(output).getroot().tag != "fcpxml":
            raise RuntimeError("functional smoke export is not valid XML")
    return 0


def main():
    """Main application entry point"""
    if "--smoke-test" in sys.argv:
        raise SystemExit(run_functional_smoke_test())

    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("ChzzkClipMomentCatcher")
    app.setApplicationVersion(APP_VERSION)
    
    # Apply stylesheet
    app.setStyleSheet(get_stylesheet())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
