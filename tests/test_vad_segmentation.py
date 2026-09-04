"""Unit tests for AdaptiveVADSegmenter."""

import unittest
import numpy as np
from src.audio.vad_segmenter import AdaptiveVADSegmenter, AudioChannelType


def generate_pcm_sine(duration_sec: float, sample_rate: int = 16000, freq: float = 440.0, amplitude: float = 10000.0) -> bytes:
    """Generate artificial 16kHz 16-bit mono speech-like sound."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    waveform = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    return waveform.tobytes()


def generate_pcm_silence(duration_sec: float, sample_rate: int = 16000) -> bytes:
    """Generate artificial silence."""
    return np.zeros(int(sample_rate * duration_sec), dtype=np.int16).tobytes()


class TestAdaptiveVADSegmenter(unittest.TestCase):

    def setUp(self):
        self.segmenter = AdaptiveVADSegmenter(
            channel=AudioChannelType.LOCAL,
            speaker_label="Speaker 1 (You)",
            silence_threshold_sec=1.5,
            min_segment_sec=3.0,
            max_segment_sec=10.0,
            energy_threshold=300.0,
        )

    def test_silence_produces_no_segments(self):
        """Pure silence should never trigger a speech segment."""
        frame = generate_pcm_silence(0.03)  # 30ms frame
        segment = None
        for i in range(100):
            seg = self.segmenter.process_frame(frame, current_time=i * 0.03)
            if seg:
                segment = seg

        self.assertIsNone(segment)

    def test_speech_then_pause_emits_segment(self):
        """Continuous speech followed by a 1.5s pause should emit a clean segment."""
        # 1. 4 seconds of active speech (above min_segment_sec of 3.0s)
        speech_frame = generate_pcm_sine(0.03)
        curr_t = 0.0
        for _ in range(133):  # ~4.0 seconds
            self.segmenter.process_frame(speech_frame, curr_t)
            curr_t += 0.03

        # 2. 1.6 seconds of silence (reaches 1.5s pause threshold)
        silence_frame = generate_pcm_silence(0.03)
        emitted_segment = None
        for _ in range(55):  # ~1.65 seconds
            seg = self.segmenter.process_frame(silence_frame, curr_t)
            if seg:
                emitted_segment = seg
                break
            curr_t += 0.03

        self.assertIsNotNone(emitted_segment)
        self.assertEqual(emitted_segment.speaker_label, "Speaker 1 (You)")
        self.assertEqual(emitted_segment.channel, AudioChannelType.LOCAL)
        self.assertGreaterEqual(emitted_segment.duration, 3.5)

    def test_flush_emits_pending_audio_on_stop(self):
        """Flushing at the end of recording should emit any valid accumulated speech."""
        speech_frame = generate_pcm_sine(0.03)
        curr_t = 0.0
        for _ in range(70):  # ~2.1 seconds
            self.segmenter.process_frame(speech_frame, curr_t)
            curr_t += 0.03

        flushed = self.segmenter.flush(curr_t)
        self.assertIsNotNone(flushed)
        self.assertGreaterEqual(flushed.duration, 2.0)


if __name__ == "__main__":
    unittest.main()
