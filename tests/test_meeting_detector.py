"""Unit tests for MeetingDetector and meeting window parsing."""

import unittest
from src.audio.meeting_detector import parse_meeting_title, MeetingDetector


class TestMeetingDetector(unittest.TestCase):

    def test_parse_google_meet(self):
        cases = [
            ("Meet - abc-defg-hij - Google Chrome", ("Google Meet", "abc-defg-hij")),
            ("Meet: Weekly Standup | Microsoft Edge", ("Google Meet", "Weekly Standup")),
            ("Meet - Sprint Retro - Brave", ("Google Meet", "Sprint Retro")),
            ("https://meet.google.com/xyz-123 - Google Chrome", ("Google Meet", "https://meet.google.com/xyz-123")),
        ]
        for title, expected in cases:
            res = parse_meeting_title(title)
            self.assertIsNotNone(res, f"Failed on: {title}")
            self.assertEqual(res[0], expected[0])
            self.assertEqual(res[1], expected[1])

    def test_parse_teams(self):
        cases = [
            ("Weekly Standup | Microsoft Teams", ("Microsoft Teams", "Weekly Standup")),
            ("Meeting | Microsoft Teams", ("Microsoft Teams", "Teams Meeting")),
            ("Teams Meeting", ("Microsoft Teams", "Teams Meeting")),
            ("Call with John Doe | Microsoft Teams", ("Microsoft Teams", "Call with John Doe")),
        ]
        for title, expected in cases:
            res = parse_meeting_title(title)
            self.assertIsNotNone(res, f"Failed on: {title}")
            self.assertEqual(res[0], expected[0])
            self.assertEqual(res[1], expected[1])

    def test_parse_zoom(self):
        cases = [
            ("Zoom Meeting - Product Design", ("Zoom", "Product Design")),
            ("Zoom Workplace", ("Zoom", "Zoom Meeting")),
            ("Zoom Webinar", ("Zoom", "Zoom Meeting")),
        ]
        for title, expected in cases:
            res = parse_meeting_title(title)
            self.assertIsNotNone(res, f"Failed on: {title}")
            self.assertEqual(res[0], expected[0])
            self.assertEqual(res[1], expected[1])

    def test_ignore_normal_windows(self):
        cases = [
            "Transcripter — Real-time Desktop Transcription",
            "Asharuu/Transcripter and 24 more pages - Personal - Microsoft Edge",
            "Epic Games Launcher",
            "Steam",
            "WhatsApp",
            "Windows PowerShell",
            "Downloads - File Explorer",
            "Google Search - meet people in town",
        ]
        for title in cases:
            res = parse_meeting_title(title)
            self.assertIsNone(res, f"Should ignore: {title}")

    def test_detector_state(self):
        detector = MeetingDetector()
        self.assertFalse(detector._is_recording)
        detector.set_recording_active(True)
        self.assertTrue(detector._is_recording)

        detector.dismiss_meeting("Google Meet", "Sync")
        self.assertIn("Google Meet::Sync", detector._dismissed_meetings)


if __name__ == "__main__":
    unittest.main()
