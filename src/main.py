"""Transcripter Desktop Application Entrypoint."""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ctypes
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main():
    # Set explicit AppUserModelID on Windows for clean taskbar grouping and custom icon
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "Asharuu.Transcripter.Desktop.1.0"
            )
        except Exception:
            pass

    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Transcripter")
    app.setOrganizationName("Asharuu")

    # Set application icon
    icon_path = PROJECT_ROOT / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set default modern font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Set modern dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0b0f19"))
    palette.setColor(QPalette.WindowText, QColor("#f1f5f9"))
    palette.setColor(QPalette.Base, QColor("#0f172a"))
    palette.setColor(QPalette.AlternateBase, QColor("#1e293b"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.Text, QColor("#f1f5f9"))
    palette.setColor(QPalette.Button, QColor("#1e293b"))
    palette.setColor(QPalette.ButtonText, QColor("#f8fafc"))
    palette.setColor(QPalette.BrightText, QColor("#ef4444"))
    palette.setColor(QPalette.Link, QColor("#38bdf8"))
    palette.setColor(QPalette.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
