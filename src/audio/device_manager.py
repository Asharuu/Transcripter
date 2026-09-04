"""Audio Device Manager: Enumerates Windows WASAPI Loopback and Microphone endpoints."""

import logging
from dataclasses import dataclass
from typing import Generator

logger = logging.getLogger(__name__)


@dataclass
class AudioDeviceInfo:
    index: int
    name: str
    channels: int
    sample_rate: int
    is_loopback: bool
    is_default: bool = False

    def __str__(self) -> str:
        default_tag = " (Default)" if self.is_default else ""
        type_tag = "[Loopback]" if self.is_loopback else "[Mic]"
        return f"{type_tag} {self.name}{default_tag} ({self.channels}ch @ {int(self.sample_rate)}Hz)"


class AudioDeviceManager:
    """Manages audio device enumeration using WASAPI via PyAudioWPatch."""

    def __init__(self):
        self._pa = None

    def _get_pa(self):
        import pyaudiowpatch as pyaudio
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        return self._pa

    def close(self):
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    def get_wasapi_host_api_index(self) -> int | None:
        p = self._get_pa()
        import pyaudiowpatch as pyaudio
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            return wasapi_info["index"]
        except Exception as e:
            logger.error("WASAPI Host API not found: %s", e)
            return None

    def get_default_loopback_device(self) -> AudioDeviceInfo | None:
        """Find the default system output loopback device."""
        p = self._get_pa()
        try:
            default_loopback = p.get_default_wasapi_loopback()
            if default_loopback:
                return AudioDeviceInfo(
                    index=default_loopback["index"],
                    name=default_loopback["name"],
                    channels=default_loopback["maxInputChannels"],
                    sample_rate=int(default_loopback["defaultSampleRate"]),
                    is_loopback=True,
                    is_default=True,
                )
        except Exception as e:
            logger.warning("Could not get default WASAPI loopback device: %s", e)
        return None

    def get_default_microphone_device(self) -> AudioDeviceInfo | None:
        """Find the default recording/microphone device under WASAPI."""
        p = self._get_pa()
        try:
            default_input = p.get_default_input_device_info()
            if default_input:
                return AudioDeviceInfo(
                    index=default_input["index"],
                    name=default_input["name"],
                    channels=default_input["maxInputChannels"],
                    sample_rate=int(default_input["defaultSampleRate"]),
                    is_loopback=False,
                    is_default=True,
                )
        except Exception as e:
            logger.warning("Could not get default microphone device: %s", e)
        return None

    def list_loopback_devices(self) -> list[AudioDeviceInfo]:
        """List all available WASAPI Loopback render devices (Speakers/Headphones)."""
        p = self._get_pa()
        devices = []
        default_idx = None
        default_dev = self.get_default_loopback_device()
        if default_dev:
            default_idx = default_dev.index

        try:
            for dev in p.get_loopback_device_info_generator():
                dev_idx = dev["index"]
                devices.append(
                    AudioDeviceInfo(
                        index=dev_idx,
                        name=dev["name"],
                        channels=dev["maxInputChannels"],
                        sample_rate=int(dev["defaultSampleRate"]),
                        is_loopback=True,
                        is_default=(dev_idx == default_idx),
                    )
                )
        except Exception as e:
            logger.error("Failed to enumerate loopback devices: %s", e)

        return devices

    def list_microphone_devices(self) -> list[AudioDeviceInfo]:
        """List all available physical microphone/capture devices."""
        p = self._get_pa()
        devices = []
        wasapi_idx = self.get_wasapi_host_api_index()
        default_dev = self.get_default_microphone_device()
        default_idx = default_dev.index if default_dev else None

        device_count = p.get_device_count()
        for i in range(device_count):
            try:
                dev = p.get_device_info_by_index(i)
                # Ensure device belongs to WASAPI and is a real input device, NOT a loopback device
                if dev.get("hostApi") == wasapi_idx and dev.get("maxInputChannels", 0) > 0:
                    if not dev.get("isLoopbackDevice", False):
                        devices.append(
                            AudioDeviceInfo(
                                index=i,
                                name=dev["name"],
                                channels=dev["maxInputChannels"],
                                sample_rate=int(dev["defaultSampleRate"]),
                                is_loopback=False,
                                is_default=(i == default_idx),
                            )
                        )
            except Exception:
                continue

        return devices
