import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "manager.py"
SPEC = importlib.util.spec_from_file_location("codexdeck_manager", MODULE_PATH)
manager = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = manager
SPEC.loader.exec_module(manager)


class ManagerTest(unittest.TestCase):
    def test_transcript_framing_preserves_original_trailing_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            for text in ("hello café", "hello café\n", "first\nsecond\n\n"):
                with self.subTest(text=text):
                    path.write_text(text if text.endswith("\n") else text + "\n")
                    Path(str(path) + ".done").write_text(json.dumps({"status": "ok", "chars": len(text)}))
                    self.assertEqual(manager.read_dictation_transcript(path), text)

    def test_invalid_transcript_completion_is_not_delivered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            path.write_text("hello\n")
            for outcome in ({"status": "ok", "chars": 99}, {"status": "error", "chars": 5}, [], {"status": "ok", "chars": True}):
                with self.subTest(outcome=outcome):
                    Path(str(path) + ".done").write_text(json.dumps(outcome))
                    with self.assertRaises(ValueError):
                        manager.read_dictation_transcript(path)

    def test_parse_volume(self):
        self.assertEqual(manager.parse_volume("Volume: 0.45"), (45, False))
        self.assertEqual(manager.parse_volume("Volume: 0.07 [MUTED]"), (7, True))

    def test_project_name(self):
        self.assertEqual(manager.project_name("/home/nb/work/misc/codex"), "codex")
        self.assertEqual(manager.project_name("/"), "/")

    def test_ancestor_root_finds_owning_tmux_pane(self):
        parents = {30: 20, 20: 10, 10: 1}
        self.assertEqual(
            manager.ancestor_root(30, {10, 11}, parents.get),
            10,
        )

    def test_resolve_event_pane_from_terminal_title(self):
        thread_id = "019fefbd-482d-7490-96e3-9bf043d73dd2"
        panes = (
            manager.Pane("%7", "work", "2", False, "codex", thread_id[:29] + "..."),
        )
        self.assertEqual(
            manager.resolve_event_pane({"thread-id": thread_id, "tmux-pane": None}, panes),
            "%7",
        )

    def test_suppressed_notification_does_not_request_attention(self):
        pane = manager.Pane("%7", "work", "2", False, "codex", "thread title")
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            event = {
                "thread-id": "thread-1",
                "turn-id": "turn-1",
                "cwd": "/work/codex",
                "tmux-pane": "%7",
                "timestamp": 50,
                "notification-policy": "suppress",
            }
            (state_dir / "events.jsonl").write_text(json.dumps(event) + "\n")
            with (
                mock.patch.object(manager, "EVENTS_PATH", state_dir / "events.jsonl"),
                mock.patch.object(manager, "ACK_PATH", state_dir / "acknowledged.json"),
            ):
                self.assertEqual(manager.load_pending((pane,)), ())

    def test_order_panes_is_deterministic_by_tmux_location(self):
        panes = (
            manager.Pane("%3", "work", "3", True, "three", "three"),
            manager.Pane("%4", "work", "1", False, "one", "one"),
            manager.Pane("%5", "work", "2", False, "two", "two"),
        )
        ordered = manager.order_panes(panes)
        self.assertEqual([pane.pane_id for pane in ordered], ["%4", "%5", "%3"])

    def test_recent_app_threads_rotate_oldest_to_newest_and_exclude_children(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.sqlite"
            connection = manager.sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE threads (
                    id TEXT PRIMARY KEY, name TEXT, title TEXT, archived INTEGER,
                    preview TEXT, thread_source TEXT, recency_at_ms INTEGER,
                    cwd TEXT
                );
                CREATE TABLE thread_spawn_edges (child_thread_id TEXT);
                """
            )
            ids = [f"00000000-0000-0000-0000-{value:012d}" for value in range(1, 8)]
            for index, thread_id in enumerate(ids[:5], 1):
                connection.execute(
                    "INSERT INTO threads VALUES (?, NULL, ?, 0, 'visible', 'user', ?, ?)",
                    (thread_id, f"Task {index}", index, f"/work/project-{index}"),
                )
            connection.execute(
                "INSERT INTO threads VALUES (?, NULL, 'Tagged child', 0, 'visible', 'subagent', 99, '/work/child')",
                (ids[5],),
            )
            connection.execute(
                "INSERT INTO threads VALUES (?, NULL, 'Edge child', 0, 'visible', 'user', 98, '/work/child')",
                (ids[6],),
            )
            connection.execute("INSERT INTO thread_spawn_edges VALUES (?)", (ids[6],))
            connection.commit()
            connection.close()
            with mock.patch.object(manager, "CODEX_STATE_DB", database):
                threads = manager.recent_app_threads()
        self.assertEqual([thread.title for thread in threads], ["Task 2", "Task 3", "Task 4", "Task 5"])
        self.assertEqual(
            [thread.project for thread in threads],
            ["project-2", "project-3", "project-4", "project-5"],
        )

    def test_open_app_thread_uses_exact_uuid_deep_link(self):
        thread = manager.AppThread(
            "00000000-0000-0000-0000-000000000123", "Exact task"
        )
        with (
            mock.patch.object(manager, "_run", return_value="") as run,
            mock.patch.object(manager, "focus_app_thread", return_value=True),
        ):
            self.assertTrue(manager.open_app_thread(thread))
        run.assert_called_once_with(
            ["xdg-open", "codex://threads/00000000-0000-0000-0000-000000000123"],
            timeout=5,
            check=True,
        )

    def test_send_return_targets_exact_hyprland_window(self):
        with mock.patch.object(manager, "_run") as run:
            manager.send_return_to_window("0xabc")
        run.assert_called_once_with(
            [
                "hyprctl",
                "eval",
                "return hl.dispatch(hl.dsp.send_shortcut({ "
                'mods = "", key = "Return", window = "address:0xabc" }))',
            ],
            timeout=3,
            check=True,
        )

    def test_send_return_rejects_invalid_window_address(self):
        with (
            mock.patch.object(manager, "_run") as run,
            self.assertRaises(ValueError),
        ):
            manager.send_return_to_window('0xabc" })) os.execute("false") --')
        run.assert_not_called()

    def test_dictation_toggles_owned_key_and_submits_after_release(self):
        process = mock.Mock()
        process.poll.return_value = None
        state = manager.DeckStateManager()
        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(manager.subprocess, "Popen", return_value=process) as popen,
            mock.patch.object(
                manager,
                "focused_app_activity_since",
                return_value=manager.AppActivity(
                    "00000000-0000-0000-0000-000000000123", 7
                ),
            ),
            mock.patch.object(manager, "desktop_log_marker", return_value=()),
            mock.patch.object(manager, "active_codex_window_address", return_value="0xabc"),
            mock.patch.object(manager.time, "sleep"),
        ):
            state._toggle_dictation()
        self.assertEqual(state._dictation_state, "recording")
        self.assertIs(state._dictation_process, process)
        self.assertIn("-P", popen.call_args.args[0])

        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(manager, "send_return_to_window") as send_return,
            mock.patch.object(
                manager, "desktop_log_marker", return_value=((Path("log"), 1),)
            ),
            mock.patch.object(manager, "turn_started_since", return_value=True),
            mock.patch.object(manager, "app_thread_context_matches", return_value=True),
            mock.patch.object(manager.time, "sleep"),
        ):
            state._toggle_dictation()
        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=3)
        send_return.assert_called_once_with("0xabc")
        self.assertEqual(state._dictation_state, "idle")

    def test_dictation_stop_releases_key_when_focus_cannot_be_restored(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state._dictation_thread_id = "00000000-0000-0000-0000-000000000123"
        state._dictation_window_address = "0xabc"
        state._dictation_renderer_window_id = 7
        with (
            mock.patch.object(manager, "focus_codex_app", return_value=False),
            mock.patch.object(manager, "open_app_thread", return_value=False),
            mock.patch.object(manager, "desktop_log_marker", return_value=None),
        ):
            state._toggle_dictation()
        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=3)
        self.assertIsNone(state._dictation_process)
        self.assertEqual(state._dictation_state, "idle")

    def test_manager_stop_releases_an_active_dictation_key(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state.stop()
        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=3)
        self.assertIsNone(state._dictation_process)
        self.assertEqual(state._dictation_state, "idle")

    def test_dictation_press_is_ignored_while_transcribing(self):
        state = manager.DeckStateManager()
        state._dictation_state = "transcribing"
        with mock.patch.object(manager.subprocess, "Popen") as popen:
            state._toggle_dictation()
        popen.assert_not_called()
        self.assertEqual(state._dictation_state, "transcribing")

    def test_dictation_press_does_not_queue_during_submission(self):
        state = manager.DeckStateManager()
        state._dictation_state = "transcribing"
        state._app_interaction_lock.acquire()
        try:
            with mock.patch.object(state, "_toggle_dictation") as toggle:
                state._handle("app_dictation", 0)
        finally:
            state._app_interaction_lock.release()
        toggle.assert_not_called()

    def test_dictation_submit_restores_original_task_after_focus_changes(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state._dictation_thread_id = "00000000-0000-0000-0000-000000000123"
        state._dictation_window_address = "0xabc"
        state._dictation_renderer_window_id = 7
        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(
                manager, "desktop_log_marker", return_value=((Path("log"), 1),)
            ),
            mock.patch.object(
                manager, "app_thread_context_matches", side_effect=[False, True, True]
            ),
            mock.patch.object(manager, "open_app_thread", return_value=True) as reopen,
            mock.patch.object(manager, "turn_started_since", return_value=True),
            mock.patch.object(manager, "send_return_to_window") as send_return,
            mock.patch.object(manager.time, "sleep"),
        ):
            state._toggle_dictation()
        reopen.assert_called_once_with(
            manager.AppThread(
                "00000000-0000-0000-0000-000000000123", "Dictation target"
            )
        )
        send_return.assert_called_once_with("0xabc")
        self.assertEqual(state._dictation_state, "idle")

    def test_dictation_submit_does_not_abort_during_send_context_change(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state._dictation_thread_id = "00000000-0000-0000-0000-000000000123"
        state._dictation_window_address = "0xabc"
        state._dictation_renderer_window_id = 7
        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(manager, "app_thread_context_matches", return_value=True) as context,
            mock.patch.object(
                manager, "desktop_log_marker", return_value=((Path("log"), 1),)
            ),
            mock.patch.object(
                manager, "turn_started_since", side_effect=[False, False, True]
            ),
            mock.patch.object(manager, "send_return_to_window") as send_return,
            mock.patch.object(manager.time, "sleep"),
        ):
            state._toggle_dictation()
        self.assertEqual(context.call_count, 3)
        context.assert_called_with(
            "00000000-0000-0000-0000-000000000123", "0xabc", 7
        )
        send_return.assert_called_once_with("0xabc")
        self.assertEqual(state._dictation_state, "idle")

    def test_dictation_submit_is_not_repeated_without_confirmation(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state._dictation_thread_id = "00000000-0000-0000-0000-000000000123"
        state._dictation_window_address = "0xabc"
        state._dictation_renderer_window_id = 7
        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(manager, "app_thread_context_matches", return_value=True),
            mock.patch.object(
                manager, "desktop_log_marker", return_value=((Path("log"), 1),)
            ),
            mock.patch.object(manager, "turn_started_since", return_value=False),
            mock.patch.object(manager, "send_return_to_window") as send_return,
            mock.patch.object(manager.time, "sleep"),
        ):
            state._toggle_dictation()
        send_return.assert_called_once_with("0xabc")
        self.assertEqual(state._dictation_state, "idle")

    def test_app_thread_navigation_waits_for_dictation_interaction(self):
        state = manager.DeckStateManager()
        thread = manager.AppThread(
            "00000000-0000-0000-0000-000000000123", "Another task"
        )
        with mock.patch.object(manager, "open_app_thread", return_value=True) as open_thread:
            state._app_interaction_lock.acquire()
            worker = state.handle_app_thread(thread)
            self.assertTrue(worker.is_alive())
            open_thread.assert_not_called()
            state._app_interaction_lock.release()
            worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
        open_thread.assert_called_once_with(thread)

    def test_manager_stop_cancels_transcribing_before_any_submit(self):
        process = mock.Mock()
        state = manager.DeckStateManager()
        state._dictation_process = process
        state._dictation_state = "recording"
        state._dictation_thread_id = "00000000-0000-0000-0000-000000000123"
        state._dictation_window_address = "0xabc"
        state._dictation_renderer_window_id = 7

        def stop_manager(_delay):
            state.stop()

        with (
            mock.patch.object(manager, "focus_codex_app", return_value=True),
            mock.patch.object(manager, "app_thread_context_matches", return_value=True),
            mock.patch.object(
                manager, "desktop_log_marker", return_value=((Path("log"), 1),)
            ),
            mock.patch.object(manager, "_run") as run,
            mock.patch.object(manager.time, "sleep", side_effect=stop_manager),
        ):
            state._toggle_dictation()
        run.assert_not_called()
        self.assertEqual(state._dictation_state, "idle")

    def test_turn_started_since_matches_exact_active_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "desktop.log"
            path.write_text("old\n")
            marker = ((path, path.stat().st_size),)
            path.write_text(
                "old\n"
                "response_routed conversationId=00000000-0000-0000-0000-000000000123 "
                "method=turn/start originWebcontentsId=1\n"
            )
            self.assertTrue(
                manager.turn_started_since(
                    marker, "00000000-0000-0000-0000-000000000123"
                )
            )
            self.assertFalse(
                manager.turn_started_since(
                    marker, "00000000-0000-0000-0000-000000000999"
                )
            )

    def test_log_correlation_ignores_newer_unrelated_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui_log = root / "codex-desktop-ui.log"
            watcher_log = root / "codex-desktop-watcher.log"
            thread_id = "00000000-0000-0000-0000-000000000123"
            ui_log.write_text(
                "2026-08-14T16:00:00.000Z info "
                f"thread_stream_view_activity_changed active=true conversationId={thread_id} "
                "rendererWindowFocused=true rendererWindowId=1\n"
            )
            watcher_log.write_text("2026-08-14T16:00:01.000Z git watcher update\n")
            os.utime(watcher_log, (2_000_000_000, 2_000_000_000))
            with mock.patch.object(manager, "CODEX_DESKTOP_LOG_ROOT", root):
                self.assertEqual(manager.current_app_thread_id(), thread_id)
                marker = manager.desktop_log_marker()
                with ui_log.open("a") as destination:
                    destination.write(
                        "2026-08-14T16:00:02.000Z info response_routed "
                        f"conversationId={thread_id} method=turn/start "
                        "originWebcontentsId=7\n"
                    )
                self.assertTrue(manager.turn_started_since(marker, thread_id))

    def test_focus_app_thread_correlates_the_routed_task_to_its_window(self):
        thread_id = "00000000-0000-0000-0000-000000000123"
        with (
            mock.patch.object(
                manager,
                "codex_app_window_addresses",
                return_value=("0xsecondary", "0xprimary"),
            ),
            mock.patch.object(manager, "focus_codex_app", return_value=True) as focus,
            mock.patch.object(
                manager,
                "focused_app_activity_since",
                side_effect=[
                    manager.AppActivity("00000000-0000-0000-0000-000000000999", 2),
                    manager.AppActivity(thread_id, 1),
                ],
            ),
            mock.patch.object(manager, "desktop_log_marker", return_value=()),
        ):
            self.assertTrue(manager.focus_app_thread(thread_id, attempts=1))
        self.assertEqual(
            [call.kwargs["window_address"] for call in focus.call_args_list],
            ["0xsecondary", "0xprimary"],
        )

    def test_focus_app_thread_accepts_an_already_active_single_window(self):
        thread_id = "00000000-0000-0000-0000-000000000123"
        with (
            mock.patch.object(
                manager, "codex_app_window_addresses", return_value=("0xprimary",)
            ),
            mock.patch.object(
                manager, "active_codex_window_address", return_value="0xprimary"
            ),
            mock.patch.object(
                manager,
                "latest_app_activity",
                return_value=manager.AppActivity(thread_id, 1),
            ),
            mock.patch.object(manager, "focus_codex_app") as focus,
        ):
            self.assertTrue(manager.focus_app_thread(thread_id, attempts=1))
        focus.assert_not_called()

    def test_focused_activity_waits_for_a_post_focus_event(self):
        wrong_activity = manager.AppActivity(
            "00000000-0000-0000-0000-000000000999", 8
        )
        correct_activity = manager.AppActivity(
            "00000000-0000-0000-0000-000000000123", 7
        )
        with (
            mock.patch.object(
                manager,
                "latest_app_activity",
                side_effect=[wrong_activity, correct_activity, correct_activity],
            ),
            mock.patch.object(
                manager, "active_codex_window_address", return_value="0xabc"
            ),
            mock.patch.object(manager.time, "sleep") as sleep,
        ):
            self.assertEqual(
                manager.focused_app_activity_since((), "0xabc", attempts=3),
                correct_activity,
            )
        self.assertEqual(sleep.call_count, 2)

    def test_focus_codex_app_validates_the_active_window(self):
        with mock.patch.object(
            manager,
            "_run",
            side_effect=[
                '[{"class":"Chatgpt","mapped":true,"title":"ChatGPT",'
                '"focusHistoryID":0,"address":"0xabc","workspace":{"id":1}}]',
                '{"id":1}',
                "",
                '{"class":"Chatgpt","address":"0xabc"}',
            ],
        ) as run:
            self.assertTrue(manager.focus_codex_app(attempts=1))
        self.assertEqual(run.call_count, 4)

    def test_busy_to_idle_transition_requests_attention(self):
        panes = (
            manager.Pane("%3", "work", "1", False, "one", "one", busy=False),
            manager.Pane("%4", "work", "2", False, "two", "two", busy=True),
        )
        transitioned = manager.attention_transitions({"%3": True, "%4": True}, panes)
        self.assertEqual([pane.pane_id for pane in transitioned], ["%3"])

    def test_attention_event_persists_until_acknowledged(self):
        pane = manager.Pane("%3", "work", "1", False, "one", "one")
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            with (
                mock.patch.object(manager, "STATE_DIR", state_dir),
                mock.patch.object(manager, "EVENTS_PATH", state_dir / "events.jsonl"),
                mock.patch.object(manager, "ACK_PATH", state_dir / "acknowledged.json"),
            ):
                manager.record_attention(pane, timestamp=50)
                pending = manager.load_pending((pane,))
                self.assertEqual(len(pending), 1)
                manager.acknowledge(pane.pane_id, pending[0].turn_id)
                self.assertEqual(manager.load_pending((pane,)), ())

    def test_pane_press_acknowledges_its_pending_completion(self):
        state = manager.DeckStateManager()
        pane = manager.Pane("%7", "work", "2", False, "codex", "thread title")
        pending = manager.Pending("%7", "turn-1", "codex", 50)
        state.snapshot = manager.Snapshot(pending=(pending,), panes=(pane,))
        with (
            mock.patch.object(manager, "switch_to_pane", return_value=True),
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            state._handle("pane", 0)
        acknowledge.assert_called_once_with("%7", "turn-1")

    def test_focused_codex_pane_acknowledges_pending_completion(self):
        pane = manager.Pane("%7", "work", "2", True, "codex", "thread title")
        pending = manager.Pending("%7", "turn-1", "codex", 50)
        with (
            mock.patch.object(
                manager, "_run", return_value="attached,focused,UTF-8\t%7"
            ),
            mock.patch.object(manager, "list_codex_panes", return_value=(pane,)),
            mock.patch.object(manager, "load_pending", return_value=(pending,)),
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            self.assertTrue(manager.acknowledge_focused_pane("/dev/pts/8", "%7"))
        acknowledge.assert_called_once_with("%7", "turn-1")

    def test_pane_focus_hook_resolves_focused_client_without_client_context(self):
        pane = manager.Pane("%7", "work", "2", True, "codex", "thread title")
        pending = manager.Pending("%7", "turn-1", "codex", 50)
        with (
            mock.patch.object(
                manager,
                "_run",
                return_value="attached,focused,UTF-8\t%7\nattached,UTF-8\t%8",
            ) as run,
            mock.patch.object(manager, "list_codex_panes", return_value=(pane,)),
            mock.patch.object(manager, "load_pending", return_value=(pending,)),
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            self.assertTrue(manager.acknowledge_focused_pane("", "%7"))
        run.assert_called_once_with(
            ["tmux", "list-clients", "-F", "#{client_flags}\t#{pane_id}"],
            check=True,
        )
        acknowledge.assert_called_once_with("%7", "turn-1")

    def test_unfocused_tmux_client_does_not_acknowledge(self):
        with (
            mock.patch.object(manager, "_run", return_value="attached,UTF-8\t%7"),
            mock.patch.object(manager, "list_codex_panes") as list_codex_panes,
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            self.assertFalse(manager.acknowledge_focused_pane("/dev/pts/8", "%7"))
        list_codex_panes.assert_not_called()
        acknowledge.assert_not_called()

    def test_focused_non_codex_pane_does_not_acknowledge(self):
        codex_pane = manager.Pane("%7", "work", "2", False, "codex", "thread title")
        with (
            mock.patch.object(
                manager, "_run", return_value="attached,focused,UTF-8\t%8"
            ),
            mock.patch.object(manager, "list_codex_panes", return_value=(codex_pane,)),
            mock.patch.object(manager, "load_pending") as load_pending,
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            self.assertFalse(manager.acknowledge_focused_pane("/dev/pts/8", "%8"))
        load_pending.assert_not_called()
        acknowledge.assert_not_called()

    def test_stale_focus_hook_does_not_acknowledge_new_selected_pane(self):
        with (
            mock.patch.object(
                manager, "_run", return_value="attached,focused,UTF-8\t%8"
            ),
            mock.patch.object(manager, "list_codex_panes") as list_codex_panes,
            mock.patch.object(manager, "acknowledge") as acknowledge,
        ):
            self.assertFalse(manager.acknowledge_focused_pane("/dev/pts/8", "%7"))
        list_codex_panes.assert_not_called()
        acknowledge.assert_not_called()

    def test_concurrent_acknowledgements_preserve_each_pane(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            with (
                mock.patch.object(manager, "STATE_DIR", state_dir),
                mock.patch.object(manager, "ACK_PATH", state_dir / "acknowledged.json"),
            ):
                barrier = threading.Barrier(8)

                def acknowledge(index):
                    barrier.wait()
                    manager.acknowledge(f"%{index}", f"turn-{index}")

                threads = [threading.Thread(target=acknowledge, args=(index,)) for index in range(8)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

                self.assertEqual(
                    json.loads((state_dir / "acknowledged.json").read_text()),
                    {f"%{index}": f"turn-{index}" for index in range(8)},
                )

    def test_switch_to_exact_pane_and_focus_ghostty(self):
        pane = manager.Pane("%7", "work", "2", False, "codex", "thread title")
        with mock.patch.object(
            manager, "_run", side_effect=["", "", "/dev/pts/8\t123", "", ""]
        ) as run:
            self.assertTrue(manager.switch_to_pane(pane))
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(["tmux", "select-window", "-t", "work:2"], check=True),
                mock.call(["tmux", "select-pane", "-t", "%7"], check=True),
                mock.call(["tmux", "list-clients", "-F", "#{client_tty}\t#{client_activity}"]),
                mock.call(["tmux", "switch-client", "-c", "/dev/pts/8", "-t", "work"], check=True),
                mock.call(
                    [
                        "hyprctl",
                        "eval",
                        'return hl.dispatch(hl.dsp.focus({window = "class:^(com.mitchellh.ghostty)$"}))',
                    ],
                    timeout=3,
                    check=True,
                ),
            ],
        )

    def test_audio_actions_use_pipewire_default_devices(self):
        state = manager.DeckStateManager()
        with mock.patch.object(manager, "_run", return_value="") as run:
            state._handle("volume_down", 0)
            state._handle("volume_up", 0)
            state._handle("output_mute", 0)
            state._handle("mic_mute", 0)
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"]),
                mock.call(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"]),
                mock.call(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]),
                mock.call(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"]),
            ],
        )

    def test_bottom_row_actions_use_existing_desktop_tools(self):
        state = manager.DeckStateManager()
        with (
            mock.patch.object(manager, "control_media") as control_media,
            mock.patch.object(
                manager, "send_enter_to_focused_input"
            ) as send_enter,
            mock.patch.object(manager, "start_new_codex") as start_new_codex,
            mock.patch.object(state, "_toggle_global_dictation") as toggle_dictation,
        ):
            state._handle("global_dictation", 0)
            state._handle("send_enter", 0)
            state._handle("new_codex", 0)
            state._handle("media_play_pause", 0)
        control_media.assert_called_once_with("play-pause")
        toggle_dictation.assert_called_once_with()
        send_enter.assert_called_once_with()
        start_new_codex.assert_called_once_with()

    def test_local_codex_projects_come_from_private_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alpha = root / "alpha"
            beta = root / "beta"
            alpha.mkdir()
            beta.mkdir()
            config = root / "projects.local.toml"
            config.write_text(
                f'[projects."{beta}"]\ntrust_level = "trusted"\n'
                f'[projects."{alpha}"]\ntrust_level = "trusted"\n'
                f'[projects."{root / "missing"}"]\ntrust_level = "trusted"\n'
            )
            with mock.patch.object(manager, "CODEX_PROJECTS_LOCAL", config):
                self.assertEqual(manager.local_codex_projects(), (alpha, beta))

    def test_start_new_codex_uses_selected_project_as_an_argument(self):
        project = Path("/work/project with spaces")
        with (
            mock.patch.object(manager, "local_codex_projects", return_value=(project,)),
            mock.patch.object(manager, "choose_codex_project", return_value=project),
            mock.patch.object(
                manager, "active_tmux_client", return_value=("/dev/pts/8", "main")
            ),
            mock.patch.object(
                manager,
                "_run",
                side_effect=["main\t3\t%9", "", "", "", "", "", ""],
            ) as run,
        ):
            self.assertTrue(manager.start_new_codex())
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(
                    [
                        "tmux",
                        "new-window",
                        "-d",
                        "-P",
                        "-F",
                        "#{session_name}\t#{window_index}\t#{pane_id}",
                        "-t",
                        "main:",
                        "-c",
                        "/work/project with spaces",
                        "/usr/bin/zsh",
                    ],
                    timeout=10,
                    check=True,
                ),
                mock.call(["tmux", "send-keys", "-t", "%9", "-l", "codex"], check=True),
                mock.call(["tmux", "send-keys", "-t", "%9", "Enter"], check=True),
                mock.call(["tmux", "select-window", "-t", "main:3"], check=True),
                mock.call(["tmux", "select-pane", "-t", "%9"], check=True),
                mock.call(
                    ["tmux", "switch-client", "-c", "/dev/pts/8", "-t", "main"],
                    check=True,
                ),
                mock.call(
                    [
                        "hyprctl",
                        "eval",
                        'return hl.dispatch(hl.dsp.focus({window = "class:^(com.mitchellh.ghostty)$"}))',
                    ],
                    timeout=3,
                    check=True,
                ),
            ],
        )

    def test_start_new_codex_reports_invalid_tmux_target(self):
        project = Path("/work/project")
        with (
            mock.patch.object(manager, "local_codex_projects", return_value=(project,)),
            mock.patch.object(manager, "choose_codex_project", return_value=project),
            mock.patch.object(
                manager, "active_tmux_client", return_value=("/dev/pts/8", "main")
            ),
            mock.patch.object(manager, "_run", return_value="not a pane"),
            mock.patch.object(manager, "_notify") as notify,
        ):
            self.assertFalse(manager.start_new_codex())
        notify.assert_called_once_with(
            "Could not start Codex",
            "tmux returned an unexpected window target.",
        )

    def test_active_tmux_client_uses_most_recent_activity(self):
        with mock.patch.object(
            manager,
            "_run",
            return_value="/dev/pts/1\t10\told\n/dev/pts/8\t20\tmain",
        ):
            self.assertEqual(manager.active_tmux_client(), ("/dev/pts/8", "main"))

    def test_global_dictation_starts_with_owned_file_output(self):
        with tempfile.TemporaryDirectory() as directory:
            voxtype = Path(directory) / "voxtype"
            voxtype.touch()
            transcript = Path(directory) / "transcript.txt"
            with (
                mock.patch.object(manager, "VOXTYPE", voxtype),
                mock.patch.object(manager, "ensure_voxtype_service", return_value=True),
                mock.patch.object(manager, "_run", return_value="") as run,
            ):
                self.assertTrue(manager.start_global_dictation(transcript))
        run.assert_called_once_with(
            [
                str(voxtype),
                "record",
                "start",
                f"--file={transcript}",
                "--no-auto-submit",
                "--no-smart-auto-submit",
            ],
            timeout=10,
            check=True,
        )

    def test_global_dictation_service_is_reused_when_active(self):
        with tempfile.TemporaryDirectory() as directory:
            voxtype = Path(directory) / "voxtype"
            voxtype.touch()
            with (
                mock.patch.object(manager, "voxtype_ready", return_value=True),
                mock.patch.object(manager, "VOXTYPE", voxtype),
                mock.patch.object(manager, "_run", side_effect=["active", ""]) as run,
            ):
                self.assertTrue(manager.ensure_voxtype_service())
        run.assert_called_once_with(
            ["systemctl", "--user", "is-active", "voxtype.service"]
        )

    def test_global_dictation_starts_voxtype_service_when_inactive(self):
        with tempfile.TemporaryDirectory() as directory:
            voxtype = Path(directory) / "voxtype"
            voxtype.touch()
            with (
                mock.patch.object(manager, "voxtype_ready", return_value=True),
                mock.patch.object(manager, "VOXTYPE", voxtype),
                mock.patch.object(
                    manager, "_run", side_effect=["inactive", ""]
                ) as mocked_run,
            ):
                self.assertTrue(manager.ensure_voxtype_service())
        self.assertEqual(
            mocked_run.call_args_list,
            [
                mock.call(
                    ["systemctl", "--user", "is-active", "voxtype.service"]
                ),
                mock.call(
                    ["systemctl", "--user", "start", "voxtype.service"],
                    timeout=10,
                    check=True,
                ),
            ],
        )

    def test_global_dictation_waits_for_daemon_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "voxtype"
            binary.touch()
            with (
                mock.patch.object(manager, "VOXTYPE", binary),
                mock.patch.object(manager, "_run", side_effect=["inactive", ""]),
                mock.patch.object(manager, "voxtype_ready", side_effect=[False, False, True]),
                mock.patch.object(manager.time, "sleep") as sleep,
            ):
                self.assertTrue(manager.ensure_voxtype_service())
                self.assertEqual(sleep.call_count, 2)

    def test_global_dictation_readiness_timeout_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "voxtype"
            binary.touch()
            with (
                mock.patch.object(manager, "VOXTYPE", binary),
                mock.patch.object(manager, "_run", return_value="active"),
                mock.patch.object(manager, "voxtype_ready", return_value=False),
                mock.patch.object(manager.time, "monotonic", side_effect=[0, 11]),
                mock.patch.object(manager, "_notify") as notify,
            ):
                self.assertFalse(manager.ensure_voxtype_service())
                notify.assert_called_once()

    def test_voxtype_readiness_requires_live_lock_and_valid_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            lock = Path(directory) / "voxtype.lock"
            with mock.patch.object(manager, "VOXTYPE_STATE_PATH", state):
                self.assertFalse(manager.voxtype_ready())
                state.write_text("idle")
                for invalid in ("", "bad", "0", "-1", "1"):
                    lock.write_text(invalid)
                    with mock.patch.object(manager.os, "kill") as kill:
                        self.assertFalse(manager.voxtype_ready())
                        kill.assert_not_called()
                lock.write_text(str(os.getpid()))
                self.assertTrue(manager.voxtype_ready())
                state.write_text("stopped")
                self.assertFalse(manager.voxtype_ready())
                state.write_text("idle")
                with mock.patch.object(manager.os, "kill", side_effect=ProcessLookupError):
                    self.assertFalse(manager.voxtype_ready())

    def test_global_dictation_reports_missing_local_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "voxtype"
            with (
                mock.patch.object(manager, "VOXTYPE", missing),
                mock.patch.object(manager, "_run") as run,
                mock.patch.object(manager, "_notify") as notify,
            ):
                self.assertFalse(manager.ensure_voxtype_service())
        run.assert_not_called()
        notify.assert_called_once_with(
            "Dictation is not installed",
            "Expected the local Voxtype binary at ~/.local/bin/voxtype.",
        )

    def test_capture_ghostty_input_includes_exact_focused_tmux_pane(self):
        window = {
            "address": "0xabc",
            "class": manager.GHOSTTY_CLASS,
            "pid": 123,
            "acceptsInput": True,
        }
        tmux = "/dev/pts/8\t789\tattached,focused,UTF-8\tmain\t3\t%9\t456\tcodex"
        with (
            mock.patch.object(manager, "_run", side_effect=[json.dumps(window), tmux]),
            mock.patch.object(manager, "ancestor_root", return_value=123) as ancestor,
            mock.patch.object(
                manager, "foreground_process_identity", return_value=(900, 12345)
            ),
        ):
            target = manager.active_input_target()
        ancestor.assert_called_once_with(789, {123})
        self.assertEqual(
            target,
            manager.InputTarget(
                "0xabc",
                manager.GHOSTTY_CLASS,
                123,
                manager.TmuxInputTarget(
                    "/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345
                ),
            ),
        )

    def test_capture_rejects_non_tmux_destinations(self):
        window = {
            "address": "0xabc",
            "class": "google-chrome",
            "pid": 123,
            "acceptsInput": True,
        }
        with (
            mock.patch.object(manager, "_run", return_value=json.dumps(window)),
            mock.patch.object(manager, "_notify") as notify,
        ):
            self.assertIsNone(manager.active_input_target())
        notify.assert_called_once_with(
            "Could not start dictation",
            "The currently focused input could not be identified safely.",
        )

    def test_foreground_process_identity_uses_pid_and_kernel_start_time(self):
        with mock.patch.object(
            manager,
            "process_stat",
            side_effect=[(900, 111), (900, 12345)],
        ) as process_stat:
            self.assertEqual(manager.foreground_process_identity(456), (900, 12345))
        self.assertEqual(
            process_stat.call_args_list,
            [mock.call(456), mock.call(900)],
        )

    def test_tmux_target_rejects_restarted_foreground_process(self):
        target = manager.TmuxInputTarget(
            "/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345
        )
        with (
            mock.patch.object(
                manager,
                "_run",
                side_effect=[
                    "main\t3\t%9\t456\tcodex",
                    "/dev/pts/8\tmain",
                ],
            ),
            mock.patch.object(
                manager, "foreground_process_identity", return_value=(901, 23456)
            ),
        ):
            self.assertFalse(manager.tmux_target_exists(target))

    def test_tmux_delivery_uses_stdin_and_exact_original_pane(self):
        target = manager.TmuxInputTarget(
            "/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345
        )
        with (
            mock.patch.object(manager, "tmux_target_exists", return_value=True) as exists,
            mock.patch.object(manager.uuid, "uuid4") as uuid4,
            mock.patch.object(manager.subprocess, "run") as run,
            mock.patch.object(manager, "_run", return_value="codex-deck-pasted") as manager_run,
        ):
            uuid4.return_value.hex = "abc123"
            self.assertTrue(manager.paste_into_tmux(target, "private transcript"))
        run.assert_called_once_with(
            ["tmux", "load-buffer", "-b", "codex-deck-dictation-abc123", "-"],
            input="private transcript", text=True, capture_output=True,
            timeout=10, check=True,
        )
        self.assertEqual(exists.call_count, 2)
        self.assertEqual(manager_run.call_args_list[0].args[0], [
            "tmux", "if-shell", "-F", "-t", "%9", "1",
            "paste-buffer -d -p -r -b codex-deck-dictation-abc123 -t %9 ; display-message -p codex-deck-pasted",
            "display-message -p codex-deck-paste-blocked",
        ])
        self.assertEqual(manager_run.call_args_list[-1].args[0],
                         ["tmux", "delete-buffer", "-b", "codex-deck-dictation-abc123"])

    def test_dictation_refuses_terminal_controls_without_loading_buffer(self):
        target = manager.TmuxInputTarget("/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345)
        with mock.patch.object(manager.subprocess, "run") as run:
            for text in ("first\rsecond", "escape\x1b[201~", "erase\x7f", "null\0"):
                self.assertFalse(manager.paste_into_tmux(target, text))
        run.assert_not_called()

    def test_dictation_revalidates_origin_after_loading(self):
        target = manager.TmuxInputTarget("/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345)
        with (
            mock.patch.object(manager, "tmux_target_exists", side_effect=[True, False]),
            mock.patch.object(manager.subprocess, "run"),
            mock.patch.object(manager, "_run") as run,
        ):
            self.assertFalse(manager.paste_into_tmux(target, "hello"))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][1], "delete-buffer")

    def test_global_dictation_restores_saved_target_after_focus_changes(self):
        state = manager.DeckStateManager()
        tmux_target = manager.TmuxInputTarget(
            "/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345
        )
        target = manager.InputTarget(
            "0xabc", manager.GHOSTTY_CLASS, 123, tmux_target
        )
        transcript = Path("/run/user/1000/codex-deck/dictation/transcript.txt")
        with (
            mock.patch.object(manager, "global_dictation_state", return_value="idle"),
            mock.patch.object(manager, "active_input_target", return_value=target),
            mock.patch.object(manager, "new_dictation_path", return_value=transcript),
            mock.patch.object(manager, "start_global_dictation", return_value=True),
        ):
            state._toggle_global_dictation()
        self.assertIs(state._global_dictation_target, target)
        self.assertEqual(state._global_dictation_path, transcript)

        with (
            mock.patch.object(manager, "global_dictation_state", return_value="recording"),
            mock.patch.object(manager, "stop_global_dictation", return_value=0),
            mock.patch.object(
                manager, "read_dictation_transcript", return_value="hello"
            ),
            mock.patch.object(manager, "deliver_dictation", return_value=True) as deliver,
            mock.patch.object(manager, "cleanup_dictation_path") as cleanup,
        ):
            state._toggle_global_dictation()
        deliver.assert_called_once_with(target, "hello")
        cleanup.assert_called_once_with(transcript)
        self.assertIsNone(state._global_dictation_target)
        self.assertIsNone(state._global_dictation_path)

    def test_failed_delivery_retains_recovery_file_and_never_retargets(self):
        state = manager.DeckStateManager()
        target = manager.InputTarget(
            "0xabc",
            manager.GHOSTTY_CLASS,
            123,
            manager.TmuxInputTarget(
                "/dev/pts/8", "main", "3", "%9", 456, "codex", 900, 12345
            ),
        )
        transcript = Path("/run/user/1000/codex-deck/dictation/transcript.txt")
        state._global_dictation_target = target
        state._global_dictation_path = transcript
        with (
            mock.patch.object(manager, "global_dictation_state", return_value="recording"),
            mock.patch.object(manager, "stop_global_dictation", return_value=0),
            mock.patch.object(
                manager, "read_dictation_transcript", return_value="hello"
            ),
            mock.patch.object(manager, "deliver_dictation", return_value=False) as deliver,
            mock.patch.object(manager, "cleanup_dictation_path") as cleanup,
            mock.patch.object(manager, "_notify") as notify,
        ):
            state._toggle_global_dictation()
        deliver.assert_called_once_with(target, "hello")
        cleanup.assert_not_called()
        notify.assert_called_once_with(
            "Dictation target was lost",
            f"Insertion was not confirmed; recovery file: {transcript}",
        )

    def test_manager_stop_retains_recovery_file_when_cancel_fails(self):
        state = manager.DeckStateManager()
        transcript = Path("/run/user/1000/codex-deck/dictation/transcript.txt")
        state._global_dictation_path = transcript
        with (
            mock.patch.object(
                manager, "global_dictation_state", return_value="transcribing"
            ),
            mock.patch.object(
                manager, "cancel_global_dictation", return_value=False
            ) as cancel,
            mock.patch.object(manager, "cleanup_dictation_path") as cleanup,
            mock.patch.object(manager, "_notify") as notify,
        ):
            state.stop()
        cancel.assert_called_once_with()
        cleanup.assert_not_called()
        notify.assert_called_once_with(
            "Dictation needs recovery",
            f"Shutdown could not cancel dictation; recovery file: {transcript}",
        )

    def test_global_dictation_state_reads_voxtype_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state"
            with mock.patch.object(manager, "VOXTYPE_STATE_PATH", state_path):
                self.assertEqual(manager.global_dictation_state(), "stopped")
                state_path.write_text("recording\n")
                self.assertEqual(manager.global_dictation_state(), "recording")
                state_path.write_text("unexpected\n")
                self.assertEqual(manager.global_dictation_state(), "stopped")

    def test_send_enter_uses_kernel_enter_key_with_existing_ydotool_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / ".ydotool_socket"
            socket_path.touch()
            with (
                mock.patch.object(manager, "YDOTOOL_SOCKET", socket_path),
                mock.patch.object(manager, "_run", return_value="") as run,
            ):
                self.assertTrue(manager.send_enter_to_focused_input())
        run.assert_called_once_with(
            ["ydotool", "key", "28:1", "28:0"], timeout=3, check=True
        )

    def test_send_enter_starts_ydotool_service_when_socket_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / ".ydotool_socket"

            def run_command(argv, **_kwargs):
                if argv == ["systemctl", "--user", "start", "ydotool.service"]:
                    socket_path.touch()
                return ""

            with (
                mock.patch.object(manager, "YDOTOOL_SOCKET", socket_path),
                mock.patch.object(manager, "_run", side_effect=run_command) as run,
            ):
                self.assertTrue(manager.send_enter_to_focused_input())
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(
                    ["systemctl", "--user", "start", "ydotool.service"],
                    timeout=10,
                    check=True,
                ),
                mock.call(
                    ["ydotool", "key", "28:1", "28:0"],
                    timeout=3,
                    check=True,
                ),
            ],
        )

    def test_media_control_reports_when_no_player_accepts_command(self):
        error = manager.subprocess.CalledProcessError(1, ["playerctl", "play-pause"])
        with (
            mock.patch.object(manager, "_run", side_effect=error),
            mock.patch.object(manager, "_notify") as notify,
        ):
            self.assertFalse(manager.control_media("play-pause"))
        notify.assert_called_once_with(
            "No controllable media",
            "No active MPRIS player accepted the command.",
        )

    def test_canonical_page_has_ten_panes_and_new_bottom_row(self):
        page_path = Path(__file__).parents[1] / "page.json"
        page = json.loads(page_path.read_text())

        actions = {}
        for position, key in page["keys"].items():
            action = key["states"]["0"]["actions"][0]
            actions[position] = (action["id"], action["settings"])

        pane_actions = [
            actions[f"{column}x{row}"]
            for row in range(2)
            for column in range(5)
        ]
        self.assertEqual(
            pane_actions,
            [
                ("com_sluongng_CodexDeck::CodexPane", {"slot": slot})
                for slot in range(10)
            ],
        )
        self.assertEqual(
            [actions[f"{column}x2"][0] for column in range(5)],
            [
                "com_sluongng_CodexDeck::GlobalDictation",
                "com_sluongng_CodexDeck::SendEnter",
                "com_sluongng_CodexDeck::NewCodex",
                "com_sluongng_CodexDeck::MediaPlayPause",
                "com_sluongng_CodexDeck::AirPods",
            ],
        )

    def press_airpods(self):
        # Exercise the public button entry point, retaining the real worker but
        # joining it so all effects are observed before mocks are removed.
        worker = threading.Thread
        threads = []

        def create_worker(*args, **kwargs):
            thread = worker(*args, **kwargs)
            threads.append(thread)
            return thread

        with (
            mock.patch.object(manager.threading, "Thread", side_effect=create_worker),
            mock.patch.object(manager.threading, "excepthook") as worker_error,
        ):
            manager.DeckStateManager().handle("airpods", 0)
            for thread in threads:
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
            worker_error.assert_not_called()

    def airpods_objects(self, adapter, connected=False, powered=True):
        path = f"/org/bluez/{adapter}/dev_7C_F3_4D_84_BF_F9"
        return json.dumps({"data": [{
            f"/org/bluez/{adapter}": {"org.bluez.Adapter1": {
                "Powered": {"type": "b", "data": powered},
            }},
            f"/org/bluez/{adapter}/dev_00_11_22_33_44_55": {
                "org.bluez.Device1": {
                    "Address": {"type": "s", "data": "00:11:22:33:44:55"},
                    "Connected": {"type": "b", "data": not connected},
                },
            },
            path: {"org.bluez.Device1": {
                "Address": {"type": "s", "data": manager.AIRPODS_MAC},
                "Adapter": {"type": "o", "data": f"/org/bluez/{adapter}"},
                "Connected": {"type": "b", "data": connected},
            }},
        }]})

    def test_airpods_connect_uses_current_adapter_then_a2dp_and_default_sink(self):
        card = "bluez_card.7C_F3_4D_84_BF_F9"
        sink = "bluez_output.7C_F3_4D_84_BF_F9.1"
        for adapter in ("hci0", "hci1", "hci12"):
            with (
                self.subTest(adapter=adapter),
                mock.patch.object(manager.time, "sleep"),
                mock.patch.object(
                    manager, "_run",
                    side_effect=[self.airpods_objects(adapter), "", card, "",
                                 f"70\t{sink}\tmodule", ""],
                ) as run,
            ):
                self.press_airpods()
            self.assertEqual(run.call_args_list, [
                mock.call([
                    "busctl", "--json=short", "call", "org.bluez", "/",
                    "org.freedesktop.DBus.ObjectManager", "GetManagedObjects",
                ], check=True),
                mock.call([
                    "busctl", "call", "org.bluez",
                    f"/org/bluez/{adapter}/dev_7C_F3_4D_84_BF_F9",
                    "org.bluez.Device1", "Connect",
                ], timeout=20, check=True),
                mock.call(["pactl", "list", "cards", "short"]),
                mock.call(["pactl", "set-card-profile", card, "a2dp-sink"]),
                mock.call(["pactl", "list", "sinks", "short"]),
                mock.call(["pactl", "set-default-sink", sink]),
            ])

    def test_airpods_disconnect_uses_discovered_connected_device(self):
        with mock.patch.object(manager, "_run", side_effect=[
            self.airpods_objects("hci1", connected=True), "",
        ]) as run:
            self.press_airpods()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0], [
            "busctl", "call", "org.bluez",
            "/org/bluez/hci1/dev_7C_F3_4D_84_BF_F9",
            "org.bluez.Device1", "Disconnect",
        ])

    def test_airpods_status_tracks_adapter_changes(self):
        with mock.patch.object(manager, "_run", side_effect=[
            self.airpods_objects("hci0", connected=False),
            self.airpods_objects("hci1", connected=True),
        ]):
            self.assertFalse(manager.airpods_connected())
            self.assertTrue(manager.airpods_connected())

    def test_airpods_prefers_connected_device_across_adapters(self):
        objects = json.loads(self.airpods_objects("hci0"))["data"][0]
        objects.update(json.loads(self.airpods_objects("hci1", connected=True))["data"][0])
        snapshot = json.dumps({"data": [objects]})
        with mock.patch.object(manager, "_run", return_value=snapshot):
            self.assertTrue(manager.airpods_connected())
        with mock.patch.object(manager, "_run", side_effect=[snapshot, ""]) as run:
            self.press_airpods()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0], [
            "busctl", "call", "org.bluez",
            "/org/bluez/hci1/dev_7C_F3_4D_84_BF_F9",
            "org.bluez.Device1", "Disconnect",
        ])

    def test_airpods_connect_skips_unpowered_adapter(self):
        objects = json.loads(self.airpods_objects("hci0", powered=False))["data"][0]
        objects.update(json.loads(self.airpods_objects("hci1"))["data"][0])
        with (
            mock.patch.object(manager.time, "sleep"),
            mock.patch.object(manager, "_run", side_effect=[
                json.dumps({"data": [objects]}), "",
                "bluez_card.7C_F3_4D_84_BF_F9", "",
                "70\tbluez_output.7C_F3_4D_84_BF_F9.1\tmodule", "",
            ]) as run,
        ):
            self.press_airpods()
        self.assertEqual(run.call_args_list[1].args[0], [
            "busctl", "call", "org.bluez",
            "/org/bluez/hci1/dev_7C_F3_4D_84_BF_F9",
            "org.bluez.Device1", "Connect",
        ])

    def test_airpods_missing_or_failed_discovery_does_not_connect(self):
        for response in ('{"data": [{}]}', 'invalid json',
                         self.airpods_objects("hci0", powered=False)):
            with (
                self.subTest(response=response),
                mock.patch.object(manager, "_run", return_value=response) as run,
                mock.patch.object(manager.log, "error") as error,
            ):
                self.press_airpods()
                self.assertEqual(run.call_count, 1)
                error.assert_called_once()

    def test_airpods_connection_failure_logs_bluez_reason(self):
        failure = manager.subprocess.CalledProcessError(
            1, ["busctl"], stderr="Call failed: br-connection-page-timeout"
        )
        with (
            mock.patch.object(manager, "_run", side_effect=[
                self.airpods_objects("hci1"), failure,
            ]) as run,
            mock.patch.object(manager.log, "error") as error,
        ):
            self.press_airpods()
        self.assertEqual(run.call_count, 2)
        self.assertIn("br-connection-page-timeout", error.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
