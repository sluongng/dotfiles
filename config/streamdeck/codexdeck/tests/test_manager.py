import importlib.util
import sys
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

    def test_resolve_event_pane_from_terminal_title(self):
        thread_id = "019fefbd-482d-7490-96e3-9bf043d73dd2"
        panes = (
            manager.Pane("%7", "work", "2", False, "codex", thread_id[:29] + "..."),
        )
        self.assertEqual(
            manager.resolve_event_pane({"thread-id": thread_id, "tmux-pane": None}, panes),
            "%7",
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
                    ["hyprctl", "dispatch", "focuswindow", "class:^(com.mitchellh.ghostty)$"],
                    timeout=3,
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
