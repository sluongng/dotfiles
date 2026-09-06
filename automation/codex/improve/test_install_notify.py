"""Installer and notification contracts using temporary roots and fake tools."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = load("install")
notify = load("notify")


class InstallNotifyTest(unittest.TestCase):
    def test_install_pins_roots_even_with_conflicting_environment(self):
        with tempfile.TemporaryDirectory(prefix="improve-install-test-") as folder:
            home = Path(folder)
            aton = home / ".local/bin/codex-automaton"
            aton.parent.mkdir(parents=True)
            aton.touch()
            overrides = {key: str(home / "unexpected") for key in (
                "CODEX_AUTOMATON_CONFIG_HOME", "CODEX_AUTOMATON_STATE_HOME",
                "CODEX_AUTOMATON_SYSTEMD_USER_DIR", "XDG_CONFIG_HOME", "XDG_STATE_HOME")}
            with (patch.object(install.Path, "home", return_value=home),
                  patch.dict(install.os.environ, overrides),
                  patch.object(sys, "argv", ["install.py"]),
                  patch.object(install, "run") as run,
                  patch.object(install.subprocess, "run", return_value=subprocess.CompletedProcess([], 3, "inactive\n", "")),
                  patch.object(install.shutil, "which", return_value="/usr/bin/codex"),
                  contextlib.redirect_stdout(io.StringIO())):
                install.main()
            aton_call = next(call.args for call in run.call_args_list if call.args[0] == str(aton))
            for flag, expected in (
                ("--config-home", home / ".config/codex-automaton"),
                ("--state-home", home / ".local/state/codex-automaton"),
                ("--systemd-user-dir", home / ".config/systemd/user"),
            ):
                self.assertEqual(aton_call[aton_call.index(flag) + 1], str(expected))
            self.assertIn("--no-enable", aton_call)
            self.assertFalse(any("enable" in call.args for call in run.call_args_list))
            dropin = (home / ".config/systemd/user/codex-automaton@codex-improve.service.d/improvement.conf").read_text()
            self.assertIn(str(home / ".local/state/codex-automaton/codex-improve/last-message.md"), dropin)

    def test_notifications_count_host_admissions_not_model_duplicates(self):
        with tempfile.TemporaryDirectory(prefix="improve-notify-test-") as folder:
            state = Path(folder)
            (state / "review").mkdir()
            (state / "history").mkdir()
            (state / "review/manifest.json").write_text(json.dumps({"batch_id": "batch"}))
            history = state / "history/batch.json"
            for admitted, expected_calls in (([], 0), (["new-candidate"], 1)):
                history.write_text(json.dumps({"result": {"candidates": [{}, {}]},
                                               "admitted_candidate_ids": admitted,
                                               "suppressed_candidate_ids": ["old-candidate"]}))
                with (patch.object(sys, "argv", ["notify.py", "--state-dir", str(state)]),
                      patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                      patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run):
                    notify.main()
                self.assertEqual(run.call_count, expected_calls)
                if expected_calls:
                    self.assertIn("Codex improvement: 1 candidate(s) to review", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
