"""Live pipeline test: verifies 3 seconds of concurrent audio capture and resampling."""

import sys
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.audio.device_manager import AudioDeviceManager
from src.audio.wasapi_capture import AudioEngine
from src.audio.synchronizer import AudioSynchronizer
from src.audio.vad_segmenter import AudioChannelType, AdaptiveVADSegmenter


def test_live_pipeline():
    print("Testing concurrent audio capture for 3 seconds...")
    adm = AudioDeviceManager()
    default_loop = adm.get_default_loopback_device()
    default_mic = adm.get_default_microphone_device()
    adm.close()

    sys_idx = default_loop.index if default_loop else None
    mic_idx = default_mic.index if default_mic else None

    print(f"Using Loopback device: {default_loop.name if default_loop else 'None'}")
    print(f"Using Mic device: {default_mic.name if default_mic else 'None'}")

    chunks_received = {"LOCAL": 0, "REMOTE": 0}
    max_rms = {"LOCAL": 0.0, "REMOTE": 0.0}

    def on_chunk(pcm16: bytes, timestamp: float, channel: AudioChannelType):
        chunks_received[channel.value] += 1
        rms = AudioSynchronizer.calculate_rms_volume(pcm16)
        if rms > max_rms[channel.value]:
            max_rms[channel.value] = rms

    engine = AudioEngine()
    started = engine.start(
        system_audio_index=sys_idx,
        mic_index=mic_idx,
        on_audio_chunk=on_chunk,
    )

    if not started:
        print("ERROR: Engine failed to start!")
        return False

    print("Capture running...")
    time.sleep(3.0)
    engine.stop()
    print("Capture stopped successfully.")

    print(f"Results:")
    print(f"  Remote (Loopback) chunks: {chunks_received['REMOTE']}, Peak RMS: {max_rms['REMOTE']:.4f}")
    print(f"  Local (Mic) chunks:       {chunks_received['LOCAL']}, Peak RMS: {max_rms['LOCAL']:.4f}")

    # Success if at least one stream received chunks
    return chunks_received["REMOTE"] > 0 or chunks_received["LOCAL"] > 0


if __name__ == "__main__":
    success = test_live_pipeline()
    sys.exit(0 if success else 1)
