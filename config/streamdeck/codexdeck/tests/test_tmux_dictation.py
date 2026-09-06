"""Exercise terminal delivery on a private server, never the user's tmux socket."""

import contextlib
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from test_manager import manager


@unittest.skipUnless(shutil.which("tmux"), "tmux is required for terminal integration")
class TmuxDictationTest(unittest.TestCase):
    @contextlib.contextmanager
    def receiver(self, bracketed):
        with tempfile.TemporaryDirectory(prefix="codexdeck-tmux-") as directory:
            root = Path(directory)
            socket = str(root / "socket")
            output = root / "received"
            ready = root / "ready"
            script = root / "receiver.py"
            script.write_text(
                "import os, pathlib, tty\n"
                "tty.setraw(0)\n"
                f"os.write(1, {b'\x1b[?2004h' if bracketed else b'\x1b[?2004l'!r})\n"
                f"pathlib.Path({str(ready)!r}).touch()\n"
                f"with open({str(output)!r}, 'ab', buffering=0) as output:\n"
                "    while True:\n"
                "        output.write(os.read(0, 65536))\n"
            )
            run = subprocess.run

            def tmux(*args):
                return run(
                    ["tmux", "-S", socket, *args], capture_output=True,
                    text=True, timeout=5, check=True,
                ).stdout.strip()

            def isolated_run(args, **kwargs):
                self.assertEqual(args[0], "tmux")
                return run(["tmux", "-S", socket, *args[1:]], **kwargs)

            def manager_run(args, **kwargs):
                return isolated_run(args, capture_output=True, text=True, **kwargs).stdout.strip()

            try:
                pane = tmux(
                    "-f", "/dev/null", "new-session", "-d", "-s", "test",
                    "-P", "-F", "#{pane_id}",
                    shlex.join([sys.executable, str(script)]),
                )
                deadline = time.monotonic() + 5
                while not ready.exists():
                    if time.monotonic() > deadline:
                        self.fail("isolated terminal receiver did not start")
                    time.sleep(0.01)
                while tmux("display-message", "-p", "-t", pane, "#{bracket_paste_flag}") != str(int(bracketed)):
                    if time.monotonic() > deadline:
                        self.fail("terminal did not set bracketed paste mode")
                    time.sleep(0.01)
                target = manager.TmuxInputTarget("unused", "test", "0", pane, 1, "python", 1, 1)
                with (
                    mock.patch.object(manager, "tmux_target_exists", return_value=True),
                    mock.patch.object(manager.subprocess, "run", side_effect=isolated_run),
                    mock.patch.object(manager, "_run", side_effect=manager_run),
                ):
                    yield target, output
                self.assertEqual(tmux("list-buffers"), "")
            finally:
                run(["tmux", "-S", socket, "kill-server"], capture_output=True, timeout=5)

    def assert_received(self, output, expected):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if output.exists() and output.read_bytes() == expected:
                return
            time.sleep(0.01)
        self.assertEqual(output.read_bytes(), expected)

    def test_multiline_paste_preserves_exact_text_inside_brackets(self):
        text = "first line\nsecond\tline café 世界\n"
        with self.receiver(True) as (target, output):
            self.assertTrue(manager.paste_into_tmux(target, text))
            self.assert_received(output, b"\x1b[200~" + text.encode() + b"\x1b[201~")

    def test_multiline_without_bracketed_mode_is_withheld_and_retained(self):
        text = "first command\nsecond command\n"
        with self.receiver(False) as (target, output):
            recovery = output.parent / "transcript.txt"
            recovery.write_text(text)
            Path(str(recovery) + ".done").write_text(json.dumps({"status": "ok", "chars": len(text)}))
            state = manager.DeckStateManager()
            state._global_dictation_target = manager.InputTarget("unused", manager.GHOSTTY_CLASS, 1, target)
            state._global_dictation_path = recovery
            with (
                mock.patch.object(manager, "global_dictation_state", return_value="recording"),
                mock.patch.object(manager, "stop_global_dictation", return_value=0),
                mock.patch.object(manager, "_notify"),
            ):
                state._toggle_global_dictation()
            self.assertEqual(recovery.read_text(), text)
            time.sleep(0.05)
            self.assertEqual(output.read_bytes(), b"")

    def test_single_line_without_bracketed_mode_does_not_add_enter(self):
        with self.receiver(False) as (target, output):
            self.assertTrue(manager.paste_into_tmux(target, "editable text"))
            self.assert_received(output, b"editable text")

    def test_tab_without_bracketed_mode_is_withheld(self):
        with self.receiver(False) as (target, output):
            self.assertFalse(manager.paste_into_tmux(target, "text\tcompletion"))
            time.sleep(0.05)
            self.assertEqual(output.read_bytes(), b"")
