"""Session Manager: Handles past and active session history, metadata, and persistence."""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import uuid

from src.core.config import get_app_data_dir, get_transcripts_dir

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    id: str
    title: str
    created_at: str  # ISO 8601 string
    duration_seconds: float
    system_audio_enabled: bool
    microphone_enabled: bool
    markdown_file: str | None = None
    txt_file: str | None = None


class SessionManager:
    """Manages transcription sessions on the local system."""

    def __init__(self):
        self.index_file = get_app_data_dir() / "sessions_index.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.index_file.exists():
            try:
                with open(self.index_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                logger.error("Failed to initialize sessions index: %s", e)

    def list_sessions(self) -> list[SessionMetadata]:
        """Returns all past sessions sorted newest first."""
        if not self.index_file.exists():
            return []
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = [SessionMetadata(**item) for item in data]
            # Sort newest first
            sessions.sort(key=lambda s: s.created_at, reverse=True)
            return sessions
        except Exception as e:
            logger.error("Error reading sessions index: %s", e)
            return []

    def create_session(
        self,
        title: str,
        duration_seconds: float,
        system_audio_enabled: bool,
        microphone_enabled: bool,
        markdown_text: str,
        plain_text: str,
    ) -> SessionMetadata:
        """Saves a completed session with Markdown and Plaintext files."""
        session_id = str(uuid.uuid4())
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        if not safe_title:
            safe_title = "Transcript"

        transcripts_dir = get_transcripts_dir()
        md_filename = f"{safe_title}_{timestamp_slug}.md"
        txt_filename = f"{safe_title}_{timestamp_slug}.txt"

        md_path = transcripts_dir / md_filename
        txt_path = transcripts_dir / txt_filename

        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(plain_text)
        except Exception as e:
            logger.error("Failed to save transcript files: %s", e)

        meta = SessionMetadata(
            id=session_id,
            title=title,
            created_at=datetime.now().isoformat(),
            duration_seconds=duration_seconds,
            system_audio_enabled=system_audio_enabled,
            microphone_enabled=microphone_enabled,
            markdown_file=str(md_path),
            txt_file=str(txt_path),
        )

        # Update index
        sessions = self.list_sessions()
        sessions.append(meta)
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump([asdict(s) for s in sessions], f, indent=2)
        except Exception as e:
            logger.error("Failed to update sessions index: %s", e)

        return meta

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session from index and removes associated files."""
        sessions = self.list_sessions()
        remaining = []
        found = False

        for s in sessions:
            if s.id == session_id:
                found = True
                # Clean up files if they exist
                if s.markdown_file:
                    try:
                        Path(s.markdown_file).unlink(missing_ok=True)
                    except Exception:
                        pass
                if s.txt_file:
                    try:
                        Path(s.txt_file).unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                remaining.append(s)

        if found:
            try:
                with open(self.index_file, "w", encoding="utf-8") as f:
                    json.dump([asdict(s) for s in remaining], f, indent=2)
                return True
            except Exception as e:
                logger.error("Failed to save updated index: %s", e)
        return False
