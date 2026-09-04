"""Audio Synchronizer: Resamples, converts channels, and normalizes PCM audio to 16kHz Mono."""

import math
import numpy as np
from scipy import signal


class AudioSynchronizer:
    """Normalizes raw audio buffers from various hardware formats to 16kHz 16-bit Mono PCM."""

    TARGET_SAMPLE_RATE = 16000

    @staticmethod
    def pcm_to_16k_mono(
        raw_data: bytes,
        source_sample_rate: int,
        source_channels: int,
        source_is_float: bool = False,
    ) -> bytes:
        """Convert arbitrary incoming audio buffer to 16kHz 16-bit Mono PCM bytes."""
        if not raw_data:
            return b""

        # 1. Parse raw bytes into numpy array
        if source_is_float:
            samples = np.frombuffer(raw_data, dtype=np.float32)
        else:
            samples = np.frombuffer(raw_data, dtype=np.int16)

        if len(samples) == 0:
            return b""

        # 2. Downmix multi-channel to mono
        if source_channels > 1:
            # Reshape into [num_frames, num_channels]
            num_frames = len(samples) // source_channels
            samples = samples[: num_frames * source_channels].reshape((num_frames, source_channels))
            # Average channels
            mono = samples.mean(axis=1)
        else:
            mono = samples

        # 3. Ensure float32 representation for high-fidelity resampling
        if not source_is_float:
            mono = mono.astype(np.float32) / 32768.0
        else:
            mono = np.clip(mono, -1.0, 1.0)

        # 4. Resample to 16,000 Hz if necessary
        if source_sample_rate != AudioSynchronizer.TARGET_SAMPLE_RATE:
            gcd = math.gcd(int(source_sample_rate), AudioSynchronizer.TARGET_SAMPLE_RATE)
            up = AudioSynchronizer.TARGET_SAMPLE_RATE // gcd
            down = int(source_sample_rate) // gcd
            resampled = signal.resample_poly(mono, up, down)
        else:
            resampled = mono

        # 5. Convert to 16-bit signed integer PCM
        resampled_clipped = np.clip(resampled * 32767.0, -32768.0, 32767.0)
        pcm16 = resampled_clipped.astype(np.int16)

        return pcm16.tobytes()

    @staticmethod
    def generate_silence(duration_seconds: float) -> bytes:
        """Generate 16kHz 16-bit mono silence bytes for the specified duration."""
        num_samples = int(AudioSynchronizer.TARGET_SAMPLE_RATE * duration_seconds)
        return (np.zeros(num_samples, dtype=np.int16)).tobytes()

    @staticmethod
    def calculate_rms_volume(pcm16_data: bytes) -> float:
        """Calculate Root Mean Square (RMS) volume normalized between 0.0 and 1.0."""
        if not pcm16_data:
            return 0.0
        samples = np.frombuffer(pcm16_data, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return 0.0
        rms = np.sqrt(np.mean(samples ** 2))
        # Normalize roughly: 32768 is max volume, normal voice is around 1000-8000
        normalized = min(1.0, rms / 8000.0)
        return float(normalized)
