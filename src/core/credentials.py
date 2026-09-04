"""Secure credential management using Windows Credential Manager / DPAPI via keyring."""

import logging
import os
import keyring

logger = logging.getLogger(__name__)

SERVICE_NAME = "TranscripterApp"
KEY_USERNAME = "gemini_api_key"


class CredentialManager:
    """Manages API key storage securely using Windows Credential Locker."""

    @staticmethod
    def get_api_key() -> str | None:
        """Retrieve the stored Gemini API key from Windows Credential Manager.
        
        Falls back to the GEMINI_API_KEY environment variable if present (useful in dev).
        """
        try:
            stored_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
            if stored_key:
                return stored_key.strip()
        except Exception as e:
            logger.warning("Failed to access keyring: %s", e)

        # Fallback to env var if running in dev environment
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            return env_key.strip()

        return None

    @staticmethod
    def save_api_key(api_key: str) -> bool:
        """Securely store the Gemini API key in Windows Credential Manager."""
        if not api_key or not api_key.strip():
            return False
        try:
            keyring.set_password(SERVICE_NAME, KEY_USERNAME, api_key.strip())
            return True
        except Exception as e:
            logger.error("Failed to save key in keyring: %s", e)
            return False

    @staticmethod
    def delete_api_key() -> bool:
        """Remove the stored Gemini API key from Windows Credential Manager."""
        try:
            keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
            return True
        except keyring.errors.PasswordDeleteError:
            return True
        except Exception as e:
            logger.error("Failed to delete key from keyring: %s", e)
            return False

    @staticmethod
    def has_api_key() -> bool:
        """Check whether a valid API key exists."""
        key = CredentialManager.get_api_key()
        return bool(key and len(key) > 5)

    @staticmethod
    def test_api_key(api_key: str) -> tuple[bool, str]:
        """Test API key validity with Google Gemini API."""
        if not api_key or not api_key.strip():
            return False, "API key cannot be empty."

        clean_key = api_key.strip()
        try:
            from google import genai
            client = genai.Client(api_key=clean_key)
            # Lightweight test call to verify permissions
            client.models.get(model="gemini-3.5-flash")
            return True, "API key valid and connection successful."
        except Exception as e:
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "400" in err_msg or "403" in err_msg:
                return False, "Invalid API Key. Please verify your Google AI Studio key."
            elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return False, "Quota exceeded or rate limit reached on Gemini API."
            return False, f"Connection failed: {err_msg}"
