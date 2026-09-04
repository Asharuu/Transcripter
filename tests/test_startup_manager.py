"""Unit tests for Windows Startup Apps integration and startup_manager."""

import os
import unittest
from pathlib import Path
from src.core.startup_manager import (
    get_project_paths,
    is_startup_enabled,
    set_startup_enabled,
    install_start_menu_shortcut,
)


class TestStartupManager(unittest.TestCase):

    def test_project_paths(self):
        project_root, pythonw, icon = get_project_paths()
        self.assertTrue(project_root.exists())
        self.assertTrue(project_root.is_dir())
        self.assertTrue(icon.exists())

    @unittest.skipUnless(os.name == "nt", "Windows registry tests require Windows OS")
    def test_startup_lifecycle(self):
        # Test enabling startup
        ok, msg = set_startup_enabled(True, start_minimized=True)
        self.assertTrue(ok, f"Failed to enable startup: {msg}")
        self.assertTrue(is_startup_enabled())

        # Test start menu shortcut
        ok_sm, msg_sm = install_start_menu_shortcut()
        self.assertTrue(ok_sm, f"Failed to install start menu shortcut: {msg_sm}")

        # Keep enabled as requested by user, but test disabling logic
        ok_dis, _ = set_startup_enabled(False)
        self.assertTrue(ok_dis)
        self.assertFalse(is_startup_enabled())

        # Restore enabled state
        ok_en, _ = set_startup_enabled(True, start_minimized=True)
        self.assertTrue(ok_en)
        self.assertTrue(is_startup_enabled())


if __name__ == "__main__":
    unittest.main()
