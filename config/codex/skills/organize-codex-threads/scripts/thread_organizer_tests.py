#!/usr/bin/env python3
"""Regression tests for thread organizer eligibility."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import thread_organizer


class AutomationOriginTests(unittest.TestCase):
    def test_accepts_app_server_automation_metadata(self) -> None:
        self.assertTrue(
            thread_organizer.is_automation_thread(
                {"threadSource": "automation"},
                [{"user_prompt": "Run the job", "model_response": "Done"}],
            )
        )

    def test_accepts_aton_prompt_when_metadata_is_missing(self) -> None:
        self.assertTrue(
            thread_organizer.is_automation_thread(
                {"threadSource": None},
                [{"user_prompt": "Aton automation ID: nightly-job Run it", "model_response": "Done"}],
            )
        )

    def test_rejects_interactive_thread(self) -> None:
        self.assertFalse(
            thread_organizer.is_automation_thread(
                {"threadSource": None},
                [{"user_prompt": "Please rename this", "model_response": "Done"}],
            )
        )


class BoundedStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.candidates = self.root / "candidates.json"
        self.proposals = self.root / "proposals.json"
        self.state = self.root / "state.json"
        self.threads = [
            {"id": "a", "name": "Old a", "recencyAt": 300, "threadSource": "cli"},
            {"id": "b", "name": "Old b", "recencyAt": 200, "threadSource": "cli"},
            {"id": "c", "name": "Old c", "recencyAt": 100, "threadSource": "cli"},
        ]
        self.dialogues = {
            thread["id"]: ([{"user_prompt": f"Prompt {thread['id']}", "model_response": "Answer"}], False)
            for thread in self.threads
        }

    def run_collect(self, *extra: str) -> dict:
        args = thread_organizer.build_parser().parse_args(
            ["collect", "--all", "--output", str(self.candidates), *extra]
        )
        with mock.patch.object(thread_organizer, "AppServerClient"), \
             mock.patch.object(thread_organizer, "list_threads", return_value=self.threads), \
             mock.patch.object(thread_organizer, "recent_dialogue", side_effect=lambda _client, thread_id: self.dialogues[thread_id]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(thread_organizer.collect_command(args), 0)
        return json.loads(self.candidates.read_text())

    def run_apply(self, *, fail_id: str | None = None, change_after_preflight: bool = False) -> tuple[int, dict]:
        args = thread_organizer.build_parser().parse_args(
            ["apply", "--candidates", str(self.candidates), "--proposals", str(self.proposals),
             "--state-file", str(self.state)]
        )
        client = mock.MagicMock()
        client.__enter__.return_value = client
        if fail_id:
            def set_name(method: str, params: dict) -> dict:
                if method == "thread/name/set" and params["threadId"] == fail_id:
                    raise thread_organizer.RpcError("injected failure")
                return {}
            client.request.side_effect = set_name
        reads = {thread["id"]: 0 for thread in self.threads}
        def dialogue_for_read(_client: object, thread_id: str) -> tuple[list[dict[str, str]], bool]:
            reads[thread_id] += 1
            if change_after_preflight and thread_id == "a" and reads[thread_id] > 1:
                return ([{"user_prompt": "New post-write prompt", "model_response": "Answer"}], False)
            return self.dialogues[thread_id]
        output = io.StringIO()
        with mock.patch.object(thread_organizer, "AppServerClient", return_value=client), \
             mock.patch.object(thread_organizer, "list_threads", return_value=self.threads), \
             mock.patch.object(thread_organizer, "recent_dialogue", side_effect=dialogue_for_read), \
             contextlib.redirect_stdout(output):
            status = thread_organizer.apply_command(args)
        return status, json.loads(output.getvalue())

    def propose(self, payload: dict) -> None:
        self.proposals.write_text(json.dumps({"schema_version": 1, "proposals": [
            {"thread_id": row["thread_id"], "name": f"Rename thread {row['thread_id']}"}
            for row in payload["threads"]
        ]}))

    def test_limit_and_successful_state_skip(self) -> None:
        payload = self.run_collect("--limit", "2", "--state-file", str(self.state))
        self.assertEqual([row["thread_id"] for row in payload["threads"]], ["a", "b"])
        self.assertEqual(payload["skipped"]["limit"], 1)
        self.propose(payload)
        status, result = self.run_apply()
        self.assertEqual(status, 0)
        self.assertEqual(len(result["renamed"]), 2)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        next_payload = self.run_collect("--limit", "2", "--state-file", str(self.state))
        self.assertEqual([row["thread_id"] for row in next_payload["threads"]], ["c"])
        self.assertEqual(next_payload["skipped"]["already_processed"], 2)

    def test_changed_dialogue_aborts_before_any_write(self) -> None:
        payload = self.run_collect("--limit", "2")
        self.propose(payload)
        self.dialogues["b"] = ([{"user_prompt": "New prompt", "model_response": "Answer"}], False)
        status, result = self.run_apply()
        self.assertEqual(status, 2)
        self.assertEqual(result["renamed"], [])
        self.assertFalse(self.state.exists())

    def test_failed_write_is_not_acknowledged(self) -> None:
        payload = self.run_collect("--limit", "2")
        self.propose(payload)
        status, result = self.run_apply(fail_id="b")
        self.assertEqual(status, 2)
        self.assertEqual(len(result["renamed"]), 1)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(set(json.loads(self.state.read_text())["threads"]), {"a"})

    def test_post_write_dialogue_change_is_not_acknowledged(self) -> None:
        payload = self.run_collect("--limit", "2")
        self.propose(payload)
        status, result = self.run_apply(change_after_preflight=True)
        self.assertEqual(status, 2)
        self.assertEqual(len(result["renamed"]), 2)
        self.assertEqual(set(json.loads(self.state.read_text())["threads"]), {"b"})

if __name__ == "__main__":
    unittest.main()
