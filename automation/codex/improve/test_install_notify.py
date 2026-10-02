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
            self.assertIn("retrospective.py", dropin)
            self.assertNotIn("ExecCondition=", dropin)
            self.assertTrue(any(call.args == ('systemctl', '--user', 'disable', '--now', 'codex-observe.timer')
                                for call in run.call_args_list))

    def test_retrospective_notifies_applied_changes_without_legacy_proposal_queue(self):
        with tempfile.TemporaryDirectory(prefix="retrospect-notify-test-") as folder:
            state = Path(folder)
            (state / "retrospective/run").mkdir(parents=True)
            (state / "retrospective/history").mkdir()
            (state / "retrospective/run/manifest.json").write_text(json.dumps({"run_id": "run"}))
            history = state / "retrospective/history/run.json"
            (state / "pipeline-state.json").write_text(json.dumps({"reviewed": {}, "candidates": {
                "legacy": {"status": "needsreview", "created_at": "2020-01-01T00:00:00Z"}}}))
            with (patch.object(sys, "argv", ["notify.py", "--state-dir", str(state)]),
                  patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                  patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run):
                history.write_text(json.dumps({"result": {"changed_files": []}}))
                notify.main()
                self.assertEqual(run.call_count, 0)
                history.write_text(json.dumps({"result": {"changed_files": ["/example/AGENTS.md"]}}))
                notify.main()
                notify.main()
                self.assertEqual(run.call_count, 1)
                self.assertIn("Codex retrospective: 1 file(s) improved", run.call_args.args[0])

    def test_failed_first_snapshot_does_not_read_legacy_proposal_state(self):
        with tempfile.TemporaryDirectory(prefix="retrospect-notify-test-") as folder:
            state = Path(folder)
            (state / "retrospective/run").mkdir(parents=True)
            (state / "pipeline-state.json").write_text("corrupt legacy state")
            with (patch.object(sys, "argv", ["notify.py", "--state-dir", str(state), "--service-result", "exit-code"]),
                  patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                  patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run):
                notify.main()
                self.assertEqual(run.call_count, 1)
                self.assertIn("Codex improvement review failed", run.call_args.args[0])

    def test_failure_before_manifest_and_overdue_notices_do_not_repeat(self):
        with tempfile.TemporaryDirectory(prefix="improve-notify-test-") as folder:
            state = Path(folder)
            candidate_id = "a" * 24
            data = {"reviewed": {}, "candidates": {candidate_id: {
                "status": "needsreview", "created_at": "2020-01-01T00:00:00Z"}}}
            (state / "pipeline-state.json").write_text(json.dumps(data))
            with (patch.object(sys, "argv", ["notify.py", "--state-dir", str(state), "--service-result", "exit-code"]),
                  patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                  patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run):
                notify.main()
                self.assertEqual(run.call_count, 2)
                notify.main()
                self.assertEqual(run.call_count, 2)
                data["candidates"][candidate_id]["status"] = "accepted"
                (state / "pipeline-state.json").write_text(json.dumps(data))
                notify.main()
                self.assertEqual(run.call_count, 3)
                notify.main()
                self.assertEqual(run.call_count, 3)
                data["candidates"][candidate_id]["status"] = "applied"
                (state / "pipeline-state.json").write_text(json.dumps(data))
                notify.main()
                self.assertEqual(run.call_count, 3)

    def test_failure_recurrence_after_success_is_notified_again(self):
        with tempfile.TemporaryDirectory(prefix="improve-notify-test-") as folder:
            state = Path(folder)
            with (patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                  patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run):
                for result, expected in (("exit-code", 1), ("exit-code", 1),
                                         ("exec-condition", 1), ("exit-code", 1),
                                         ("success", 1), ("exit-code", 2)):
                    with patch.object(sys, "argv", ["notify.py", "--state-dir", str(state), "--service-result", result]):
                        notify.main()
                    self.assertEqual(run.call_count, expected)

    def test_failed_notification_delivery_remains_retryable(self):
        with tempfile.TemporaryDirectory(prefix="improve-notify-test-") as folder:
            state = Path(folder)
            with (patch.object(sys, "argv", ["notify.py", "--state-dir", str(state), "--service-result", "timeout"]),
                  patch.object(notify.shutil, "which", return_value="/fake/notify-send"),
                  patch.object(notify.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run):
                notify.main()
                notify.main()
                self.assertEqual(run.call_count, 2)
                self.assertFalse((state / "last-notification.json").exists())

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
