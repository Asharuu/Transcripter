"""Unit tests for AppConfig configuration serialization and persistence."""

import unittest
import tempfile
from pathlib import Path
from src.core.config import AppConfig, AudioSettings


class TestAppConfig(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config(self):
        cfg = AppConfig()
        self.assertTrue(cfg.auto_detect_meetings)
        self.assertEqual(cfg.stt_model, "gemini-3.5-flash-lite")
        self.assertTrue(cfg.ai_post_processing_enabled)

    def test_save_and_load(self):
        cfg = AppConfig(
            auto_detect_meetings=False,
            stt_model="gemini-3.5-flash-lite",
            system_audio_enabled=False,
        )
        cfg.save(self.config_path)

        loaded = AppConfig.load(self.config_path)
        self.assertFalse(loaded.auto_detect_meetings)
        self.assertEqual(loaded.stt_model, "gemini-3.5-flash-lite")
        self.assertFalse(loaded.system_audio_enabled)

    def test_legacy_model_auto_upgrade(self):
        # Emulate older config containing deprecated gemini-2.5-flash
        raw_json = '{"stt_model": "gemini-2.5-flash", "auto_detect_meetings": true}'
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(raw_json)

        loaded = AppConfig.load(self.config_path)
        self.assertEqual(loaded.stt_model, "gemini-3.5-flash-lite")
        self.assertTrue(loaded.auto_detect_meetings)


if __name__ == "__main__":
    unittest.main()
