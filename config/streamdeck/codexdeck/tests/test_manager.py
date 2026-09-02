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

    def test_airpods_connect_uses_bluez_then_a2dp_and_default_sink(self):
        state = manager.DeckStateManager()
        card = "bluez_card.7C_F3_4D_84_BF_F9"
        sink = "bluez_output.7C_F3_4D_84_BF_F9.1"
        with (
            mock.patch.object(manager, "airpods_connected", return_value=False),
            mock.patch.object(manager.time, "sleep"),
            mock.patch.object(
                manager,
                "_run",
                side_effect=["", card, "", f"70\t{sink}\tmodule", ""],
            ) as run,
        ):
            state._toggle_airpods()
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(
                    [
                        "busctl",
                        "call",
                        "org.bluez",
                        manager.AIRPODS_DBUS_PATH,
                        "org.bluez.Device1",
                        "Connect",
                    ],
                    timeout=20,
                    check=True,
                ),
                mock.call(["pactl", "list", "cards", "short"]),
                mock.call(["pactl", "set-card-profile", card, "a2dp-sink"]),
                mock.call(["pactl", "list", "sinks", "short"]),
                mock.call(["pactl", "set-default-sink", sink]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
