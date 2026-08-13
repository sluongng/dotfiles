import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "notify.py"
SPEC = importlib.util.spec_from_file_location("codexdeck_notify", MODULE_PATH)
notify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = notify
SPEC.loader.exec_module(notify)

THREAD_ID = "019ffa53-63d9-7fa3-81ed-1ac5b400b3d0"
PARENT_THREAD_ID = "019ffa51-eb66-7a43-bbe2-1b64126053e0"


def create_state_db(codex_home: Path, source: str, thread_source: str | None) -> None:
    codex_home.mkdir()
    with closing(sqlite3.connect(codex_home / "state_5.sqlite")) as connection:
        connection.executescript(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                agent_path TEXT,
                thread_source TEXT
            );
            CREATE TABLE thread_spawn_edges (
                parent_thread_id TEXT NOT NULL,
                child_thread_id TEXT NOT NULL PRIMARY KEY
            );
            """
        )
        connection.execute(
            "INSERT INTO threads VALUES (?, ?, ?, ?)",
            (THREAD_ID, source, "/root/scout", thread_source),
        )
        if thread_source == "subagent":
            connection.execute(
                "INSERT INTO thread_spawn_edges VALUES (?, ?)",
                (PARENT_THREAD_ID, THREAD_ID),
            )
        connection.commit()


def create_rollout(codex_home: Path, source: object) -> None:
    rollout_dir = codex_home / "sessions/2026/08/13"
    rollout_dir.mkdir(parents=True)
    metadata = {"type": "session_meta", "payload": {"id": THREAD_ID, "source": source}}
    (rollout_dir / f"rollout-2026-08-13T10-00-00-{THREAD_ID}.jsonl").write_text(
        json.dumps(metadata) + "\n"
    )


class NotifyTest(unittest.TestCase):
    def run_hook(self, codex_home: Path, state_home: Path) -> dict:
        payload = json.dumps(
            {
                "type": "agent-turn-complete",
                "thread-id": THREAD_ID,
                "turn-id": "turn-1",
                "cwd": "/work/project",
            }
        )
        with (
            mock.patch.object(sys, "argv", [str(MODULE_PATH), payload]),
            mock.patch.dict(
                "os.environ",
                {"CODEX_HOME": str(codex_home), "XDG_STATE_HOME": str(state_home)},
                clear=True,
            ),
            mock.patch.object(notify.time, "time", return_value=50),
        ):
            self.assertEqual(notify.main(), 0)
        return json.loads((state_home / "codex-deck/events.jsonl").read_text())

    def test_root_completion_posts_desktop_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_db(root / "codex", "vscode", "cli")
            with mock.patch.object(notify.subprocess, "run") as run:
                event = self.run_hook(root / "codex", root / "state")
        self.assertEqual(event["session-kind"], "root")
        self.assertEqual(event["notification-policy"], "show")
        run.assert_called_once()

    def test_subagent_completion_is_logged_without_notification(self):
        source = json.dumps(
            {
                "subagent": {
                    "thread_spawn": {
                        "parent_thread_id": PARENT_THREAD_ID,
                        "agent_path": "/root/scout",
                    }
                }
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_db(root / "codex", source, "subagent")
            with mock.patch.object(notify.subprocess, "run") as run:
                event = self.run_hook(root / "codex", root / "state")
        self.assertEqual(event["session-kind"], "subagent")
        self.assertNotIn("parent-thread-id", event)
        self.assertNotIn("agent-path", event)
        self.assertEqual(event["notification-policy"], "suppress")
        run.assert_not_called()

    def test_unknown_completion_is_logged_without_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(notify.subprocess, "run") as run:
                event = self.run_hook(root / "codex", root / "state")
        self.assertEqual(event["session-kind"], "unknown")
        self.assertEqual(event["notification-policy"], "suppress")
        run.assert_not_called()

    def test_root_rollout_fallback_posts_desktop_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_rollout(root / "codex", "vscode")
            with mock.patch.object(notify.subprocess, "run") as run:
                event = self.run_hook(root / "codex", root / "state")
        self.assertEqual(event["session-kind"], "root")
        self.assertEqual(event["notification-policy"], "show")
        run.assert_called_once()

    def test_subagent_rollout_fallback_is_logged_without_notification(self):
        source = {
            "subagent": {
                "thread_spawn": {
                    "parent_thread_id": PARENT_THREAD_ID,
                    "agent_path": "/root/scout",
                }
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_rollout(root / "codex", source)
            with mock.patch.object(notify.subprocess, "run") as run:
                event = self.run_hook(root / "codex", root / "state")
        self.assertEqual(event["session-kind"], "subagent")
        self.assertNotIn("parent-thread-id", event)
        self.assertNotIn("agent-path", event)
        self.assertEqual(event["notification-policy"], "suppress")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
