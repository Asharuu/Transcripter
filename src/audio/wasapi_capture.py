"""WASAPI Audio Capture: Multi-threaded Loopback and Microphone capture engine."""

import logging
import threading
import time
from typing import Callable
import pyaudiowpatch as pyaudio

from src.audio.synchronizer import AudioSynchronizer
from src.audio.vad_segmenter import AudioChannelType

logger = logging.getLogger(__name__)


class AudioCaptureThread(threading.Thread):
    """Worker thread that continuously captures audio from a specific device (Loopback or Mic),
    normalizes it to 16kHz Mono PCM, and passes it to the registered callback.
    """

    def __init__(
        self,
        pa: pyaudio.PyAudio,
        device_index: int,
        channel_type: AudioChannelType,
        on_audio_chunk: Callable[[bytes, float, AudioChannelType], None],
        frames_per_buffer: int = 1024,
    ):
        super().__init__(daemon=True)
        self.pa = pa
        self.device_index = device_index
        self.channel_type = channel_type
        self.on_audio_chunk = on_audio_chunk
        self.frames_per_buffer = frames_per_buffer

        self._stop_event = threading.Event()
        self._is_paused = threading.Event()
        self.stream = None

        # Device hardware configuration
        dev_info = self.pa.get_device_info_by_index(device_index)
        self.device_name = dev_info.get("name", "Unknown Device")
        self.hardware_sample_rate = int(dev_info.get("defaultSampleRate", 48000))
        self.hardware_channels = max(1, int(dev_info.get("maxInputChannels", 2)))
        self.is_loopback = bool(dev_info.get("isLoopbackDevice", False))

    def stop(self) -> None:
        """Signal thread to stop and wait for termination."""
        self._stop_event.set()
        self._is_paused.clear()

    def pause(self) -> None:
        self._is_paused.set()

    def resume(self) -> None:
        self._is_paused.clear()

    def run(self) -> None:
        logger.info(
            "Starting capture thread for %s (%s, %dch @ %dHz)",
            self.channel_type.value,
            self.device_name,
            self.hardware_channels,
            self.hardware_sample_rate,
        )

        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.hardware_channels,
                rate=self.hardware_sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.frames_per_buffer,
            )
        except Exception as e:
            logger.error("Failed to open audio stream on device %d: %s", self.device_index, e)
            return

        frame_duration = self.frames_per_buffer / self.hardware_sample_rate

        while not self._stop_event.is_set():
            if self._is_paused.is_set():
                time.sleep(0.05)
                continue

            try:
                # On Windows WASAPI loopback, if no audio is playing, stream.read() will block.
                # Check available frames first to prevent starvation or blocking.
                if self.is_loopback:
                    available = self.stream.get_read_available()
                    if available < self.frames_per_buffer:
                        # System is currently silent
                        silence = AudioSynchronizer.generate_silence(frame_duration)
                        timestamp = time.time()
                        if self.on_audio_chunk:
                            self.on_audio_chunk(silence, timestamp, self.channel_type)
                        time.sleep(frame_duration)
                        continue

                # Read hardware audio buffer
                raw_data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                timestamp = time.time()

                if raw_data:
                    # Resample and downmix to standard 16kHz 16-bit Mono PCM
                    pcm16 = AudioSynchronizer.pcm_to_16k_mono(
                        raw_data=raw_data,
                        source_sample_rate=self.hardware_sample_rate,
                        source_channels=self.hardware_channels,
                        source_is_float=False,
                    )
                    if pcm16 and self.on_audio_chunk:
                        self.on_audio_chunk(pcm16, timestamp, self.channel_type)

            except IOError as e:
                # If loopback is silent, WASAPI might produce an underflow or empty buffer
                if self.is_loopback:
                    timestamp = time.time()
                    silence = AudioSynchronizer.generate_silence(frame_duration)
                    if self.on_audio_chunk:
                        self.on_audio_chunk(silence, timestamp, self.channel_type)
                    time.sleep(frame_duration)
                else:
                    logger.debug("Audio read error: %s", e)
                    time.sleep(0.01)
            except Exception as e:
                logger.warning("Unexpected error during audio capture: %s", e)
                time.sleep(0.02)

        # Cleanup stream
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        except Exception:
            pass
        logger.info("Stopped capture thread for %s", self.channel_type.value)


class AudioEngine:
    """High-level audio capture coordinator managing System Audio & Mic threads."""

    def __init__(self):
        self._pa = None
        self._system_thread: AudioCaptureThread | None = None
        self._mic_thread: AudioCaptureThread | None = None
        self._on_chunk_callback: Callable[[bytes, float, AudioChannelType], None] | None = None

    def _get_pa(self) -> pyaudio.PyAudio:
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        return self._pa

    def start(
        self,
        system_audio_index: int | None,
        mic_index: int | None,
        on_audio_chunk: Callable[[bytes, float, AudioChannelType], None],
    ) -> bool:
        """Start capturing from enabled audio sources."""
        self.stop()
        self._on_chunk_callback = on_audio_chunk
        pa = self._get_pa()

        started_any = False

        # 1. Start System Audio Loopback if requested
        if system_audio_index is not None:
            try:
                self._system_thread = AudioCaptureThread(
                    pa=pa,
                    device_index=system_audio_index,
                    channel_type=AudioChannelType.REMOTE,
                    on_audio_chunk=self._on_chunk_callback,
                )
                self._system_thread.start()
                started_any = True
            except Exception as e:
                logger.error("Failed to start System Audio thread: %s", e)

        # 2. Start Microphone if requested
        if mic_index is not None:
            try:
                self._mic_thread = AudioCaptureThread(
                    pa=pa,
                    device_index=mic_index,
                    channel_type=AudioChannelType.LOCAL,
                    on_audio_chunk=self._on_chunk_callback,
                )
                self._mic_thread.start()
                started_any = True
            except Exception as e:
                logger.error("Failed to start Microphone thread: %s", e)

        return started_any

    def stop(self) -> None:
        """Stop all active capture threads."""
        if self._system_thread:
            self._system_thread.stop()
            self._system_thread.join(timeout=1.0)
            self._system_thread = None

        if self._mic_thread:
            self._mic_thread.stop()
            self._mic_thread.join(timeout=1.0)
            self._mic_thread = None

    def pause(self) -> None:
        if self._system_thread:
            self._system_thread.pause()
        if self._mic_thread:
            self._mic_thread.pause()

    def resume(self) -> None:
        if self._system_thread:
            self._system_thread.resume()
        if self._mic_thread:
            self._mic_thread.resume()

    def is_running(self) -> bool:
        sys_alive = self._system_thread.is_alive() if self._system_thread else False
        mic_alive = self._mic_thread.is_alive() if self._mic_thread else False
        return sys_alive or mic_alive
