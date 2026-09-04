"""Notion-style Floating Meeting Notification Popup Card."""

from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QFont, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QFrame,
)


class MeetingPopupWidget(QWidget):
    """Floating notification popup that prompts to transcribe detected meetings."""

    start_requested = Signal(str, str)  # (app_type, meeting_title)
    dismissed = Signal(str, str)        # (app_type, meeting_title)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.app_type = ""
        self.meeting_title = ""

        # Auto-dismiss countdown (15 seconds)
        self.total_time_ms = 15000
        self.remaining_time_ms = self.total_time_ms
        self.timer_step_ms = 100
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.timeout.connect(self._on_timer_tick)
        self._is_paused = False

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        # Main Container Frame with Shadow and Border
        self.container = QFrame(self)
        self.container.setObjectName("popupContainer")
        self.container.setStyleSheet("""
            QFrame#popupContainer {
                background-color: #0c120e;
                border: 1px solid #10b981;
                border-radius: 8px;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # 1. Header: Badge + Close Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.badge_label = QLabel("● AUTO-DETECT // MEETING")
        self.badge_label.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
        self.badge_label.setStyleSheet("""
            color: #10b981;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-weight: 800;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        header_layout.addWidget(self.badge_label)
        header_layout.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setToolTip("Dismiss")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #f87171;
            }
        """)
        self.btn_close.clicked.connect(self._on_dismiss_clicked)
        header_layout.addWidget(self.btn_close)
        layout.addLayout(header_layout)

        # 2. Meeting Title & Prompt
        self.title_label = QLabel("Meeting detected")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #ffffff; background: transparent;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        desc_label = QLabel("Start real-time recording & transcription?")
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #94a3b8; background: transparent;")
        layout.addWidget(desc_label)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(8)

        self.btn_start = QPushButton("▶ START TRANSCRIBE")
        self.btn_start.setFixedHeight(30)
        self.btn_start.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: 1px solid #34d399;
                border-radius: 4px;
                padding: 0 14px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #10b981;
                border-color: #6ee7b7;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_start)

        self.btn_dismiss = QPushButton("DISMISS")
        self.btn_dismiss.setFixedHeight(30)
        self.btn_dismiss.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
        self.btn_dismiss.setCursor(Qt.PointingHandCursor)
        self.btn_dismiss.setStyleSheet("""
            QPushButton {
                background-color: #141c16;
                color: #94a3b8;
                border: 1px solid #28372e;
                border-radius: 4px;
                padding: 0 12px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d2920;
                color: #f1f5f9;
                border-color: #385242;
            }
        """)
        self.btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        btn_layout.addWidget(self.btn_dismiss)

        layout.addLayout(btn_layout)

        # 4. Slim Auto-dismiss Countdown Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #141c16;
                border: none;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)

        root_layout.addWidget(self.container)
        self.setFixedWidth(360)

    def show_meeting(self, app_type: str, meeting_title: str):
        """Displays the popup with meeting information in the bottom-right of the screen."""
        self.app_type = app_type
        self.meeting_title = meeting_title

        app_upper = app_type.upper()
        self.badge_label.setText(f"● AUTO-DETECT // {app_upper}")
        self.title_label.setText(meeting_title)

        # Reposition to bottom-right of primary screen above taskbar
        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.adjustSize()
            x = geom.right() - self.width() - 20
            y = geom.bottom() - self.height() - 20
            self.move(x, y)

        # Reset timer
        self.remaining_time_ms = self.total_time_ms
        self.progress_bar.setValue(100)
        self._dismiss_timer.start(self.timer_step_ms)

        self.show()
        self.raise_()

    def enterEvent(self, event):
        """Pause auto-dismiss countdown when hovering."""
        super().enterEvent(event)
        self._is_paused = True

    def leaveEvent(self, event):
        """Resume auto-dismiss countdown when mouse leaves."""
        super().leaveEvent(event)
        self._is_paused = False

    def _on_timer_tick(self):
        if self._is_paused:
            return

        self.remaining_time_ms -= self.timer_step_ms
        if self.remaining_time_ms <= 0:
            self._dismiss_timer.stop()
            self.hide()
            self.dismissed.emit(self.app_type, self.meeting_title)
        else:
            pct = int((self.remaining_time_ms / self.total_time_ms) * 100)
            self.progress_bar.setValue(pct)

    def _on_start_clicked(self):
        self._dismiss_timer.stop()
        self.hide()
        self.start_requested.emit(self.app_type, self.meeting_title)

    def _on_dismiss_clicked(self):
        self._dismiss_timer.stop()
        self.hide()
        self.dismissed.emit(self.app_type, self.meeting_title)
