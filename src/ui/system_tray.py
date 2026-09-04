"""System Tray Icon for Transcripter background execution."""

from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget


class TranscripterTrayIcon(QSystemTrayIcon):
    """System Tray icon with quick actions and window toggle."""

    show_window_requested = Signal()
    toggle_recording_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_icon()
        self._init_menu()
        self.activated.connect(self._on_activated)

    def _init_icon(self):
        project_root = Path(__file__).resolve().parent.parent.parent
        icon_path = project_root / "assets" / "icon.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        self.setToolTip("Transcripter — Meeting Detector Active")

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c120e;
                border: 1px solid #1f2d24;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
                color: #f1f5f9;
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #0f2c1c;
                color: #34d399;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1f2d24;
                margin: 4px 2px;
            }
        """)

        # 1. Open Window
        act_open = QAction("🖥 Open Transcripter", menu)
        act_open.triggered.connect(self.show_window_requested.emit)
        menu.addAction(act_open)

        menu.addSeparator()

        # 2. Start / Pause Recording
        self.act_record = QAction("▶ Start Recording", menu)
        self.act_record.triggered.connect(self.toggle_recording_requested.emit)
        menu.addAction(self.act_record)

        # 3. Settings
        act_settings = QAction("⚙ Settings...", menu)
        act_settings.triggered.connect(self.settings_requested.emit)
        menu.addAction(act_settings)

        menu.addSeparator()

        # 4. Exit
        act_exit = QAction("🚪 Exit Transcripter", menu)
        act_exit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_exit)

        self.setContextMenu(menu)

    def update_recording_state(self, is_recording: bool, is_paused: bool = False):
        """Updates the tray menu recording label according to recording state."""
        if is_recording:
            self.act_record.setText("⏸ Pause Recording")
            self.setToolTip("Transcripter — ● Recording Active")
        elif is_paused:
            self.act_record.setText("▶ Resume Recording")
            self.setToolTip("Transcripter — ⏸ Recording Paused")
        else:
            self.act_record.setText("▶ Start Recording")
            self.setToolTip("Transcripter — Meeting Detector Active")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window_requested.emit()
