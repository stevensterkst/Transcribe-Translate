from __future__ import annotations
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import AppConfig
from core.pipeline import _range_seconds

class RangeTests(unittest.TestCase):
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
