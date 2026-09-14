import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "manager.py"
SPEC = importlib.util.spec_from_file_location("codexdeck_manager", MODULE_PATH)
manager = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = manager
SPEC.loader.exec_module(manager)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class DictationCompletionTest(unittest.TestCase):
    def test_stop_polls_completion_and_preserves_trailing_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            path.write_text("dictated line\n")
            done_path = Path(str(path) + ".done")

            def publish_completion(_seconds):
                done_path.write_text(json.dumps({"status": "ok", "chars": 14}))

            with (
                mock.patch.object(
                    manager.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0),
                ) as run,
                mock.patch.object(manager.time, "sleep", side_effect=publish_completion),
            ):
                self.assertEqual(manager.stop_global_dictation(path), 0)

            run.assert_called_once_with(
                [str(manager.VOXTYPE), "record", "stop"],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(manager.read_dictation_transcript(path), "dictated line\n")

    def test_existing_completion_is_not_stopped_again(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            path.write_text("already complete\n")
            Path(str(path) + ".done").write_text(
                json.dumps({"status": "ok", "chars": 17})
            )
            with mock.patch.object(manager.subprocess, "run") as run:
                self.assertEqual(manager.stop_global_dictation(path), 0)

            run.assert_not_called()
            self.assertEqual(manager.read_dictation_transcript(path), "already complete\n")

    def test_empty_error_and_malformed_completion_preserve_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            done_path = Path(str(path) + ".done")
            path.write_text("recovery text\n")

            for body, expected in (
                (json.dumps({"status": "empty"}), 3),
                (json.dumps({"status": "error"}), 1),
                ("not json", 1),
            ):
                with self.subTest(body=body):
                    done_path.write_text(body)
                    with mock.patch.object(manager.subprocess, "run") as run:
                        self.assertEqual(manager.stop_global_dictation(path), expected)
                    run.assert_not_called()
                    self.assertEqual(path.read_text(), "recovery text\n")

    def test_timeout_preserves_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            path.write_text("recovery text\n")
            clock = FakeClock()
            with (
                mock.patch.object(
                    manager.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0),
                ),
                mock.patch.object(manager.time, "monotonic", clock.monotonic),
                mock.patch.object(manager.time, "sleep", clock.sleep),
            ):
                self.assertEqual(manager.stop_global_dictation(path), 4)

            self.assertEqual(path.read_text(), "recovery text\n")
            self.assertFalse(Path(str(path) + ".done").exists())


if __name__ == "__main__":
    unittest.main()
