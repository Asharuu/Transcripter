"""Voice Activity Detection & Adaptive Speech Segmentation Engine."""

import logging
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class AudioChannelType(str, Enum):
    LOCAL = "LOCAL"      # Microphone -> Speaker 1 (You)
    REMOTE = "REMOTE"    # System Audio Loopback -> Speaker 2 (Remote)


@dataclass
class SpeechSegment:
    channel: AudioChannelType
    speaker_label: str
    pcm_data: bytes
    start_time: float
    end_time: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


class AdaptiveVADSegmenter:
    """Detects speech boundaries and aggregates audio frames into optimal segments.
    
    Protects against short-pause fragmentation and Gemini rate limits by enforcing
    adaptive minimum and maximum segment thresholds.
    """

    def __init__(
        self,
        channel: AudioChannelType,
        speaker_label: str,
        sample_rate: int = 16000,
        silence_threshold_sec: float = 1.5,
        min_segment_sec: float = 5.0,
        max_segment_sec: float = 25.0,
        energy_threshold: float = 300.0,
    ):
        self.channel = channel
        self.speaker_label = speaker_label
        self.sample_rate = sample_rate
        self.silence_threshold_sec = silence_threshold_sec
        self.min_segment_sec = min_segment_sec
        self.max_segment_sec = max_segment_sec
        self.energy_threshold = energy_threshold

        # Buffer state
        self._buffer: list[bytes] = []
        self._current_speech_start: float = 0.0
        self._last_speech_time: float = 0.0
        self._is_speaking: bool = False
        self._consecutive_speech_frames: int = 0
        self._consecutive_silence_frames: int = 0

    def reset(self) -> None:
        self._buffer.clear()
        self._is_speaking = False
        self._current_speech_start = 0.0
        self._last_speech_time = 0.0
        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0

    def process_frame(self, pcm_frame: bytes, current_time: float) -> SpeechSegment | None:
        """Process a 16kHz 16-bit mono PCM frame (typically 20-50ms) and return a segment if ready."""
        if not pcm_frame:
            return None

        # Compute frame energy (RMS)
        samples = np.frombuffer(pcm_frame, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return None
        rms = float(np.sqrt(np.mean(samples ** 2)))

        is_voice = rms > self.energy_threshold

        if is_voice:
            self._consecutive_speech_frames += 1
            self._consecutive_silence_frames = 0
            self._last_speech_time = current_time

            if not self._is_speaking and self._consecutive_speech_frames >= 3:
                # Confirmed speech start
                self._is_speaking = True
                if self._current_speech_start <= 0.0:
                    self._current_speech_start = current_time
        else:
            self._consecutive_silence_frames += 1
            self._consecutive_speech_frames = 0

        # Always append to buffer while in speaking state or building pre-roll
        if self._is_speaking or (self._consecutive_speech_frames > 0):
            if self._current_speech_start <= 0.0:
                self._current_speech_start = current_time
            self._buffer.append(pcm_frame)

        # Calculate current buffer duration
        total_samples = sum(len(f) // 2 for f in self._buffer)
        buffer_duration = total_samples / self.sample_rate

        # Check conditions for emitting a segment:
        silence_duration = current_time - self._last_speech_time if self._is_speaking else 0.0

        # Condition A: Natural pause detected and minimum duration reached
        natural_pause_ready = (
            self._is_speaking
            and silence_duration >= self.silence_threshold_sec
            and buffer_duration >= self.min_segment_sec
        )

        # Condition B: Hard maximum duration exceeded (force cut)
        hard_limit_exceeded = (
            self._is_speaking
            and buffer_duration >= self.max_segment_sec
        )

        if natural_pause_ready or hard_limit_exceeded:
            segment = self._emit_segment(current_time)
            return segment

        return None

    def flush(self, current_time: float) -> SpeechSegment | None:
        """Force flush any remaining speech in the buffer (called on recording STOP)."""
        if not self._buffer:
            return None

        total_samples = sum(len(f) // 2 for f in self._buffer)
        buffer_duration = total_samples / self.sample_rate

        # If at least 1.0 second of audio exists, emit it
        if buffer_duration >= 1.0:
            return self._emit_segment(current_time)
        else:
            self.reset()
            return None

    def _emit_segment(self, end_time: float) -> SpeechSegment:
        pcm_bytes = b"".join(self._buffer)
        total_samples = len(pcm_bytes) // 2
        buffer_duration = total_samples / self.sample_rate

        start_time = self._current_speech_start
        if start_time <= 0.0 or start_time > end_time:
            start_time = max(0.0, end_time - buffer_duration)

        segment = SpeechSegment(
            channel=self.channel,
            speaker_label=self.speaker_label,
            pcm_data=pcm_bytes,
            start_time=start_time,
            end_time=end_time,
        )
        self.reset()
        return segment
