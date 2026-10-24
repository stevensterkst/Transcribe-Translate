from __future__ import annotations
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import AppConfig
from core.pipeline import _parse_media_duration, _range_seconds

class RangeTests(unittest.TestCase):
    def test_parse_ffmpeg_duration(self):
        sample = "Input #0, mov,mp4, from media:\\n  Duration: 00:12:34.56, start: 0.000000, bitrate: 128 kb/s"
        self.assertAlmostEqual(_parse_media_duration(sample), 754.56)

    def test_missing_ffmpeg_duration_returns_none(self):
        self.assertIsNone(_parse_media_duration("Input #0, m4a, from media:\\n  Stream #0:0: Audio: aac"))
    def test_full(self):
        self.assertIsNone(_range_seconds(AppConfig(range_mode="full", range_value=50), 600))
    def test_first_minutes(self):
        self.assertEqual(_range_seconds(AppConfig(range_mode="minutes", range_value=5), 1200), 300)
    def test_minutes_cannot_exceed_source(self):
        self.assertEqual(_range_seconds(AppConfig(range_mode="minutes", range_value=30), 600), 600)
    def test_first_percent(self):
        self.assertEqual(_range_seconds(AppConfig(range_mode="percent", range_value=50), 600), 300)
    def test_percent_cannot_exceed_100(self):
        self.assertEqual(_range_seconds(AppConfig(range_mode="percent", range_value=150), 600), 600)
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            _range_seconds(AppConfig(range_mode="bogus", range_value=10), 600)

if __name__ == "__main__":
    unittest.main()
