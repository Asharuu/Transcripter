"""Unit tests for CredentialManager."""

import os
import unittest
from unittest.mock import patch
from src.core.credentials import CredentialManager, SERVICE_NAME, KEY_USERNAME


class TestCredentialManager(unittest.TestCase):

    def setUp(self):
        # Clear env var if set
        self.old_env = os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self):
        if self.old_env is not None:
            os.environ["GEMINI_API_KEY"] = self.old_env

    @patch("keyring.get_password")
    def test_get_api_key_from_keyring(self, mock_get_pw):
        mock_get_pw.return_value = "AIzaSyFakeKeyFromKeyring12345"
        key = CredentialManager.get_api_key()
        self.assertEqual(key, "AIzaSyFakeKeyFromKeyring12345")
        mock_get_pw.assert_called_once_with(SERVICE_NAME, KEY_USERNAME)

    @patch("keyring.get_password")
    def test_get_api_key_env_fallback(self, mock_get_pw):
        mock_get_pw.return_value = None
        os.environ["GEMINI_API_KEY"] = "AIzaSyFakeKeyFromEnv9999"
        key = CredentialManager.get_api_key()
        self.assertEqual(key, "AIzaSyFakeKeyFromEnv9999")

    @patch("keyring.set_password")
    def test_save_api_key(self, mock_set_pw):
        success = CredentialManager.save_api_key("AIzaSyNewKey123")
        self.assertTrue(success)
        mock_set_pw.assert_called_once_with(SERVICE_NAME, KEY_USERNAME, "AIzaSyNewKey123")

    @patch("keyring.delete_password")
    def test_delete_api_key(self, mock_del_pw):
        success = CredentialManager.delete_api_key()
        self.assertTrue(success)
        mock_del_pw.assert_called_once_with(SERVICE_NAME, KEY_USERNAME)


if __name__ == "__main__":
    unittest.main()
