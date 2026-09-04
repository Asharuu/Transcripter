"""Main Window: Modern Dashboard for Transcripter."""

import os
import sys
import time
from datetime import datetime
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QFont, QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QFrame,
)

from src.core.config import AppConfig
from src.core.credentials import CredentialManager
from src.core.speaker_manager import SpeakerTurnManager, SpeakerTurn
from src.core.session_manager import SessionManager, SessionMetadata
from src.audio.device_manager import AudioDeviceManager
from src.audio.wasapi_capture import AudioEngine
from src.audio.vad_segmenter import AdaptiveVADSegmenter, AudioChannelType, SpeechSegment
from src.audio.synchronizer import AudioSynchronizer
from src.stt.gemini_stt import GeminiSTTEngine
from src.stt.post_processor import ConservativePostProcessor
from src.ui.transcript_widget import TranscriptViewWidget
from src.ui.settings_dialog import SettingsDialog


class WorkerBridge(QObject):
    """Bridge for cross-thread signals from audio and STT threads to Qt GUI."""
    segment_transcribed = Signal(str, str, float, float)  # speaker, text, start_t, end_t
    audio_level_updated = Signal(float)                    # rms volume 0.0 - 1.0
    status_message = Signal(str)                          # status bar message


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transcripter — Real-time Desktop Transcription")
        self.resize(1100, 720)
        self.setMinimumSize(850, 550)

        # Core Engines & State
        self.config = AppConfig.load()
        self.turn_manager = SpeakerTurnManager()
        self.session_manager = SessionManager()
        self.audio_engine = AudioEngine()
        self.stt_engine = GeminiSTTEngine(model_name=self.config.stt_model)
        self.post_processor = ConservativePostProcessor(model_name=self.config.stt_model)

        self.bridge = WorkerBridge()
        self.bridge.segment_transcribed.connect(self._on_segment_transcribed)
        self.bridge.audio_level_updated.connect(self._on_audio_level_updated)
        self.bridge.status_message.connect(self._on_status_message)

        # VAD Segmenters for each physical channel
        self.mic_segmenter = AdaptiveVADSegmenter(
            channel=AudioChannelType.LOCAL,
            speaker_label="Speaker 1 (You)",
            silence_threshold_sec=self.config.audio.vad_silence_seconds,
        )
        self.system_segmenter = AdaptiveVADSegmenter(
            channel=AudioChannelType.REMOTE,
            speaker_label="Speaker 2 (Remote)",
            silence_threshold_sec=self.config.audio.vad_silence_seconds,
        )

        # Session timing & state
        self.is_recording = False
        self.session_start_time = 0.0
        self.active_session_id: str | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        self._init_ui()
        self._load_recent_sessions()
        self._check_api_key_status()

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f19;
            }
            QWidget {
                color: #f1f5f9;
                font-family: 'Segoe UI', sans-serif;
            }
            QSplitter::handle {
                background-color: #1e293b;
                width: 1px;
            }
            QListWidget {
                background-color: #0f172a;
                border: none;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 4px;
                color: #cbd5e1;
            }
            QListWidget::item:hover {
                background-color: #1e293b;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton#primaryAction {
                background-color: #2563eb;
                border: none;
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton#primaryAction:hover {
                background-color: #1d4ed8;
            }
            QPushButton#stopAction {
                background-color: #dc2626;
                border: none;
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton#stopAction:hover {
                background-color: #b91c1c;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 13px;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 12px;
                color: #94a3b8;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 3px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 3px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)

        # ----------------- LEFT SIDEBAR -----------------
        self.sidebar = QWidget()
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(280)
        self.sidebar.setStyleSheet("background-color: #0f172a; border-right: 1px solid #1e293b;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(12)

        # App Brand Header with Pin & Collapse controls
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(6)

        brand_label = QLabel("Transcripter")
        brand_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        brand_label.setStyleSheet("color: #38bdf8;")
        brand_layout.addWidget(brand_label)
        brand_layout.addStretch()

        # Pin / Unpin Button (📌)
        self.is_sidebar_pinned = True
        self.btn_pin_sidebar = QPushButton("📌")
        self.btn_pin_sidebar.setToolTip("Pin / Unpin Sidebar")
        self.btn_pin_sidebar.setFixedSize(30, 30)
        self.btn_pin_sidebar.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_pin_sidebar.clicked.connect(self._toggle_pin_sidebar)
        brand_layout.addWidget(self.btn_pin_sidebar)

        # Collapse Sidebar Button (◀ / ≡)
        self.btn_collapse_sidebar = QPushButton("◀")
        self.btn_collapse_sidebar.setToolTip("Tutup / Collapse Sidebar")
        self.btn_collapse_sidebar.setFixedSize(30, 30)
        self.btn_collapse_sidebar.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_collapse_sidebar.clicked.connect(self._toggle_sidebar)
        brand_layout.addWidget(self.btn_collapse_sidebar)

        sidebar_layout.addLayout(brand_layout)

        # + New Session Button
        self.btn_new = QPushButton("+ New Session")
        self.btn_new.setObjectName("primaryAction")
        self.btn_new.clicked.connect(self._new_session)
        sidebar_layout.addWidget(self.btn_new)

        # Recent Sessions Header
        recent_label = QLabel("Recent Sessions")
        recent_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        recent_label.setStyleSheet("color: #94a3b8; margin-top: 8px;")
        sidebar_layout.addWidget(recent_label)

        # Sessions List
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self._on_session_clicked)
        sidebar_layout.addWidget(self.session_list)

        # Settings button at bottom of sidebar
        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_settings.clicked.connect(self._open_settings)
        sidebar_layout.addWidget(self.btn_settings)

        self.splitter.addWidget(self.sidebar)

        # ----------------- RIGHT WORKSPACE -----------------
        workspace = QWidget()
        workspace.setStyleSheet("background-color: #0b0f19;")
        ws_layout = QVBoxLayout(workspace)
        ws_layout.setContentsMargins(20, 16, 20, 16)
        ws_layout.setSpacing(14)

        # Top Bar: Session Title & Audio Controls
        top_bar = QHBoxLayout()

        # Workspace Toggle Sidebar Button (visible when sidebar is closed)
        self.btn_open_sidebar = QPushButton("☰")
        self.btn_open_sidebar.setToolTip("Buka / Expand Sidebar")
        self.btn_open_sidebar.setFixedSize(32, 32)
        self.btn_open_sidebar.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_open_sidebar.clicked.connect(self._toggle_sidebar)
        self.btn_open_sidebar.setVisible(False)
        top_bar.addWidget(self.btn_open_sidebar)

        # Session Title Editor
        self.title_input = QLineEdit("Untitled Session")
        self.title_input.setPlaceholderText("Enter session title (e.g. Dasar OOP)...")
        self.title_input.setMinimumWidth(260)
        top_bar.addWidget(self.title_input)

        top_bar.addSpacing(15)

        # Audio source checkboxes
        self.chk_system = QCheckBox("System Audio")
        self.chk_system.setChecked(self.config.system_audio_enabled)
        self.chk_system.toggled.connect(self._on_source_toggled)
        top_bar.addWidget(self.chk_system)

        self.chk_mic = QCheckBox("Microphone")
        self.chk_mic.setChecked(self.config.microphone_enabled)
        self.chk_mic.toggled.connect(self._on_source_toggled)
        top_bar.addWidget(self.chk_mic)

        top_bar.addStretch()

        # Timer Badge
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.timer_label.setStyleSheet("color: #94a3b8; padding: 4px 8px;")
        top_bar.addWidget(self.timer_label)

        # Start / Stop Button
        self.btn_record = QPushButton("▶ START")
        self.btn_record.setObjectName("primaryAction")
        self.btn_record.setMinimumWidth(100)
        self.btn_record.clicked.connect(self._toggle_recording)
        top_bar.addWidget(self.btn_record)

        ws_layout.addLayout(top_bar)

        # Status row: VU meter & quick export buttons
        status_row = QHBoxLayout()

        # Recording state badge
        self.state_badge = QLabel("READY")
        self.state_badge.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        status_row.addWidget(self.state_badge)

        # VU Meter
        self.vu_meter = QProgressBar()
        self.vu_meter.setRange(0, 100)
        self.vu_meter.setValue(0)
        self.vu_meter.setTextVisible(False)
        self.vu_meter.setFixedWidth(120)
        status_row.addWidget(self.vu_meter)

        # Status text
        self.status_text = QLabel("Press START to begin listening")
        self.status_text.setStyleSheet("color: #64748b; font-size: 12px;")
        status_row.addWidget(self.status_text)

        status_row.addStretch()

        # Export Buttons
        self.btn_export_md = QPushButton("Export .md")
        self.btn_export_md.clicked.connect(self._export_markdown)
        status_row.addWidget(self.btn_export_md)

        self.btn_export_txt = QPushButton("Export .txt")
        self.btn_export_txt.clicked.connect(self._export_txt)
        status_row.addWidget(self.btn_export_txt)

        ws_layout.addLayout(status_row)

        # Center Transcript View
        self.transcript_widget = TranscriptViewWidget()
        self.transcript_widget.turn_edited.connect(self._on_turn_edited)
        ws_layout.addWidget(self.transcript_widget, 1)

        self.splitter.addWidget(workspace)
        self.splitter.setSizes([240, 860])
        main_layout.addWidget(self.splitter)

    # ----------------- RECORDING WORKFLOW -----------------

    def _toggle_recording(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        if not CredentialManager.has_api_key():
            reply = QMessageBox.warning(
                self,
                "API Key Missing",
                "You haven't configured a Gemini API key yet. Open Settings now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._open_settings()
            return

        if not self.chk_system.isChecked() and not self.chk_mic.isChecked():
            QMessageBox.warning(self, "No Audio Source", "Please select at least System Audio or Microphone.")
            return

        # Prepare device indices
        adm = AudioDeviceManager()
        sys_idx = None
        mic_idx = None

        if self.chk_system.isChecked():
            if self.config.system_audio_device_index is not None:
                sys_idx = self.config.system_audio_device_index
            else:
                default_loop = adm.get_default_loopback_device()
                sys_idx = default_loop.index if default_loop else None

        if self.chk_mic.isChecked():
            if self.config.microphone_device_index is not None:
                mic_idx = self.config.microphone_device_index
            else:
                default_mic = adm.get_default_microphone_device()
                mic_idx = default_mic.index if default_mic else None

        adm.close()

        # Start audio engine
        started = self.audio_engine.start(
            system_audio_index=sys_idx,
            mic_index=mic_idx,
            on_audio_chunk=self._on_raw_audio_chunk,
        )

        if not started:
            QMessageBox.critical(self, "Audio Error", "Failed to initialize audio capture devices.")
            return

        # Reset state & turn manager
        self.mic_segmenter.reset()
        self.system_segmenter.reset()
        self.is_recording = True
        self.session_start_time = time.time()
        self.session_duration = 0.0

        # UI updates
        self.btn_record.setText("■ STOP")
        self.btn_record.setObjectName("stopAction")
        self.btn_record.setStyle(self.btn_record.style())
        self.state_badge.setText("● RECORDING")
        self.state_badge.setStyleSheet("background-color: #991b1b; color: #ffffff; font-weight: bold; padding: 3px 8px; border-radius: 4px;")
        self.status_text.setText("Listening & buffering speech...")
        self.chk_system.setEnabled(False)
        self.chk_mic.setEnabled(False)
        self.timer.start(1000)

    def _stop_recording(self):
        self.is_recording = False
        self.timer.stop()
        self.audio_engine.stop()

        now = time.time()
        if self.session_start_time > 0:
            self.session_duration = max(0.0, now - self.session_start_time)
            mins, secs = divmod(int(self.session_duration), 60)
            hours, mins = divmod(mins, 60)
            dur_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
            self.timer_label.setText(dur_str)

        # Flush any remaining audio in segmenters
        mic_flush = self.mic_segmenter.flush(now)
        sys_flush = self.system_segmenter.flush(now)

        if mic_flush:
            self._process_speech_segment_async(mic_flush)
        if sys_flush:
            self._process_speech_segment_async(sys_flush)

        # UI updates
        self.btn_record.setText("▶ START")
        self.btn_record.setObjectName("primaryAction")
        self.btn_record.setStyle(self.btn_record.style())
        self.state_badge.setText("COMPLETED")
        self.state_badge.setStyleSheet("background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 3px 8px; border-radius: 4px;")
        self.status_text.setText("Session complete. You can edit the transcript and export.")
        self.vu_meter.setValue(0)
        self.chk_system.setEnabled(True)
        self.chk_mic.setEnabled(True)

        # Finalize turn
        self.turn_manager.finalize_active_turn()

        # Auto-save session to history
        self._save_current_session()

    def _on_raw_audio_chunk(self, pcm16: bytes, timestamp: float, channel: AudioChannelType):
        """Callback from audio capture threads."""
        if not self.is_recording:
            return

        # Update VU Meter volume
        rms = AudioSynchronizer.calculate_rms_volume(pcm16)
        self.bridge.audio_level_updated.emit(rms)

        # Route to appropriate VAD segmenter
        segment = None
        if channel == AudioChannelType.LOCAL:
            segment = self.mic_segmenter.process_frame(pcm16, timestamp)
        else:
            segment = self.system_segmenter.process_frame(pcm16, timestamp)

        if segment:
            # Process segment in worker thread
            self._process_speech_segment_async(segment)

    def _process_speech_segment_async(self, segment: SpeechSegment):
        """Asynchronously transcribes audio segment and posts back to GUI."""
        import threading

        def run():
            self.bridge.status_message.emit(f"Transcribing {segment.speaker_label} speech segment...")
            raw_text = self.stt_engine.transcribe(segment.pcm_data)

            if not raw_text.strip():
                return

            # Apply conservative post-processor if enabled
            final_text = raw_text
            if self.config.ai_post_processing_enabled:
                final_text = self.post_processor.process(raw_text)

            rel_start = max(0.0, segment.start_time - self.session_start_time)
            rel_end = max(rel_start + segment.duration, segment.end_time - self.session_start_time)

            self.bridge.segment_transcribed.emit(
                segment.speaker_label,
                final_text,
                rel_start,
                rel_end,
            )
            self.bridge.status_message.emit("Listening & buffering speech...")

        threading.Thread(target=run, daemon=True).start()

    # ----------------- BRIDGE SLOTS -----------------

    @Slot(str, str, float, float)
    def _on_segment_transcribed(self, speaker: str, text: str, start_t: float, end_t: float):
        """Ingest newly transcribed segment into the turn manager and update UI."""
        is_same_speaker = (
            self.turn_manager.active_turn is not None
            and self.turn_manager.active_turn.speaker == speaker
            and not self.turn_manager.active_turn.is_finalized
        )

        turn = self.turn_manager.add_segment(speaker, text, start_t, end_t)
        if is_same_speaker:
            self.transcript_widget.update_turn(turn)
        else:
            self.transcript_widget.add_turn(turn)

        # Update saved session in background to prevent race conditions on stop
        self._save_current_session()

    @Slot(float)
    def _on_audio_level_updated(self, rms: float):
        val = int(rms * 100)
        self.vu_meter.setValue(val)

    @Slot(str)
    def _on_status_message(self, msg: str):
        self.status_text.setText(msg)

    # ----------------- SESSION & EXPORT -----------------

    def _toggle_sidebar(self):
        """Toggle sidebar collapsed or expanded."""
        sizes = self.splitter.sizes()
        if sizes[0] > 0:
            # Collapse sidebar
            self._prev_sidebar_width = sizes[0]
            self.splitter.setSizes([0, sizes[0] + sizes[1]])
            self.btn_open_sidebar.setVisible(True)
        else:
            # Expand sidebar
            restore_w = getattr(self, "_prev_sidebar_width", 240)
            if restore_w <= 0:
                restore_w = 240
            rem = max(100, sizes[1] - restore_w)
            self.splitter.setSizes([restore_w, rem])
            self.btn_open_sidebar.setVisible(False)

    def _toggle_pin_sidebar(self):
        """Toggle pinned state of the sidebar."""
        self.is_sidebar_pinned = not self.is_sidebar_pinned
        if self.is_sidebar_pinned:
            self.btn_pin_sidebar.setText("📌")
            self.btn_pin_sidebar.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    border: 1px solid #3b82f6;
                    border-radius: 6px;
                    padding: 0;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
            """)
            self.btn_pin_sidebar.setToolTip("Sidebar is pinned (Always Open)")
        else:
            self.btn_pin_sidebar.setText("📍")
            self.btn_pin_sidebar.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 0;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #334155;
                }
            """)
            self.btn_pin_sidebar.setToolTip("Sidebar is unpinned (Click to pin)")

    def _update_timer(self):
        elapsed = time.time() - self.session_start_time
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            self.timer_label.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
        else:
            self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _new_session(self):
        if self.is_recording:
            self._stop_recording()
        self.active_session_id = None
        self.turn_manager.reset()
        self.transcript_widget.clear()
        self.title_input.setText("Untitled Session")
        self.timer_label.setText("00:00")
        self.status_text.setText("New session ready. Press START.")

    def _save_current_session(self):
        if not self.turn_manager.turns:
            return

        if self.is_recording and self.session_start_time > 0:
            duration = max(0.0, time.time() - self.session_start_time)
        else:
            duration = getattr(self, "session_duration", 0.0)
            if duration <= 0.0 and self.session_start_time > 0:
                duration = max(0.0, time.time() - self.session_start_time)

        title = self.title_input.text().strip() or "Untitled Session"
        dt = datetime.fromtimestamp(self.session_start_time if self.session_start_time > 0 else time.time())

        md_content = self.turn_manager.to_markdown(title, dt, duration)
        txt_content = self.turn_manager.to_plain_text(title, dt, duration)

        meta = self.session_manager.save_or_update_session(
            session_id=self.active_session_id,
            title=title,
            duration_seconds=duration,
            system_audio_enabled=self.chk_system.isChecked(),
            microphone_enabled=self.chk_mic.isChecked(),
            markdown_text=md_content,
            plain_text=txt_content,
        )
        self.active_session_id = meta.id
        self._load_recent_sessions()

    def _load_recent_sessions(self):
        self.session_list.clear()
        sessions = self.session_manager.list_sessions()
        for s in sessions[:20]:
            item = QListWidgetItem(f"{s.title}")
            item.setData(Qt.UserRole, s.id)
            self.session_list.addItem(item)

    def _on_session_clicked(self, item: QListWidgetItem):
        sess_id = item.data(Qt.UserRole)
        sessions = self.session_manager.list_sessions()
        for s in sessions:
            if s.id == sess_id and s.markdown_file and os.path.exists(s.markdown_file):
                if self.is_recording:
                    self._stop_recording()

                self.active_session_id = s.id
                self.title_input.setText(s.title)

                # Format session duration onto timer label
                mins, secs = divmod(int(s.duration_seconds), 60)
                hours, mins = divmod(mins, 60)
                dur_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
                self.timer_label.setText(dur_str)

                # Read and parse markdown into turns
                try:
                    with open(s.markdown_file, "r", encoding="utf-8") as f:
                        md_text = f.read()
                    turns = self.turn_manager.load_from_markdown(md_text)
                    self.transcript_widget.clear()
                    for t in turns:
                        self.transcript_widget.add_turn(t)
                    self.status_text.setText(f"Loaded past session: {s.title} ({len(turns)} turns)")
                except Exception as e:
                    self.status_text.setText(f"Error loading transcript: {e}")

                # If sidebar is not pinned, auto-collapse on selection to give full view
                if not self.is_sidebar_pinned:
                    self.splitter.setSizes([0, 1000])
                    self.btn_open_sidebar.setVisible(True)
                break

    def _export_markdown(self):
        title = self.title_input.text().strip() or "Transcript"
        if self.is_recording and self.session_start_time > 0:
            duration = max(0.0, time.time() - self.session_start_time)
        else:
            duration = getattr(self, "session_duration", 0.0)
            if duration <= 0.0 and self.session_start_time > 0:
                duration = max(0.0, time.time() - self.session_start_time)
        dt = datetime.fromtimestamp(self.session_start_time if self.session_start_time > 0 else time.time())
        md = self.turn_manager.to_markdown(title, dt, duration)

        path, _ = QFileDialog.getSaveFileName(self, "Export Markdown", f"{title}.md", "Markdown Files (*.md)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(md)
                QMessageBox.information(self, "Export Success", f"Transcript saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save file: {e}")

    def _export_txt(self):
        title = self.title_input.text().strip() or "Transcript"
        if self.is_recording and self.session_start_time > 0:
            duration = max(0.0, time.time() - self.session_start_time)
        else:
            duration = getattr(self, "session_duration", 0.0)
            if duration <= 0.0 and self.session_start_time > 0:
                duration = max(0.0, time.time() - self.session_start_time)
        dt = datetime.fromtimestamp(self.session_start_time if self.session_start_time > 0 else time.time())
        txt = self.turn_manager.to_plain_text(title, dt, duration)

        path, _ = QFileDialog.getSaveFileName(self, "Export Plain Text", f"{title}.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
                QMessageBox.information(self, "Export Success", f"Transcript saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save file: {e}")

    def _on_turn_edited(self, turn_id: int, new_text: str):
        for turn in self.turn_manager.turns:
            if turn.id == turn_id:
                turn.update_text(new_text)
                # Auto-save changes back to storage if viewing a saved session or finished recording
                if not self.is_recording and self.turn_manager.turns:
                    self._save_current_session()
                break

    def _on_source_toggled(self):
        self.config.system_audio_enabled = self.chk_system.isChecked()
        self.config.microphone_enabled = self.chk_mic.isChecked()
        self.config.save()

    def _open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self):
        self.config = AppConfig.load()
        self.stt_engine.model_name = self.config.stt_model
        self.post_processor.model_name = self.config.stt_model
        self.mic_segmenter.silence_threshold_sec = self.config.audio.vad_silence_seconds
        self.system_segmenter.silence_threshold_sec = self.config.audio.vad_silence_seconds
        self._check_api_key_status()

    def _check_api_key_status(self):
        if not CredentialManager.has_api_key():
            self.status_text.setText("⚠ Gemini API key not configured. Click Settings to enter key.")
