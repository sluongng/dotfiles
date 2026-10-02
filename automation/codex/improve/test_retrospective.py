#!/usr/bin/env python3
"""Fixture-only public CLI lifecycle checks; never scans live user sessions."""
import compression.zstd
from contextlib import closing, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import retrospective as retro

NOW = 1788627600


def record(kind, payload, seconds=0):
    return {"timestamp": retro.observe.utc(NOW + seconds), "type": kind, "payload": payload}


def message(role, text, seconds=0, phase=None):
    return record("response_item", {"type": "message", "role": role, "phase": phase,
                                   "content": [{"type": "input_text", "text": text}]}, seconds)


class RetrospectiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home, self.state, self.aton, self.source = (self.base / x for x in ("home", "state", "aton", "source"))
        for path in (self.home, self.state, self.aton, self.source):
            path.mkdir()
        self.db = self.home / "state_5.sqlite"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, source TEXT, updated_at INTEGER, first_user_message TEXT, agent_path TEXT, cwd TEXT, title TEXT)")
        self.args = ["--state-dir", str(self.state), "--codex-home", str(self.home),
                     "--aton-state-dir", str(self.aton), "--source-root", str(self.source)]

    def thread(self, tid="root", entries=None, source="cli", agent_path=None, compressed=False, updated=NOW):
        path = self.home / (tid + ".jsonl")
        entries = entries if entries is not None else [message("user", "Please improve this", -10), message("assistant", "Done", -5)]
        text = "".join(json.dumps(item) + "\n" for item in entries)
        if compressed:
            with compression.zstd.open(str(path) + ".zst", "wt") as stream:
                stream.write(text)
        else:
            path.write_text(text)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO threads VALUES (?,?,?,?,?,?,?,?)",
                         (tid, str(path), source, updated, "", agent_path, "/workspace", "Example chat"))
        return path

    def cli(self, command, *extra, now=NOW, success=True):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(retro.time, "time", return_value=now), redirect_stdout(out), redirect_stderr(err):
            code = retro.main(self.args + [command] + list(extra))
        self.assertEqual(code, 0 if success else 1, err.getvalue())
        return json.loads(out.getvalue() if success else err.getvalue())

    def result(self, run, **updates):
        value = {"run_id": run["run_id"], "outcome": "completed", "summary": "Reviewed all chat transcripts",
                 "reviewed_chat_ids": [x["id"] for x in run["chats"]], "changed_files": [],
                 "validation": "No changes required; existing instructions cover the evidence", "assessments": []}
        value.update(updates)
        path = self.base / "result.json"
        path.write_text(json.dumps(value))
        return str(path)

    def test_all_chats_without_batch_cap_and_complete_receipt(self):
        for i in range(205):
            self.thread(f"chat-{i}")
        # Retired event queue has no bearing on transcript selection.
        (self.state / "events").mkdir()
        (self.state / "events/broken.json").write_text("not JSON")
        run = self.cli("prepare")
        self.assertEqual(run["counts"], {"chats": 205, "messages": 410})
        changed = self.source / "AGENTS.md"
        changed.write_text("New instruction\n")
        receipt = self.cli("finish", "--result", self.result(run, changed_files=[str(changed)]))
        self.assertEqual(receipt["changed_files"], [{"path": str(changed), "sha256": retro.hashlib.sha256(changed.read_bytes()).hexdigest()}])
        status = self.cli("status")
        self.assertEqual(status["watermark"], run["through"])
        self.assertEqual(status["status"], "completed")
        self.assertNotIn("pending_events", status)

    def test_transcript_only_full_text_phases_locators_compressed_forks(self):
        entries = [record("session_meta", {"cwd": "/native", "forked_from_id": "old"}),
                   message("user", "Copied prefix", -8 * 86400),
                   record("event_msg", {"type": "user_message", "message": "Duplicate"}, -20),
                   message("user", "# AGENTS.md instructions injected", -19),
                   message("user", "<skill>injected wrapper</skill>", -18),
                   record("response_item", {"type": "reasoning", "summary": "PRIVATE THINKING"}, -17),
                   record("response_item", {"type": "function_call", "name": "shell", "arguments": "TOOLS"}, -16),
                   message("user", "Native correction " + "x" * 18000, -15),
                   message("assistant", "Progress", -14, "commentary"),
                   message("assistant", "Done", -13, "final_answer"),
                   message("assistant", "Future", 1),
                   record("response_item", {"type": "message", "role": "assistant", "channel": "analysis",
                                            "content": [{"text": "HIDDEN CHAIN OF THOUGHT"}]}, -12)]
        self.thread(entries=entries, compressed=True)
        self.thread("child", agent_path="/root/worker")
        self.thread("dict-child", entries=[record("session_meta", {"source": {"subagent": "spawn"}}), message("user", "Child", -1)])
        self.thread("meta", entries=[message("user", "Automation ID: codex-improve", -1)])
        self.thread("private")
        (self.state / "excluded-roots.json").write_text('["private"]')
        run = self.cli("prepare")
        self.assertEqual([x["id"] for x in run["chats"]], ["root"])
        artifact = json.loads(Path(run["chats"][0]["path"]).read_text())
        self.assertEqual([x["text"] for x in artifact["messages"]], ["Native correction " + "x" * 18000, "Progress", "Done"])
        self.assertEqual([x["source"]["line"] for x in artifact["messages"]], [8, 9, 10])
        self.assertEqual(artifact["cwd"], "/native")
        self.assertEqual(artifact["title"], "Example chat")
        self.assertEqual(artifact["fork"], {"forked_from_id": "old"})
        self.assertEqual(Path(run["chats"][0]["path"]).stat().st_mode & 0o777, 0o600)

    def test_event_fallback_only_for_legacy_without_response_messages(self):
        self.thread(entries=[record("event_msg", {"type": "user_message", "message": "Legacy question"}, -2),
                             record("event_msg", {"type": "agent_message", "message": "Legacy answer"}, -1)])
        run = self.cli("prepare")
        artifact = json.loads(Path(run["chats"][0]["path"]).read_text())
        self.assertEqual([x["text"] for x in artifact["messages"]], ["Legacy question", "Legacy answer"])

    def test_all_root_chat_surfaces_including_mcp_and_future_sources(self):
        self.thread("mcp-root", source="mcp")
        self.thread("new-root", source="future-chat-surface")
        self.thread("json-child", source=json.dumps({"subagent": {"thread_spawn": "parent"}}))
        run = self.cli("prepare")
        self.assertEqual([chat["id"] for chat in run["chats"]], ["mcp-root", "new-root"])

    def test_failure_partial_unknown_duplicate_and_retry_immutable(self):
        self.thread()
        run = self.cli("prepare")
        original = Path(run["chats"][0]["path"]).read_bytes()
        self.thread(entries=[message("user", "New text", 1)], updated=NOW + 1)
        retry = self.cli("prepare", now=NOW + 2)
        self.assertEqual(retry["run_id"], run["run_id"])
        self.assertEqual(Path(retry["chats"][0]["path"]).read_bytes(), original)
        for ids in ([], ["unknown"], ["root", "root"]):
            self.cli("finish", "--result", self.result(run, reviewed_chat_ids=ids), success=False)
            self.assertIsNone(self.cli("status")["watermark"])
        self.cli("finish", "--result", self.result(run))
        next_run = self.cli("prepare", now=NOW + 2)
        self.assertNotEqual(next_run["run_id"], run["run_id"])
        self.assertEqual(next_run["since"], run["through"])
        self.assertEqual(next_run["counts"], {"chats": 1, "messages": 1})

    def test_migration_ignores_aton_success_and_uses_completed_history(self):
        directory = self.aton / "codex-improve"
        directory.mkdir()
        receipt = directory / "last-run.json"
        receipt.write_text(json.dumps({"ok": True, "finished_unix": NOW - 100}))
        (directory / "attempts.jsonl").write_text(json.dumps({"state": "COMPLETED", "recorded_unix": NOW - 100,
                                                              "infrastructure": {"outcome": "completed"}}) + "\n")
        self.thread(entries=[message("user", "Before watermark", -101), message("user", "After", -99)])
        run = self.cli("prepare")
        self.assertEqual(run["since"], retro.observe.utc(NOW - 7 * 86400))
        self.assertEqual(run["counts"]["messages"], 2)
        # A failed Aton attempt cannot become the successful migration bookmark.
        other_state = self.base / "other-state"
        (other_state / "history").mkdir(parents=True)
        (other_state / "history/old.json").write_text(json.dumps({"finished_at": retro.observe.utc(NOW - 80)}))
        receipt.write_text(json.dumps({"ok": False, "finished_unix": NOW - 10}))
        self.args[1] = str(other_state)
        fallback = self.cli("prepare")
        self.assertEqual(fallback["since"], retro.observe.utc(NOW - 80))
        self.assertEqual(fallback["counts"], {"chats": 0, "messages": 0})
        self.cli("finish", "--result", self.result(fallback))
        self.assertEqual(self.cli("status")["watermark"], fallback["through"])

    def test_legacy_completed_review_precedes_newer_aton_process_success(self):
        directory = self.aton / "codex-improve"
        directory.mkdir()
        (directory / "last-run.json").write_text(json.dumps({"ok": True, "finished_unix": NOW - 10}))
        (directory / "attempts.jsonl").write_text(json.dumps({"state": "FAILED", "recorded_unix": NOW - 9,
                                                              "infrastructure": {"outcome": "failed"}}) + "\n")
        (self.state / "history").mkdir()
        (self.state / "history/completed.json").write_text(json.dumps({"finished_at": retro.observe.utc(NOW - 100)}))
        self.thread(entries=[message("user", "Unreviewed correction", -80)])
        run = self.cli("prepare")
        self.assertEqual(run["since"], retro.observe.utc(NOW - 100))
        self.assertEqual(run["counts"], {"chats": 1, "messages": 1})

    def test_unproven_aton_receipt_bootstraps_conservatively(self):
        directory = self.aton / "codex-improve"
        directory.mkdir()
        (directory / "last-run.json").write_text(json.dumps({"ok": True, "finished_unix": NOW - 10}))
        self.thread(entries=[message("user", "Unreviewed correction", -80)])
        run = self.cli("prepare")
        self.assertEqual(run["since"], retro.observe.utc(NOW - 7 * 86400))
        self.assertEqual(run["counts"], {"chats": 1, "messages": 1})

    def test_source_parse_failure_does_not_publish_snapshot_or_watermark(self):
        path = self.thread()
        path.write_text(path.read_text() + "broken\n")
        self.cli("prepare", success=False)
        self.assertEqual(self.cli("status"), {"watermark": None, "status": "idle", "current": None})

    def test_same_second_database_timestamp_does_not_drop_later_message(self):
        self.thread()
        run = self.cli("prepare", now=NOW + 0.2)
        self.cli("finish", "--result", self.result(run), now=NOW + 0.2)
        self.thread(entries=[message("user", "Later same second", 0.7)], updated=NOW)
        next_run = self.cli("prepare", now=NOW + 1)
        self.assertEqual(next_run["counts"], {"chats": 1, "messages": 1})

    def test_result_schema_and_unknown_assessment_and_missing_files(self):
        self.thread()
        run = self.cli("prepare")
        for updates in ({"summary": ""}, {"outcome": "incomplete"}, {"changed_files": ["relative.md"]},
                        {"changed_files": [str(self.base / "absent.md")]},
                        {"validation": " "}, {"extra": "field"},
                        {"assessments": [{"chat_ids": ["unknown"], "disposition": "changed", "rationale": "test"}]}):
            self.cli("finish", "--result", self.result(run, **updates), success=False)
        self.assertIsNone(self.cli("status")["watermark"])

    def test_report_failure_retains_watermark_and_snapshot(self):
        self.thread()
        run = self.cli("prepare")
        report = self.state / "latest.md"
        target = self.base / "target"
        target.write_text("Preserve")
        for symlink in (True, False):
            if symlink:
                report.symlink_to(target)
            else:
                report.mkdir()
            self.cli("finish", "--result", self.result(run), success=False)
            self.assertIsNone(self.cli("status")["watermark"])
            self.assertEqual(self.cli("prepare", now=NOW + 10)["run_id"], run["run_id"])
            if symlink:
                report.unlink()
            else:
                report.rmdir()
        self.assertEqual(target.read_text(), "Preserve")
        self.cli("finish", "--result", self.result(run))
        self.assertEqual(self.cli("status")["watermark"], run["through"])

    def test_state_commit_failure_after_receipt_retains_same_snapshot(self):
        self.thread()
        run = self.cli("prepare")
        result = self.result(run)
        original = retro.observe.atomic_json
        def fail_state(path, value, **kwargs):
            if path == self.state / "retrospective/state.json":
                raise OSError("fixture state commit failure")
            return original(path, value, **kwargs)
        with patch.object(retro.observe, "atomic_json", side_effect=fail_state):
            self.cli("finish", "--result", result, success=False)
        self.assertIsNone(self.cli("status")["watermark"])
        self.assertEqual(self.cli("status")["status"], "ready")
        self.assertEqual(self.cli("prepare", now=NOW + 20)["run_id"], run["run_id"])
        changed = self.base / "AGENTS.md"
        changed.write_text("A further improvement made during the retry.\n")
        result = self.result(run, summary="Retry includes an additional change.", changed_files=[str(changed)])
        receipt = self.cli("finish", "--result", result)
        self.assertEqual(receipt["result"], json.loads(Path(result).read_text()))
        self.assertIn(str(changed), (self.state / "latest.md").read_text())
        self.assertEqual(self.cli("status")["status"], "completed")
        report = (self.state / "latest.md").read_text()
        repeated = self.cli("finish", "--result", self.result(run, summary="Must not replace committed history."))
        self.assertEqual(repeated, receipt)
        self.assertEqual((self.state / "latest.md").read_text(), report)


if __name__ == "__main__":
    unittest.main()
