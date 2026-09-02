from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.PluginManager.PluginBase import PluginBase

from .actions import AirPodsAction
from .actions import AppDictationAction
from .actions import AppThreadAction
from .actions import CodexPaneAction
from .actions import MicMuteAction
from .actions import OutputMuteAction
from .actions import VolumeDownAction
from .actions import VolumeUpAction
from .manager import DeckStateManager


KEY_ONLY = {
    Input.Key: ActionInputSupport.SUPPORTED,
    Input.Dial: ActionInputSupport.UNSUPPORTED,
    Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
}


class CodexDeckPlugin(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "Codex Deck"
        self.GITHUB_REPO = "https://github.com/sluongng/dotfiles"
        super().__init__()

        self.manager = DeckStateManager()
        for suffix, name, action in (
            ("CodexPane", "Codex pane", CodexPaneAction),
            ("AppThread", "Recent ChatGPT task", AppThreadAction),
            ("AppDictation", "ChatGPT dictation", AppDictationAction),
            ("VolumeDown", "Volume down", VolumeDownAction),
            ("VolumeUp", "Volume up", VolumeUpAction),
            ("OutputMute", "Mute output", OutputMuteAction),
            ("MicMute", "Mute microphone", MicMuteAction),
            ("AirPods", "AirPods connect", AirPodsAction),
        ):
            self.add_action_holder(
                ActionHolder(
                    plugin_base=self,
                    action_core=action,
                    action_id_suffix=suffix,
                    action_name=name,
                    action_support=KEY_ONLY,
                )
            )

        self.register(
            plugin_name="Codex Deck",
            github_repo="https://github.com/sluongng/dotfiles",
            plugin_version="0.5.0",
            app_version="1.5.0-beta.15",
        )
        self.manager.start()

    def on_uninstall(self):
        self.manager.stop()
        super().on_uninstall()
