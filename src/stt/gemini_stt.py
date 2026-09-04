"""Gemini Speech-to-Text Engine using the official Google GenAI SDK."""

import io
import logging
import time
import wave
from google import genai
from google.genai import types

from src.core.credentials import CredentialManager
from src.stt.base import BaseSTTEngine

logger = logging.getLogger(__name__)

STT_SYSTEM_PROMPT = (
    "You are a verbatim speech-to-text transcriber specializing in Indonesian, English, "
    "and mixed Indonesian-English (Indoglish) speech. "
    "Transcribe exactly what is spoken. Preserve all technical terms, coding terms, "
    "and conversational code-switching naturally as uttered. "
    "DO NOT translate into another language. "
    "DO NOT summarize or rephrase. "
    "DO NOT add conversational filler or explanations. "
    "Return ONLY the plain transcribed text."
)


def pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    """Pack raw 16-bit mono PCM bytes into an in-memory WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class GeminiSTTEngine(BaseSTTEngine):
    """Speech-to-Text engine powered by Google Gemini multimodal audio."""

    def __init__(self, model_name: str = "gemini-3.5-flash-lite"):
        self.model_name = model_name
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client | None:
        api_key = CredentialManager.get_api_key()
        if not api_key:
            return None
        if self._client is None:
            self._client = genai.Client(api_key=api_key)
        return self._client

    def is_configured(self) -> bool:
        return CredentialManager.has_api_key()

    def transcribe(self, pcm_data: bytes, sample_rate: int = 16000) -> str:
        """Upload audio chunk to Gemini and return verbatim transcription."""
        if not pcm_data or len(pcm_data) < sample_rate * 2 * 0.5:
            # Audio shorter than 0.5 seconds is skipped
            return ""

        client = self._get_client()
        if not client:
            logger.warning("Gemini API key not configured.")
            return "[Gemini API key belum dikonfigurasi di Settings]"

        wav_bytes = pcm_to_wav_bytes(pcm_data, sample_rate)

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(
                        data=wav_bytes,
                        mime_type="audio/wav",
                    ),
                    "Transcribe the spoken audio verbatim according to the system instructions.",
                ],
                config=types.GenerateContentConfig(
                    system_instruction=STT_SYSTEM_PROMPT,
                    temperature=0.0,
                ),
            )
            if response and response.text:
                return response.text.strip()
            return ""

        except Exception as e:
            err_str = str(e)
            logger.error("Gemini STT transcription error: %s", err_str)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                return "[Batas kuota Gemini API tercapai. Mohon tunggu sebentar...]"
            elif "API_KEY_INVALID" in err_str or "400" in err_str:
                return "[Kunci API Gemini tidak valid. Silakan periksa di Settings.]"
            elif "503" in err_str or "overloaded" in err_str.lower():
                return "[Server Gemini sedang sibuk. Mencoba kembali...]"
            return f"[Gagal mentranskripsi: {err_str[:80]}]"
