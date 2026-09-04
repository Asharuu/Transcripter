"""Abstract base interface for Speech-to-Text engines."""

from abc import ABC, abstractmethod


class BaseSTTEngine(ABC):
    """Abstract interface that all STT providers must implement."""

    @abstractmethod
    def transcribe(self, pcm_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe 16kHz 16-bit Mono PCM audio into verbatim text."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the engine is ready and credentials are valid."""
        pass
