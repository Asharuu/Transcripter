"""Background meeting detector: scans desktop windows for Google Meet, MS Teams, Zoom, etc."""

import os
import re
import time
from PySide6.QtCore import QObject, QTimer, Signal

if os.name == "nt":
    import ctypes
    from ctypes import wintypes


def parse_meeting_title(title: str) -> tuple[str, str] | None:
    """Parses a window title and returns (app_name, clean_title) if it matches a meeting."""
    if not title or not title.strip():
        return None

    raw = title.strip()
    lower = raw.lower()

    # 1. Google Meet
    # e.g., 'Meet - abc-defg-hij - Google Chrome', 'Meet: Weekly Sync | Microsoft Edge'
    m = re.search(
        r"Meet\s*[-–—:]\s*(.+?)(?:\s*[-–—|]\s*(?:Google Chrome|Microsoft\u200b Edge|Microsoft Edge|Brave|Firefox|Opera|Vivaldi))?$",
        raw,
        re.IGNORECASE,
    )
    if m:
        clean = m.group(1).strip()
        clean = re.sub(
            r"\s*[-–—|]\s*(?:Google Chrome|Microsoft\u200b Edge|Microsoft Edge|Brave|Firefox|Opera|Vivaldi)$",
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()
        return "Google Meet", clean or "Google Meet"

    if "meet.google.com" in lower or ("google meet" in lower and not "search" in lower):
        clean = re.sub(
            r"\s*[-–—|]\s*(?:Google Meet|Google Chrome|Microsoft\u200b Edge|Microsoft Edge|Brave|Firefox)$",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        return "Google Meet", clean or "Google Meet"

    # 2. Microsoft Teams
    if "microsoft teams" in lower:
        clean = re.sub(r"\s*[-–—|]\s*Microsoft Teams.*$", "", raw, flags=re.IGNORECASE).strip()
        if clean.lower() in ["meeting", "", "call"]:
            clean = "Teams Meeting"
        return "Microsoft Teams", clean
    if "teams meeting" in lower:
        return "Microsoft Teams", "Teams Meeting"

    # 3. Zoom
    if "zoom meeting" in lower or "zoom workplace" in lower or "zoom webinar" in lower:
        clean = re.sub(
            r"^(?:Zoom Meeting\s*[-–—:]?\s*|Zoom Workplace\s*[-–—:]?\s*|Zoom Webinar\s*[-–—:]?\s*)",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        return "Zoom", clean or "Zoom Meeting"

    # 4. Cisco Webex
    if "webex" in lower:
        clean = re.sub(r"\s*[-–—|]\s*(?:Cisco Webex Meetings|Webex).*$", "", raw, flags=re.IGNORECASE).strip()
        return "Webex", clean or "Webex Meeting"

    return None


def get_desktop_window_titles() -> list[str]:
    """Retrieves visible top-level desktop window titles on Windows safely."""
    if os.name != "nt":
        return []

    titles: list[str] = []
    try:
        user32 = ctypes.windll.user32
        desk = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_READOBJECTS

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    val = buf.value.strip()
                    if val:
                        titles.append(val)
            return True

        if desk:
            user32.EnumDesktopWindows(desk, WNDENUMPROC(enum_cb), 0)
            user32.CloseDesktop(desk)
        else:
            # Fallback to EnumWindows
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass

    return titles


class MeetingDetector(QObject):
    """Background monitor for active meeting applications."""

    meeting_detected = Signal(str, str)  # (app_type, meeting_title)
    meeting_ended = Signal(str, str)     # (app_type, meeting_title)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scan_windows)
        self._is_recording = False
        self._enabled = True

        # Tracks currently active meetings: key -> (app_type, title)
        self._active_meetings: dict[str, tuple[str, str]] = {}
        # Tracks dismissed or started meetings: key -> timestamp
        self._dismissed_meetings: dict[str, float] = {}
        # Dismiss snooze duration: 30 minutes
        self._snooze_seconds = 1800.0

    def start(self, interval_ms: int = 2000):
        """Starts periodic scanning for meetings."""
        if not self._timer.isActive():
            self._timer.start(interval_ms)

    def stop(self):
        """Stops scanning."""
        self._timer.stop()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self._active_meetings.clear()

    def set_recording_active(self, is_recording: bool):
        """Informs the detector whether Transcripter is actively recording."""
        self._is_recording = is_recording

    def dismiss_meeting(self, app_type: str, meeting_title: str):
        """Marks a meeting as dismissed so the user is not prompted again during this session."""
        key = f"{app_type}::{meeting_title}"
        self._dismissed_meetings[key] = time.time()

    def mark_meeting_recorded(self, app_type: str, meeting_title: str):
        """Marks a meeting as actively recorded."""
        key = f"{app_type}::{meeting_title}"
        self._dismissed_meetings[key] = time.time()

    def _scan_windows(self):
        if not self._enabled or self._is_recording:
            return

        titles = get_desktop_window_titles()
        current_detected_keys: set[str] = set()

        for win_title in titles:
            parsed = parse_meeting_title(win_title)
            if not parsed:
                continue

            app_type, meeting_title = parsed
            key = f"{app_type}::{meeting_title}"
            current_detected_keys.add(key)

            # Check if dismissed recently
            dismissed_time = self._dismissed_meetings.get(key)
            if dismissed_time and (time.time() - dismissed_time) < self._snooze_seconds:
                continue

            # If not already marked as active/prompted
            if key not in self._active_meetings:
                self._active_meetings[key] = (app_type, meeting_title)
                self.meeting_detected.emit(app_type, meeting_title)

        # Detect closed meetings to clean up
        closed_keys = [k for k in self._active_meetings if k not in current_detected_keys]
        for k in closed_keys:
            app, title = self._active_meetings.pop(k)
            self.meeting_ended.emit(app, title)
            # Also clear snooze when meeting window is closed so next call prompts again
            self._dismissed_meetings.pop(k, None)
