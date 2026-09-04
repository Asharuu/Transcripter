"""Settings Dialog: API key management via Windows DPAPI and Audio Device selection."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QDoubleSpinBox,
)

from src.core.credentials import CredentialManager
from src.core.config import AppConfig
from src.audio.device_manager import AudioDeviceManager


class SettingsDialog(QDialog):
    """Configuration dialog for API keys, devices, and AI behavior."""

    settings_saved = Signal()

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings — Transcripter")
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: bold;
                color: #38bdf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #cbd5e1;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 6px 10px;
                color: #f8fafc;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 7px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#dangerBtn {
                background-color: #dc2626;
            }
            QPushButton#dangerBtn:hover {
                background-color: #b91c1c;
            }
            QPushButton#secondaryBtn {
                background-color: #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
        """)

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 1. API KEY SECTION
        api_group = QGroupBox("Gemini API Key (Windows Credential Locker)")
        api_layout = QVBoxLayout(api_group)

        api_desc = QLabel(
            "API keys are stored securely using Windows Credential Manager (DPAPI). "
            "They will never be committed to Git or stored in plaintext."
        )
        api_desc.setWordWrap(True)
        api_desc.setStyleSheet("color: #94a3b8; font-size: 11px; margin-bottom: 6px;")
        api_layout.addWidget(api_desc)

        key_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Paste your Google Gemini API key here...")
        key_row.addWidget(self.api_key_input)

        self.btn_show_key = QPushButton("Show")
        self.btn_show_key.setObjectName("secondaryBtn")
        self.btn_show_key.setCheckable(True)
        self.btn_show_key.toggled.connect(self._toggle_show_key)
        key_row.addWidget(self.btn_show_key)
        api_layout.addLayout(key_row)

        # Status & Action Buttons
        status_row = QHBoxLayout()
        self.status_label = QLabel("Checking status...")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        self.btn_test_key = QPushButton("Test Connection")
        self.btn_test_key.setObjectName("secondaryBtn")
        self.btn_test_key.clicked.connect(self._test_key)
        status_row.addWidget(self.btn_test_key)

        self.btn_delete_key = QPushButton("Remove Key")
        self.btn_delete_key.setObjectName("dangerBtn")
        self.btn_delete_key.clicked.connect(self._delete_key)
        status_row.addWidget(self.btn_delete_key)

        api_layout.addLayout(status_row)
        layout.addWidget(api_group)

        # 2. AUDIO DEVICES SECTION
        audio_group = QGroupBox("Audio Devices")
        form_layout = QFormLayout(audio_group)

        # System Audio Dropdown
        self.combo_system = QComboBox()
        form_layout.addRow("System Audio (Loopback):", self.combo_system)

        # Microphone Dropdown
        self.combo_mic = QComboBox()
        form_layout.addRow("Microphone:", self.combo_mic)

        layout.addWidget(audio_group)

        # 3. AI & TRANSCRIPTION BEHAVIOR
        ai_group = QGroupBox("Speech & AI Settings")
        ai_layout = QFormLayout(ai_group)

        self.combo_model = QComboBox()
        self.combo_model.addItems(["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest"])
        ai_layout.addRow("STT Model:", self.combo_model)

        self.chk_post_process = QCheckBox("Enable Conservative AI Post-Processing (Punctuation & Typos)")
        self.chk_post_process.setStyleSheet("color: #cbd5e1;")
        ai_layout.addRow("", self.chk_post_process)

        self.spin_vad_pause = QDoubleSpinBox()
        self.spin_vad_pause.setRange(0.8, 4.0)
        self.spin_vad_pause.setSingleStep(0.2)
        self.spin_vad_pause.setSuffix(" sec")
        ai_layout.addRow("Pause Threshold (VAD):", self.spin_vad_pause)

        layout.addWidget(ai_group)

        # 4. BOTTOM ACTION BUTTONS
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _toggle_show_key(self, checked: bool):
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.btn_show_key.setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.btn_show_key.setText("Show")

    def _load_values(self):
        # Load API key
        key = CredentialManager.get_api_key()
        if key:
            self.api_key_input.setText(key)
            self.status_label.setText("✓ API key stored in DPAPI")
            self.status_label.setStyleSheet("color: #4ade80;")
        else:
            self.status_label.setText("⚠ No API key configured")
            self.status_label.setStyleSheet("color: #f87171;")

        # Populate devices
        adm = AudioDeviceManager()
        loopbacks = adm.list_loopback_devices()
        self.combo_system.addItem("System Default Output", None)
        for dev in loopbacks:
            self.combo_system.addItem(f"{dev.name} {'(Default)' if dev.is_default else ''}", dev.index)

        mics = adm.list_microphone_devices()
        self.combo_mic.addItem("System Default Microphone", None)
        for dev in mics:
            self.combo_mic.addItem(f"{dev.name} {'(Default)' if dev.is_default else ''}", dev.index)
        adm.close()

        # Set selections from config
        if self.config.system_audio_device_index is not None:
            idx = self.combo_system.findData(self.config.system_audio_device_index)
            if idx >= 0:
                self.combo_system.setCurrentIndex(idx)

        if self.config.microphone_device_index is not None:
            idx = self.combo_mic.findData(self.config.microphone_device_index)
            if idx >= 0:
                self.combo_mic.setCurrentIndex(idx)

        # AI settings
        model_idx = self.combo_model.findText(self.config.stt_model)
        if model_idx >= 0:
            self.combo_model.setCurrentIndex(model_idx)
        self.chk_post_process.setChecked(self.config.ai_post_processing_enabled)
        self.spin_vad_pause.setValue(self.config.audio.vad_silence_seconds)

    def _test_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key Missing", "Please enter an API key first.")
            return

        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: #38bdf8;")
        self.btn_test_key.setEnabled(False)

        valid, msg = CredentialManager.test_api_key(key)
        self.btn_test_key.setEnabled(True)

        if valid:
            self.status_label.setText("✓ Connection Successful!")
            self.status_label.setStyleSheet("color: #4ade80;")
            QMessageBox.information(self, "Success", msg)
        else:
            self.status_label.setText("✕ Connection Failed")
            self.status_label.setStyleSheet("color: #f87171;")
            QMessageBox.critical(self, "Connection Error", msg)

    def _delete_key(self):
        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            "Are you sure you want to remove the stored API key from Windows Credential Manager?",
        )
        if confirm == QMessageBox.Yes:
            CredentialManager.delete_api_key()
            self.api_key_input.clear()
            self.status_label.setText("⚠ API key removed")
            self.status_label.setStyleSheet("color: #f87171;")

    def _save_settings(self):
        # Save API key
        key = self.api_key_input.text().strip()
        if key:
            CredentialManager.save_api_key(key)

        # Save audio devices
        self.config.system_audio_device_index = self.combo_system.currentData()
        self.config.microphone_device_index = self.combo_mic.currentData()

        # Save AI settings
        self.config.stt_model = self.combo_model.currentText()
        self.config.ai_post_processing_enabled = self.chk_post_process.isChecked()
        self.config.audio.vad_silence_seconds = self.spin_vad_pause.value()

        self.config.save()
        self.settings_saved.emit()
        self.accept()
