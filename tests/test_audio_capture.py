"""Audio Device Enumeration & WASAPI Loopback Verification Test."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.audio.device_manager import AudioDeviceManager
from src.audio.wasapi_capture import AudioCaptureThread
from src.audio.vad_segmenter import AudioChannelType
from src.audio.synchronizer import AudioSynchronizer


def test_enumeration():
    print("=" * 60)
    print("TRANSRIPTER — AUDIO DEVICE ENUMERATION TEST")
    print("=" * 60)

    adm = AudioDeviceManager()
    wasapi_idx = adm.get_wasapi_host_api_index()
    print(f"WASAPI Host API Index: {wasapi_idx}")

    default_loopback = adm.get_default_loopback_device()
    print(f"\nDefault Loopback Device: {default_loopback}")

    default_mic = adm.get_default_microphone_device()
    print(f"Default Microphone Device: {default_mic}")

    print("\n--- All Available Loopback Render Endpoints ---")
    loopbacks = adm.list_loopback_devices()
    for d in loopbacks:
        print(f"  [{d.index}] {d.name} ({d.channels} ch @ {d.sample_rate} Hz) {'*DEFAULT*' if d.is_default else ''}")

    print("\n--- All Available Microphone Input Endpoints ---")
    mics = adm.list_microphone_devices()
    for m in mics:
        print(f"  [{m.index}] {m.name} ({m.channels} ch @ {m.sample_rate} Hz) {'*DEFAULT*' if m.is_default else ''}")

    adm.close()
    return len(loopbacks) > 0 or len(mics) > 0


if __name__ == "__main__":
    success = test_enumeration()
    sys.exit(0 if success else 1)
