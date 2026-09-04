"""Conservative AI Post-Processor: Fixes punctuation, capitalization, and obvious typos
without altering meaning, summarizing, or rewriting speech.
"""

import logging
from google import genai
from google.genai import types

from src.core.credentials import CredentialManager

logger = logging.getLogger(__name__)

POST_PROCESSOR_PROMPT = """You are a strictly conservative transcript editor.
Your ONLY goal is to make the raw speech transcript readable by:
1. Adding proper punctuation (periods, commas, question marks).
2. Fixing capitalization (first words of sentences, proper nouns, acronyms like OOP, SQL, API).
3. Correcting obvious acoustic speech recognition misspellings when the intended word is unmistakable.
4. Preserving code-switching (Indonesian and English mixed together) exactly as spoken.

ABSOLUTE RESTRICTIONS:
- NEVER summarize or condense the text.
- NEVER paraphrase or rewrite the speaker's sentences.
- NEVER add information or explain what the speaker "probably meant".
- NEVER remove meaningful words or convert casual speech into formal academic prose.
- NEVER turn speech into lecture bullet points.
- If uncertain, leave the words exactly as originally transcribed.

Return ONLY the cleaned transcript with no preamble, quotes, or meta-comments.
"""


class ConservativePostProcessor:
    """Polishes raw speech transcripts with strict conservative boundaries."""

    def __init__(self, model_name: str = "gemini-3.5-flash"):
        self.model_name = model_name
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client | None:
        api_key = CredentialManager.get_api_key()
        if not api_key:
            return None
        if self._client is None:
            self._client = genai.Client(api_key=api_key)
        return self._client

    def process(self, raw_text: str) -> str:
        """Conservatively clean raw transcription text."""
        clean_input = raw_text.strip()
        if not clean_input or len(clean_input.split()) < 3:
            # Very short text does not need complex LLM polishing
            return clean_input

        # If it looks like an error message from STT, pass through directly
        if clean_input.startswith("[") and clean_input.endswith("]"):
            return clean_input

        client = self._get_client()
        if not client:
            return clean_input

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[clean_input],
                config=types.GenerateContentConfig(
                    system_instruction=POST_PROCESSOR_PROMPT,
                    temperature=0.0,
                ),
            )
            if response and response.text:
                polished = response.text.strip()
                # Safety check: Guard against runaway hallucinations or extreme length divergence
                input_words = len(clean_input.split())
                output_words = len(polished.split())
                # If output suddenly exploded or shrank by > 50%, reject and keep raw text
                if output_words > input_words * 1.5 or output_words < input_words * 0.5:
                    logger.warning("Polished output word count deviated excessively; keeping raw text.")
                    return clean_input
                return polished
            return clean_input
        except Exception as e:
            logger.warning("Post-processor failed, falling back to raw text: %s", e)
            return clean_input
