import argparse
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

SPEC = importlib.util.spec_from_file_location("pipeline", Path(__file__).with_name("pipeline.py"))
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.state = self.base / "state"
        self.target = "config/codex/skills/example/SKILL.md"
        self.original = "---\nname: example\ndescription: Example skill.\n---\n\nAlways read every reference.\n"
        path = self.root / self.target
        path.parent.mkdir(parents=True)
        path.write_text(self.original)
        self.args = argparse.Namespace(state_dir=self.state, source_root=self.root, codex_home=self.base / "codex")
        self.event("a" * 64)

    def event(self, event_id, text="The skill loaded unrelated references again."):
        p.atomic_json(self.state / "events" / f"{event_id}.json", {
            "id": event_id, "root_id": "root", "thread_id": "thread", "timestamp": "2026-09-05T12:00:00Z",
            "kind": "user_message", "text": text, "source": {"path": "private/session.jsonl", "line": 3}})

    def prepare(self):
        with p.locked(self.state):
            return p.prepare(self.args)

    def candidate(self):
        return {"evidence_event_ids": ["a" * 64], "problem": "Unrelated references were read.",
                "proposed_change": "Load supporting references only when relevant.", "target": self.target,
                "patch": f"--- a/{self.target}\n+++ b/{self.target}\n@@ -6 +6 @@\n-Always read every reference.\n+Read references only when relevant.\n",
                "checks": ["markdown", "frontmatter"], "expected_behavior": "Read only relevant references.", "confidence": "high"}

    def result(self, candidate=True):
        current = p.active(self.state)
        return {"batch_id": current["batch_id"], "outcome": "reviewed" if candidate else "no_change",
                "summary": "One recurring issue." if candidate else "No reusable change.",
                "candidates": [self.candidate()] if candidate else []}

    def finish(self, result):
        self.args.result = self.base / "result.json"
        p.atomic_json(self.args.result, result)
        with p.locked(self.state):
            return p.finish(self.args)

    def dated_event(self, event_id, when, root, text="Ordinary task detail", kind="user_message"):
        self.event(event_id, text)
        path = self.state / "events" / f"{event_id}.json"
        event = p.read_json(path)
        event.update(timestamp=when, root_id=root, kind=kind)
        p.atomic_json(path, event)

    def test_selection_reserves_oldest_and_groups_priority_context(self):
        (self.state / "events" / f"{'a' * 64}.json").unlink()
        for i in range(15):
            self.dated_event(f"ordinary{i:02d}", "2026-09-10T00:00:00Z", f"ordinary{i}")
        self.dated_event("zzz-oldest", "2026-08-01T00:00:00Z", "oldest")
        self.dated_event("zzz-context", "2026-09-20T00:00:00Z", "correction")
        self.dated_event("zzz-correction", "2026-09-21T00:00:00Z", "correction", "I asked you not to do that again")
        self.dated_event("zzz-failed1", "2026-09-22T00:00:00Z", "failure", "Build failed", "task_outcome")
        self.dated_event("zzz-failed2", "2026-09-23T00:00:00Z", "failure", "Build failed again", "task_outcome")
        with patch.object(p, "MAX_EVENTS", 8):
            self.prepare()
        manifest = p.active(self.state)
        ids = manifest["event_ids"]
        self.assertEqual(len(ids), 8)
        for key in ("zzz-oldest", "zzz-correction", "zzz-context", "zzz-failed1", "zzz-failed2"):
            self.assertIn(key, ids)
        self.assertEqual(ids.index("zzz-context") + 1, ids.index("zzz-correction"))
        self.assertFalse(next(g for g in manifest["selection"]["task_groups"] if g["task_id"] == "correction")["partial"])

    def test_priority_tasks_get_round_robin_turns_without_mutating_evidence(self):
        (self.state / "events" / f"{'a' * 64}.json").unlink()
        for i in range(30):
            self.dated_event(f"dominant{i:02d}", "2026-09-01T00:00:00Z", "dominant",
                             "prefix " * 100 + " You should not do this again " + " suffix" * 100)
        self.dated_event("later-correction", "2026-09-20T00:00:00Z", "second", "Do not repeat this again")
        events = list(p.eligible(self.state, {}))
        original = json.dumps(events, sort_keys=True)
        before = p.backlog_metrics(events)
        with patch.object(p, "MAX_EVENTS", 24):
            selected, _ = p.select_events(events)
        self.assertEqual(len(selected), 24)
        self.assertIn("later-correction", [event["id"] for event in selected])
        self.assertEqual(json.dumps(events, sort_keys=True), original)
        self.assertEqual(p.backlog_metrics(events)["high_signal_pending_events"], before["high_signal_pending_events"])
        self.assertTrue(any(event["text_truncated"] for event in selected))

    def test_status_distinguishes_backlogs_slos_and_legacy_proposal_age(self):
        self.dated_event("correction", "2026-09-10T00:00:00Z", "correction", "Do not do this again")
        self.dated_event("unknown", "invalid", "unknown")
        self.prepare()
        output = self.finish(self.result())
        candidate_id = output["candidate_ids"][0]
        data = p.ledger(self.state)
        data["candidates"][candidate_id].pop("created_at")
        p.atomic_json(self.state / "pipeline-state.json", data)
        path = self.state / "candidates" / candidate_id / "candidate.json"
        candidate = p.read_json(path)
        candidate["created_at"] = "2026-09-01T00:00:00Z"
        p.atomic_json(path, candidate)
        self.dated_event("new-correction", "2026-09-10T00:00:00Z", "new", "Stop doing that again")
        self.dated_event("new-unknown", "invalid", "unknown")
        p.atomic_json(self.state / "observation.json", {
            "timestamp": "2026-09-27T00:00:00Z", "counts": {"pending": 17},
            "scheduler": {"status": "attention", "findings": [{"check": "active_without_enabled_timer", "id": "job"}],
                          "jobs": [{"id": "job", "declared_status": "ACTIVE", "timer": {"active": "inactive"},
                                    "last_success_at": "2026-09-01T00:00:00Z", "prompt": "private task content"}],
                          "prompt": "private task content"}})
        captured = io.StringIO()
        with patch.object(p, "now", return_value="2026-09-28T00:00:00Z"), patch.object(p.subprocess, "run", side_effect=AssertionError("status must not invoke systemctl")), contextlib.redirect_stdout(captured):
            self.assertEqual(p.main(["--state-dir", str(self.state), "status"]), 0)
        status = json.loads(captured.getvalue())
        self.assertEqual(status["review_event_backlog"]["pending_events"], 2)
        self.assertEqual(status["collector_thread_backlog"]["pending_threads"], 17)
        self.assertTrue(status["scheduler"]["cached"])
        self.assertEqual(status["scheduler"]["observed_at"], "2026-09-27T00:00:00Z")
        self.assertEqual(status["scheduler"]["status"], "attention")
        self.assertEqual(status["scheduler"]["findings"][0]["check"], "active_without_enabled_timer")
        self.assertEqual(status["scheduler"]["jobs"][0]["last_success_at"], "2026-09-01T00:00:00Z")
        self.assertNotIn("private task content", captured.getvalue())
        self.assertEqual(status["oldest_pending_age_days"], 18)
        self.assertEqual(status["unknown_timestamp_events"], 1)
        self.assertEqual(status["high_signal_over_7_days"], 1)
        self.assertEqual(status["events_over_14_days"], 1)
        self.assertEqual(status["proposal_progress"]["overdue_candidates"][0]["candidate_id"], candidate_id)
        self.assertEqual(status["completed_review_outcomes"], {"reviewed": 1})

    def test_applied_candidate_can_be_checked_without_false_baseline_failure(self):
        self.prepare()
        output = self.finish(self.result())
        self.args.candidate_id = output["candidate_ids"][0]
        (self.root / self.target).write_text(self.original.replace("Always read every reference.", "Read references only when relevant."))
        self.args.status = "applied"
        p.decision(self.args)
        verified = p.check(self.args)
        self.assertEqual(verified["status"], "applied_state_verified")
        self.assertIn("not performed", verified["behavioral_validation"])
        p.decision(self.args)  # verification preserves applied decision compatibility
        (self.root / self.target).write_text(self.original)
        self.assertEqual(p.check(self.args)["status"], "failed")

    def test_batch_stable_and_ack_only_snapshot(self):
        first = self.prepare()
        self.event("b" * 64)
        self.assertEqual(first["batch_id"], self.prepare()["batch_id"])
        self.finish(self.result(False))
        self.assertEqual(set(p.ledger(self.state)["reviewed"]), {"a" * 64})
        second = self.prepare()
        self.assertNotEqual(first["batch_id"], second["batch_id"])
        self.assertEqual(p.active(self.state)["event_ids"], ["b" * 64])

    def test_wrong_batch_and_unknown_evidence_do_not_ack(self):
        self.prepare()
        result = self.result()
        result["batch_id"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "batch_id"):
            self.finish(result)
        result = self.result()
        result["candidates"][0]["evidence_event_ids"] = ["outside"]
        with self.assertRaisesRegex(ValueError, "outside"):
            self.finish(result)
        self.assertEqual(p.ledger(self.state)["reviewed"], {})

    def test_finish_checks_patch_without_live_changes(self):
        self.prepare()
        output = self.finish(self.result())
        candidate_id = output["candidate_ids"][0]
        self.assertEqual(output["validation"][candidate_id], "syntax_validated_needs_behavior_review")
        artifact = p.read_json(self.state / "candidates" / candidate_id / "validation.json")
        self.assertEqual(artifact["behavioral_validation"], "not performed; scenario-specific evaluation needed")
        self.assertFalse(artifact["live_changes"])
        self.assertEqual((self.root / self.target).read_text(), self.original)
        self.assertTrue((self.state / "candidates" / candidate_id / "validated.patch").is_file())

    def test_failed_patch_is_explicit_reviewed_candidate(self):
        self.prepare()
        result = self.result()
        result["candidates"][0]["patch"] = result["candidates"][0]["patch"].replace("-Always read every reference.", "-Missing old line.")
        output = self.finish(result)
        self.assertEqual(set(output["validation"].values()), {"failed"})
        self.assertEqual(len(p.ledger(self.state)["reviewed"]), 1)

    def test_baseline_change_fails_check(self):
        self.prepare()
        (self.root / self.target).write_text(self.original + "New authorized edit.\n")
        output = self.finish(self.result())
        candidate_id = output["candidate_ids"][0]
        report = p.read_json(self.state / "candidates" / candidate_id / "validation.json")
        self.assertIn("baseline changed", report["error"])

    def test_malicious_command_and_extra_field_rejected(self):
        self.prepare()
        result = self.result()
        result["candidates"][0]["checks"] = ["touch /tmp/model-command"]
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            self.finish(result)
        result = self.result()
        result["command"] = "arbitrary command"
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            self.finish(result)
        self.assertFalse(p.ledger(self.state)["reviewed"])

    def test_path_and_symlink_boundaries(self):
        for target in ("../config/codex/AGENTS.md", "/etc/passwd", "config/codex/config.toml",
                       "config/codex/skills/a/scripts/fix.sh", "config/codex/plugins/cache/skills/a/SKILL.md",
                       "config/codex/skills/a/references/../../config.toml"):
            self.assertFalse(p.allowed_target(target), target)
        path = self.root / "config/codex/skills/linked"
        path.symlink_to(self.root / "config/codex/skills/example", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            p.target_path(self.root, "config/codex/skills/linked/SKILL.md")
        self.assertNotIn("config/codex/skills/linked/SKILL.md", p.inventory(self.root))

    def test_multi_file_patch_rejected_before_ack(self):
        self.prepare()
        result = self.result()
        result["candidates"][0]["patch"] += "--- a/other\n+++ b/other\n@@ -1 +1 @@\n-a\n+b\n"
        with self.assertRaisesRegex(ValueError, "extra files"):
            self.finish(result)
        self.assertFalse(p.ledger(self.state)["reviewed"])

    def test_dedup_rejected_and_applied_record(self):
        self.prepare()
        output = self.finish(self.result())
        candidate_id = output["candidate_ids"][0]
        self.args.candidate_id = candidate_id
        self.args.status = "applied"
        with self.assertRaisesRegex(ValueError, "does not match"):
            p.decision(self.args)
        # Simulates a separate authorized user edit; pipeline never applies it.
        (self.root / self.target).write_text(self.original.replace("Always read every reference.", "Read references only when relevant."))
        p.decision(self.args)
        record = p.ledger(self.state)["candidates"][candidate_id]
        self.assertEqual(record["status"], "applied")
        self.assertIn("applied_sha256", record)
        self.args.status = "rejected"
        p.decision(self.args)
        self.event("b" * 64)
        self.prepare()
        result = self.result()
        result["candidates"][0]["evidence_event_ids"] = ["b" * 64]
        output = self.finish(result)
        self.assertEqual(output["suppressed_candidate_ids"], [candidate_id])
        self.assertFalse(output["candidate_ids"])
        history = p.read_json(self.state / "history" / f"{output['batch_id']}.json")
        self.assertEqual(history["admitted_candidate_ids"], [])
        self.assertEqual(history["suppressed_candidate_ids"], [candidate_id])
        self.assertEqual(p.active(self.state)["previous_decisions"][0]["status"], "rejected")

    def test_no_change_cannot_hide_candidates(self):
        self.prepare()
        result = self.result()
        result["outcome"] = "no_change"
        with self.assertRaisesRegex(ValueError, "no candidates"):
            self.finish(result)

    def test_required_frontmatter_cannot_be_omitted(self):
        self.prepare()
        result = self.result()
        candidate = result["candidates"][0]
        candidate["checks"] = ["markdown"]
        candidate["patch"] = f"--- a/{self.target}\n+++ b/{self.target}\n@@ -1,4 +1,4 @@\n ---\n-name: example\n+name: INVALID!\n description: Example skill.\n ---\n"
        output = self.finish(result)
        candidate_id = output["candidate_ids"][0]
        report = p.read_json(self.state / "candidates" / candidate_id / "validation.json")
        self.assertEqual(report["status"], "failed")
        self.assertIn("skill name", report["error"])

    def test_cli_gate_empty_ready_and_malformed(self):
        command = ["--state-dir", str(self.state), "--source-root", str(self.root), "gate"]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(p.main(command), 0)
            self.prepare()
            self.finish(self.result(False))
            self.assertEqual(p.main(command), 1)
            (self.state / "events/bad.json").write_text("bad json")
            self.assertEqual(p.main(command), 255)

    def test_bounded_batch(self):
        for i in range(p.MAX_EVENTS + 4):
            self.event(f"event{i:04d}")
        self.prepare()
        self.assertEqual(len(p.active(self.state)["event_ids"]), p.MAX_EVENTS)

    def test_private_files_and_idempotent_finish(self):
        self.prepare()
        result = self.result(False)
        self.finish(result)
        self.assertEqual(self.finish(result)["status"], "already_reviewed")
        self.assertEqual((self.state / "pipeline-state.json").stat().st_mode & 0o777, 0o600)

    def test_concurrent_command_waits_for_state_lock(self):
        command = [sys.executable, str(Path(p.__file__)), "--state-dir", str(self.state), "gate"]
        with p.locked(self.state):
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run(command, capture_output=True, timeout=0.15)
        self.assertEqual(subprocess.run(command, capture_output=True, timeout=2).returncode, 0)

    def test_output_symlink_is_rejected(self):
        self.prepare()
        external = self.base / "external"
        external.mkdir()
        (self.state / "history").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.finish(self.result(False))
        self.assertEqual(list(external.iterdir()), [])

    def test_no_patch_remains_explicitly_unvalidated(self):
        self.prepare()
        result = self.result()
        result["candidates"][0]["patch"] = None
        output = self.finish(result)
        self.assertEqual(set(output["validation"].values()), {"failed"})
        self.assertEqual((self.root / self.target).read_text(), self.original)

    def test_metadata_preserves_only_boolean_attribution(self):
        path = self.state / "events" / f"{'a' * 64}.json"
        event = p.read_json(path)
        event["metadata"] = {"human": False, "automation": True, "command": "do something"}
        p.atomic_json(path, event)
        evidence = next(p.eligible(self.state, {}))
        self.assertEqual(evidence["metadata"], {"human": False, "automation": True})
        event["metadata"] = {"human": "true", "automation": 1}
        p.atomic_json(path, event)
        self.assertEqual(next(p.eligible(self.state, {}))["metadata"], {})

    def test_status_reports_active_batch_and_backlog(self):
        self.prepare()
        self.event("b" * 64)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = p.main(["--state-dir", str(self.state), "--source-root", str(self.root), "status"])
        self.assertEqual(code, 0)
        status = json.loads(captured.getvalue())
        self.assertEqual(status["pending_events"], 2)
        self.assertEqual(status["active_batch_selected_events"], 1)
        self.assertEqual(status["active_batch_total_pending_events"], 2)

    def test_readable_report_includes_coverage_and_candidate_links(self):
        self.prepare()
        self.event("b" * 64)
        output = self.finish(self.result())
        candidate_id = output["candidate_ids"][0]
        report = (self.state / "latest.md").read_text()
        self.assertIn("1 events screened in this batch; 1 eligible events remain pending", report)
        self.assertIn(f"candidates/{candidate_id}/validation.json", report)
        self.assertIn(self.target, report)
        self.assertEqual(output["pending_events"], 1)
        self.prepare()
        self.finish(self.result(False))
        self.assertIn("No instruction changes proposed", (self.state / "latest.md").read_text())

    def test_request_schema_compatibility_and_host_duplicate_rejection(self):
        schema_text = (p.HERE / "result.schema.json").read_text()
        self.assertNotIn("uniqueItems", schema_text)
        self.prepare()
        for field in ("checks", "evidence_event_ids"):
            result = self.result()
            candidate = result["candidates"][0]
            candidate[field] = [candidate[field][0]] * 2
            with self.assertRaisesRegex(ValueError, "duplicate items"):
                self.finish(result)
        self.assertFalse(p.ledger(self.state)["reviewed"])

    def test_pending_prepare_refreshes_request_without_changing_manifest(self):
        first = self.prepare()
        manifest_path = self.state / "review/manifest.json"
        original_manifest = manifest_path.read_bytes()
        (self.state / "review/result.schema.json").write_text('{"uniqueItems":true}')
        (self.state / "review/prompt.md").write_text("Old prompt")
        self.event("b" * 64)
        second = self.prepare()
        self.assertTrue(second["reused"])
        self.assertEqual(first["batch_id"], second["batch_id"])
        self.assertEqual(manifest_path.read_bytes(), original_manifest)
        self.assertNotIn("uniqueItems", (self.state / "review/result.schema.json").read_text())
        self.assertIn("not yet evaluated", (self.state / "review/prompt.md").read_text())
        self.assertFalse(p.ledger(self.state)["reviewed"])

    def test_long_events_use_excerpts_and_safe_full_evidence_pointers(self):
        long_text = "Beginning detail. " + "middle material " * 1000 + " Ending detail."
        for i in range(90):
            self.event(f"long{i:04d}", long_text)
        self.prepare()
        manifest = p.active(self.state)
        long_events = [event for event in manifest["events"] if event["id"].startswith("long")]
        self.assertGreater(len(long_events), 50)
        self.assertLessEqual(sum(len(json.dumps(event).encode()) for event in manifest["events"]), p.MAX_BATCH_BYTES)
        for event in long_events:
            self.assertTrue(event["text_truncated"])
            self.assertLessEqual(len(event["text"]), p.MAX_EXCERPT_CHARS)
            self.assertTrue(event["text"].startswith("Beginning detail."))
            self.assertTrue(event["text"].endswith("Ending detail."))
            full_path = Path(event["evidence_path"])
            self.assertEqual(full_path, (self.state / "events" / f"{event['id']}.json").resolve())
            self.assertEqual(p.read_json(full_path)["text"], long_text)
        self.assertFalse(manifest["events"][0]["text_truncated"])

    def test_metadata_cannot_spoof_full_evidence_pointer(self):
        path = self.state / "events" / f"{'a' * 64}.json"
        event = p.read_json(path)
        event["evidence_path"] = "/etc/shadow"
        event["metadata"] = {"evidence_path": "/etc/shadow", "human": True}
        p.atomic_json(path, event)
        self.prepare()
        selected = p.active(self.state)["events"][0]
        self.assertEqual(selected["evidence_path"], str(path.resolve()))
        self.assertEqual(selected["metadata"], {"human": True})

    def test_source_capture_truncation_survives_manifest_screening(self):
        path = self.state / "events" / f"{'a' * 64}.json"
        event = p.read_json(path)
        event.update(source_text_truncated=True, original_text_chars=25000)
        p.atomic_json(path, event)
        self.prepare()
        selected = p.active(self.state)["events"][0]
        self.assertTrue(selected["source_text_truncated"])
        self.assertEqual(selected["original_text_chars"], 25000)
        self.assertEqual(selected["source"], event["source"])
        self.assertIn("source.line", (self.state / "review/prompt.md").read_text())


if __name__ == "__main__":
    unittest.main()
