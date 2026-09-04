"""Application configuration and persistent preferences."""

import os
from pathlib import Path
from dataclasses import dataclass, field
import json


def get_app_data_dir() -> Path:
    """Returns the application data directory under Windows AppData/Roaming or user home."""
    app_data = os.getenv("APPDATA")
    if app_data:
        base_dir = Path(app_data) / "Transcripter"
    else:
        base_dir = Path.home() / ".transcripter"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_transcripts_dir() -> Path:
    """Directory where exported and local transcripts are saved."""
    t_dir = get_app_data_dir() / "transcripts"
    t_dir.mkdir(parents=True, exist_ok=True)
    return t_dir


def get_logs_dir() -> Path:
    """Directory where application diagnostic logs are stored."""
    l_dir = get_app_data_dir() / "logs"
    l_dir.mkdir(parents=True, exist_ok=True)
    return l_dir


@dataclass
class AudioSettings:
    sample_rate: int = 16000
    chunk_ms: int = 30  # Frame size in milliseconds for VAD (10, 20, or 30ms)
    vad_silence_seconds: float = 1.5  # Silence pause to trigger speech completion
    min_segment_seconds: float = 5.0  # Minimum audio duration before sending to STT
    max_segment_seconds: float = 25.0  # Maximum audio duration before forcing a cut
    speaker_turn_timeout: float = 7.0  # Max pause before active speaker turn is finalized


@dataclass
class AppConfig:
    # Selected audio device IDs (None = system default)
    system_audio_device_index: int | None = None
    microphone_device_index: int | None = None
    
    # Audio source toggles
    system_audio_enabled: bool = True
    microphone_enabled: bool = True

    # STT & AI Settings
    stt_model: str = "gemini-3.5-flash-lite"
    ai_post_processing_enabled: bool = True
    auto_detect_meetings: bool = True

    # Windows Startup & System Tray Integration
    launch_at_startup: bool = True
    start_minimized_to_tray: bool = True
    minimize_to_tray_on_close: bool = False

    # Audio Engine Tuning
    audio: AudioSettings = field(default_factory=AudioSettings)

    def save(self, config_file: Path | None = None) -> None:
        if config_file is None:
            config_file = get_app_data_dir() / "config.json"
        data = {
            "system_audio_device_index": self.system_audio_device_index,
            "microphone_device_index": self.microphone_device_index,
            "system_audio_enabled": self.system_audio_enabled,
            "microphone_enabled": self.microphone_enabled,
            "stt_model": self.stt_model,
            "ai_post_processing_enabled": self.ai_post_processing_enabled,
            "auto_detect_meetings": self.auto_detect_meetings,
            "launch_at_startup": self.launch_at_startup,
            "start_minimized_to_tray": self.start_minimized_to_tray,
            "minimize_to_tray_on_close": self.minimize_to_tray_on_close,
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "chunk_ms": self.audio.chunk_ms,
                "vad_silence_seconds": self.audio.vad_silence_seconds,
                "min_segment_seconds": self.audio.min_segment_seconds,
                "max_segment_seconds": self.audio.max_segment_seconds,
                "speaker_turn_timeout": self.audio.speaker_turn_timeout,
            }
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, config_file: Path | None = None) -> "AppConfig":
        if config_file is None:
            config_file = get_app_data_dir() / "config.json"
        if not config_file.exists():
            return cls()
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            audio_data = data.get("audio", {})
            audio_settings = AudioSettings(
                sample_rate=audio_data.get("sample_rate", 16000),
                chunk_ms=audio_data.get("chunk_ms", 30),
                vad_silence_seconds=audio_data.get("vad_silence_seconds", 1.5),
                min_segment_seconds=audio_data.get("min_segment_seconds", 5.0),
                max_segment_seconds=audio_data.get("max_segment_seconds", 25.0),
                speaker_turn_timeout=audio_data.get("speaker_turn_timeout", 7.0),
            )
            raw_model = data.get("stt_model", "gemini-3.5-flash-lite")
            # Upgrade deprecated or rate-limited models automatically to gemini-3.5-flash-lite
            if any(old in raw_model for old in ["2.5", "2.0", "1.5"]) or raw_model == "gemini-3.5-flash":
                raw_model = "gemini-3.5-flash-lite"

            return cls(
                system_audio_device_index=data.get("system_audio_device_index"),
                microphone_device_index=data.get("microphone_device_index"),
                system_audio_enabled=data.get("system_audio_enabled", True),
                microphone_enabled=data.get("microphone_enabled", True),
                stt_model=raw_model,
                ai_post_processing_enabled=data.get("ai_post_processing_enabled", True),
                auto_detect_meetings=data.get("auto_detect_meetings", True),
                launch_at_startup=data.get("launch_at_startup", True),
                start_minimized_to_tray=data.get("start_minimized_to_tray", True),
                minimize_to_tray_on_close=data.get("minimize_to_tray_on_close", False),
                audio=audio_settings
            )
        except Exception:
            return cls()
