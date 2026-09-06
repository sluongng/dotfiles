#!/usr/bin/env python3
"""Fixture-only collector checks; no live Codex data or runtime is touched."""
import compression.zstd
from contextlib import closing
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("observe", Path(__file__).with_name("observe.py"))
observe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observe)
NOW = 1788627600


def record(kind, payload, seconds=0):
    return {"timestamp": observe.utc(NOW + seconds), "type": kind, "payload": payload}


def user(text, seconds=0):
    return record("event_msg", {"type": "user_message", "message": text}, seconds)


def context(turn="t1"):
    return record("turn_context", {"turn_id": turn, "model": "test-model"})


class ObserveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home, self.state, self.source = (self.base / x for x in ("codex", "state", "source"))
        self.home.mkdir()
        (self.source / "config/codex/agents").mkdir(parents=True)
        (self.home / "agents").mkdir()
        config = 'model = "test-model"\nmodel_reasoning_effort = "high"\n'
        (self.home / "config.toml").write_text(config)
        (self.source / "config/codex/config.toml").write_text(config)
        self.db = self.home / "state_5.sqlite"
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, source TEXT, updated_at INTEGER, created_at INTEGER, first_user_message TEXT, agent_path TEXT)")
        self.args = observe.parser().parse_args(["--state-dir", str(self.state), "--codex-home", str(self.home), "--source-root", str(self.source)])

    def thread(self, tid="root", entries=None, *, source="cli", first="", created=NOW, updated=NOW):
        path = self.home / (tid + ".jsonl")
        entries = entries if entries is not None else [record("session_meta", {"id": tid, "source": source}), context(), user("Fix the actual problem.")]
        self.write(path, entries)
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?)", (tid, str(path), source, updated, created, first, None))
        return path

    def write(self, path, entries, mode="w"):
        with path.open(mode) as h:
            for item in entries:
                h.write(json.dumps(item) + "\n")

    def run_collector(self, now=NOW):
        return observe.collect(self.args, now=now)

    def events(self):
        return [json.loads(p.read_text()) for p in (self.state / "events").glob("*.json")]

    def checkpoint(self):
        return json.loads((self.state / "collector-state.json").read_text())

    def test_incremental_old_thread_and_rerun(self):
        path = self.thread(created=NOW - 100 * 86400)
        self.assertEqual(self.run_collector()["events_created"], 1)
        first = self.checkpoint()["threads"]["root"]["offset"]
        self.assertEqual(self.run_collector()["events_created"], 0)
        self.write(path, [context("t2"), user("Keep going until the check passes.", 1)], "a")
        # File growth is observed even before DB updated_at catches up.
        self.assertEqual(self.run_collector(NOW + 2)["events_created"], 1)
        self.assertGreater(self.checkpoint()["threads"]["root"]["offset"], first)
        self.assertEqual(len(self.events()), 2)

    def test_duplicate_response_event_and_final_outcome(self):
        self.thread(entries=[context(), user("One correction"), record("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "One correction"}]}), record("response_item", {"type": "message", "role": "assistant", "phase": "final_answer", "content": [{"type": "output_text", "text": "The actual validation passed."}]})])
        self.assertEqual(self.run_collector()["events_created"], 2)
        self.assertEqual({e["kind"] for e in self.events()}, {"user_message", "task_outcome"})

    def test_paginated_item_completion_and_legacy_final_deduplicate(self):
        self.thread(entries=[context(), record("event_msg", {"type": "item_completed", "item": {"type": "UserMessage", "content": [{"type": "Text", "text": "Native paginated prompt"}]}}), record("event_msg", {"type": "item_completed", "item": {"type": "AgentMessage", "phase": "final_answer", "content": [{"type": "Text", "text": "Verified outcome"}]}}), record("event_msg", {"type": "task_complete", "last_agent_message": "Verified outcome"})])
        self.run_collector()
        self.assertEqual(len(self.events()), 2)
        self.assertEqual({e["text"] for e in self.events()}, {"Native paginated prompt", "Verified outcome"})

    def test_compression_migration_and_append(self):
        path = self.thread()
        self.run_collector()
        compressed = Path(str(path) + ".zst")
        with compression.zstd.open(compressed, "wb") as h:
            h.write(path.read_bytes())
            h.write((json.dumps(context("t2")) + "\n" + json.dumps(user("Check the deployed result", 1)) + "\n").encode())
        path.unlink()
        self.assertEqual(self.run_collector(NOW + 2)["events_created"], 1)
        self.assertEqual(self.run_collector(NOW + 3)["events_created"], 0)
        self.assertEqual(len(self.events()), 2)

    def test_rewrite_replays_without_duplicate_events(self):
        path = self.thread()
        self.run_collector()
        replacement = path.with_suffix(".new")
        self.write(replacement, [record("event_msg", {"type": "warning", "message": "new storage prefix"}), context(), user("Fix the actual problem."), context("t2"), user("A new correction", 1)])
        replacement.replace(path)
        self.assertEqual(self.run_collector()["events_created"], 1)
        self.assertEqual(len(self.events()), 2)

    def test_inherited_child_and_root_fork_never_learned(self):
        self.thread("child", source='{"subagent":{"thread_spawn":{"parent_thread_id":"parent"}}}')
        self.thread("fork", entries=[record("session_meta", {"id": "fork", "source": "cli", "forked_from_id": "parent"}), context(), user("Copied parent correction")])
        self.assertEqual(self.run_collector()["events_created"], 0)
        self.assertEqual(self.events(), [])

    def test_automation_is_nonhuman_and_meta_jobs_excluded(self):
        self.thread("regular", first="Automation ID: nightly-review", entries=[context(), user("Automation ID: nightly-review\nInspect recent runs"), record("response_item", {"type": "message", "role": "assistant", "phase": "final_answer", "content": [{"text": "Finished nightly check"}]})])
        self.thread("meta", first="Aton automation ID: codex-improve", entries=[context(), user("Improve our instructions")])
        self.thread("setup-thread")
        self.state.mkdir()
        (self.state / "excluded-roots.json").write_text(json.dumps(["setup-thread"]))
        self.thread("explicit")
        self.args.exclude_root.append("explicit")
        self.run_collector()
        events = self.events()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["thread_id"] == "regular" and e["kind"] == "task_outcome" and e["metadata"]["automation"] and not e["metadata"]["human"] for e in events))

    def test_invalid_local_exclusions_do_not_advance_collection(self):
        self.thread()
        self.state.mkdir()
        for invalid in ({"root": True}, [42], ["bad\nargument"]):
            (self.state / "excluded-roots.json").write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError, "list of thread IDs"):
                self.run_collector()
            self.assertFalse((self.state / "collector-state.json").exists())
            self.assertEqual(self.events(), [])

    def test_injected_instructions_filtered(self):
        self.thread(entries=[context(), *[user(prefix + "\nDo not learn this") for prefix in observe.INJECTED], user("The user correction")])
        self.run_collector()
        self.assertEqual([e["text"] for e in self.events()], ["The user correction"])

    def test_bad_read_never_acknowledges_and_recovers(self):
        path = self.thread()
        self.run_collector()
        before = self.checkpoint()["threads"]["root"]
        self.write(path, [context("t2"), user("Must not be lost", 1)], "a")
        with path.open("a") as h:
            h.write("{malformed}\n")
        self.assertEqual(self.run_collector()["errors"], 1)
        self.assertEqual(self.checkpoint()["threads"]["root"], before)
        self.assertEqual(len(self.events()), 1)
        path.write_bytes(path.read_bytes().replace(b"{malformed}\n", b""))
        self.assertEqual(self.run_collector()["events_created"], 1)

    def test_bad_thread_does_not_starve_bounded_queue(self):
        self.args.max_threads = 1
        broken = self.thread("a-broken")
        broken.write_text("{broken}\n")
        self.thread("z-good")
        self.assertEqual(self.run_collector()["errors"], 1)
        self.assertNotIn("a-broken", self.checkpoint()["threads"])
        self.assertEqual(self.run_collector(NOW + 1)["events_created"], 1)

    def test_bootstrap_cutoff_persists_across_bounded_catchup(self):
        self.args.max_lines = 2
        self.thread(entries=[record("session_meta", {"id": "root"}), context(), user("Old event", -8 * 86400), user("Recent event", -6 * 86400), user("Newest event")])
        for i in range(4):
            self.run_collector(NOW + i * 86400)
        self.assertEqual({e["text"] for e in self.events()}, {"Recent event", "Newest event"})
        self.assertEqual(self.checkpoint()["cutoff"], NOW - 7 * 86400)

    def test_partial_write_retried_after_growth(self):
        path = self.thread()
        self.run_collector()
        line = (json.dumps(user("Completed later", 1)) + "\n").encode()
        with path.open("ab") as h:
            h.write(line[:20])
        self.assertEqual(self.run_collector()["events_created"], 0)
        with path.open("ab") as h:
            h.write(line[20:])
        self.assertEqual(self.run_collector()["events_created"], 1)

    def test_private_immutable_files_and_exclusive_lock(self):
        self.thread()
        self.run_collector()
        for p in [self.state, self.state / "events"]:
            self.assertEqual(p.stat().st_mode & 0o777, 0o700)
        event_file = next((self.state / "events").glob("*.json"))
        original = event_file.read_bytes()
        self.assertEqual(event_file.stat().st_mode & 0o777, 0o600)
        self.assertFalse(observe.atomic_json(event_file, {"changed": True}, immutable=True))
        self.assertEqual(event_file.read_bytes(), original)
        with (self.state / "collector.lock").open("w") as h:
            fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.run_collector()["status"], "busy")

    def test_long_message_marks_capture_limit_and_keeps_usable_source_locator(self):
        original = "Context. " * 2500 + "The final correction must remain recoverable."
        path = self.thread(entries=[context(), user(original)])
        self.run_collector()
        item = self.events()[0]
        self.assertTrue(item["source_text_truncated"])
        self.assertEqual(item["original_text_chars"], len(original))
        self.assertEqual(len(item["text"]), observe.MAX_TEXT)
        self.assertNotIn("final correction", item["text"])
        locator = item["source"]
        recovered = json.loads(path.read_text().splitlines()[locator["line"] - 1])
        self.assertEqual(recovered["payload"]["message"], original)
        compressed = Path(str(path) + ".zst")
        with compression.zstd.open(compressed, "wb") as stream:
            stream.write(path.read_bytes())
        path.unlink()
        resolved = observe.resolve_rollout(locator["path"])
        with compression.zstd.open(resolved, "rt") as stream:
            recovered = json.loads(stream.readlines()[locator["line"] - 1])
        self.assertEqual(recovered["payload"]["message"], original)

    def test_health_only_allowed_fields_and_role_links(self):
        (self.home / "config.toml").write_text('model="other"\nsecret="never-expose-this"\n')
        source_role = self.source / "config/codex/agents/scout.toml"
        source_role.write_text('model="small"\nmodel_reasoning_effort="high"\n')
        (self.home / "agents/scout.toml").symlink_to(source_role)
        (self.home / "agents/broken.toml").symlink_to(self.base / "missing")
        check = observe.health(self.home, self.source)
        self.assertEqual(check["roles_checked"], 1)
        self.assertEqual({f["check"] for f in check["findings"]}, {"model_drift", "broken_symlink", "role_symlink"})
        self.assertNotIn("never-expose-this", json.dumps(check))
        self.run_collector()
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.run_collector()["events_created"], 0)


if __name__ == "__main__":
    unittest.main()
