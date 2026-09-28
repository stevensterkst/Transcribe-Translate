import tempfile
import unittest
from pathlib import Path

from core.config import default_output_dir, resolve_output_dir


class OutputDirTests(unittest.TestCase):
    def test_default_is_downloads(self):
        self.assertEqual(default_output_dir(), Path.home() / "Downloads" / "Transcribe-Translate")

    def test_legacy_repo_output_migrates(self):
        self.assertEqual(resolve_output_dir("output"), default_output_dir())

    def test_project_local_output_migrates(self):
        self.assertEqual(resolve_output_dir("C:/Users/test/OpenAI/transcribe-translate/output"), default_output_dir())

    def test_explicit_external_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "results"
            self.assertEqual(resolve_output_dir(target), target)


if __name__ == "__main__":
    unittest.main()
