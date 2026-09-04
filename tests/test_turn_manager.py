"""Unit tests for SpeakerTurnManager."""

import unittest
from datetime import datetime
from src.core.speaker_manager import SpeakerTurnManager


class TestSpeakerTurnManager(unittest.TestCase):

    def setUp(self):
        self.manager = SpeakerTurnManager()

    def test_same_speaker_merges_across_pauses(self):
        """Verify multiple speech segments from the same speaker stay in ONE block."""
        # Turn 1: Speaker 1 says sentence 1
        self.manager.add_segment("Speaker 1 (You)", "Hari ini kita membahas OOP.", 0.0, 3.2)
        # Turn 1 continued: Speaker 1 speaks again after pause
        self.manager.add_segment("Speaker 1 (You)", "Pertama kita akan membahas class.", 4.5, 7.8)
        # Turn 1 continued: Speaker 1 speaks a 3rd sentence
        self.manager.add_segment("Speaker 1 (You)", "Class merupakan blueprint...", 8.5, 11.2)

        self.assertEqual(len(self.manager.turns), 1)
        turn = self.manager.turns[0]
        self.assertEqual(turn.speaker, "Speaker 1 (You)")
        expected_text = "Hari ini kita membahas OOP. Pertama kita akan membahas class. Class merupakan blueprint..."
        self.assertEqual(turn.full_text, expected_text)

    def test_speaker_change_creates_new_block(self):
        """Verify changing speaker finalizes current block and creates a new one."""
        self.manager.add_segment("Speaker 1 (You)", "Halo semuanya.", 0.0, 2.0)
        self.manager.add_segment("Speaker 2 (Remote)", "Halo juga Pak.", 3.0, 5.0)
        self.manager.add_segment("Speaker 1 (You)", "Baik, mari kita mulai.", 6.0, 8.0)

        self.assertEqual(len(self.manager.turns), 3)
        self.assertEqual(self.manager.turns[0].speaker, "Speaker 1 (You)")
        self.assertEqual(self.manager.turns[1].speaker, "Speaker 2 (Remote)")
        self.assertEqual(self.manager.turns[2].speaker, "Speaker 1 (You)")

    def test_markdown_export_format(self):
        """Verify markdown export matches clean specification with single title and date."""
        self.manager.add_segment("Speaker 1 (You)", "Hari ini kita membahas OOP.", 0.0, 3.0)
        self.manager.add_segment("Speaker 2 (Remote)", "Pak, apakah ada tugas?", 4.0, 6.0)

        md = self.manager.to_markdown("Dasar OOP", datetime(2026, 9, 3, 14, 0, 0), 360)
        self.assertIn("# Dasar OOP", md)
        self.assertIn("**Date & Time:** 2026-09-03 14:00:00", md)
        self.assertIn("**Duration:** 06:00", md)
        self.assertIn("### Speaker 1 (You)", md)
        self.assertIn("Hari ini kita membahas OOP.", md)
        self.assertIn("### Speaker 2 (Remote)", md)
        self.assertIn("Pak, apakah ada tugas?", md)


if __name__ == "__main__":
    unittest.main()
