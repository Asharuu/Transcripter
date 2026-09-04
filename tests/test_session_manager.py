"""Unit tests for SessionManager."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.core.session_manager import SessionManager, format_relative_time


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_app_dir = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self.temp_dir
        self.manager = SessionManager()

    def tearDown(self):
        if self.orig_app_dir:
            os.environ["APPDATA"] = self.orig_app_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_rename_session(self):
        meta = self.manager.create_session(
            title="Initial Title",
            duration_seconds=120.0,
            system_audio_enabled=True,
            microphone_enabled=True,
            markdown_text="# Initial Title\n\nSome text",
            plain_text="Initial Title\n\nSome text",
        )
        self.assertEqual(meta.title, "Initial Title")

        # Rename session
        renamed = self.manager.rename_session(meta.id, "Updated New Title")
        self.assertIsNotNone(renamed)
        self.assertEqual(renamed.title, "Updated New Title")

        # Verify from index
        sessions = self.manager.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].title, "Updated New Title")

        # Verify markdown file content was updated
        with open(renamed.markdown_file, "r", encoding="utf-8") as f:
            md = f.read()
        self.assertTrue(md.startswith("# Updated New Title"))

    def test_delete_session(self):
        meta = self.manager.create_session(
            title="To Delete",
            duration_seconds=60.0,
            system_audio_enabled=True,
            microphone_enabled=True,
            markdown_text="# To Delete\n\ncontent",
            plain_text="To Delete\n\ncontent",
        )
        md_path = meta.markdown_file
        self.assertTrue(os.path.exists(md_path))

        deleted = self.manager.delete_session(meta.id)
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(md_path))
        self.assertEqual(len(self.manager.list_sessions()), 0)

    def test_format_relative_time(self):
        from datetime import datetime, timedelta
        now = datetime.now()

        iso_now = now.isoformat()
        self.assertEqual(format_relative_time(iso_now), "now")

        iso_2m = (now - timedelta(minutes=2)).isoformat()
        self.assertEqual(format_relative_time(iso_2m), "2m")

        iso_3h = (now - timedelta(hours=3)).isoformat()
        self.assertEqual(format_relative_time(iso_3h), "3h")

        iso_4d = (now - timedelta(days=4)).isoformat()
        self.assertEqual(format_relative_time(iso_4d), "4d")


if __name__ == "__main__":
    unittest.main()
