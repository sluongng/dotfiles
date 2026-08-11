import importlib.util
import sys
import tempfile
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

    def test_order_panes_is_deterministic_by_tmux_location(self):
        panes = (
            manager.Pane("%3", "work", "3", True, "three", "three"),
            manager.Pane("%4", "work", "1", False, "one", "one"),
            manager.Pane("%5", "work", "2", False, "two", "two"),
        )
        ordered = manager.order_panes(panes)
        self.assertEqual([pane.pane_id for pane in ordered], ["%4", "%5", "%3"])

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
