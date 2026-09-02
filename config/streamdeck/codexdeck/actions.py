from pathlib import Path

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionCore import ActionCore
from src.backend.PluginManager.EventAssigner import EventAssigner


ASSETS = Path(__file__).with_name("assets")


def fitted_label(text, max_chars=16):
    text = str(text or "")
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    # A 72px key has roughly 64px of usable label width. At the default font,
    # an average glyph is about 0.6em wide, so scale longer names accordingly.
    font_size = max(7, min(14, 100 // max(1, len(text))))
    return text, font_size


class ManagedKeyAction(ActionCore):
    kind = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_event_assigner(
            EventAssigner(
                id="Key Down",
                ui_label="Key Down",
                default_events=[Input.Key.Events.DOWN],
                callback=lambda _data=None: self._pressed(),
            )
        )

    @property
    def slot(self):
        return int(self.get_settings().get("slot", 0))

    def on_ready(self):
        # Pages created outside StreamController's UI do not automatically get
        # the control-owner fields that the UI writes for the first action.
        # Without them ActionCore silently ignores icon, label, and background
        # updates, leaving every hardware key black.
        state = self.get_state()
        if state is not None:
            permissions = state.action_permission_manager
            state_dict = permissions.get_state_dict()
            changed = False
            for key, value in (
                ("image-control-action", 0),
                ("label-control-actions", [0, 0, 0]),
                ("background-control-action", 0),
            ):
                if key not in state_dict:
                    state_dict[key] = value
                    changed = True
            if changed:
                self.page.save()
        self.plugin_base.manager.register(self)

    def _pressed(self):
        self.plugin_base.manager.handle(self.kind, self.slot)

    def render(self, snapshot):
        raise NotImplementedError

    def _media(self, name, fps=8, loop=True, update=False):
        self.set_media(
            media_path=str(ASSETS / name), fps=fps, loop=loop, update=update
        )

    def _labels(self, top="", center="", bottom=""):
        top, top_size = fitted_label(top, max_chars=14)
        center, center_size = fitted_label(center)
        bottom, bottom_size = fitted_label(bottom, max_chars=16)
        self.set_label(top, "top", font_size=min(9, top_size), update=False)
        self.set_label(center, "center", font_size=center_size, update=False)
        self.set_label(bottom, "bottom", font_size=min(9, bottom_size), update=True)


class CompletionSlotAction(ManagedKeyAction):
    kind = "completion"

    def render(self, snapshot):
        pending = snapshot.pending[self.slot] if self.slot < len(snapshot.pending) else None
        if pending is None:
            self._media("codex-dim.png", update=False)
            self.set_background_color([3, 8, 14, 255], update=False)
            self._labels()
            return
        self._media("codex-pulse.gif", fps=8, loop=True, update=False)
        self.set_background_color([3, 20, 18, 255], update=False)
        self._labels("DONE", pending.pane_id, pending.project)


class CodexPaneAction(ManagedKeyAction):
    kind = "pane"

    def render(self, snapshot):
        pane = snapshot.panes[self.slot] if self.slot < len(snapshot.panes) else None
        if pane is None:
            self._media("codex-dim.png", update=False)
            self.set_background_color([3, 8, 14, 255], update=False)
            self._labels()
            return
        pending = next(
            (item for item in snapshot.pending if item.pane_id == pane.pane_id), None
        )
        if pending is not None:
            self._media("codex-pulse.gif", fps=8, loop=True, update=False)
            self.set_background_color([3, 20, 18, 255], update=False)
            self._labels("", pane.project, "DONE")
            return
        self._media("codex-ready.png", update=False)
        color = [10, 62, 48, 255] if pane.active else [8, 27, 43, 255]
        self.set_background_color(color, update=False)
        self._labels("", pane.project, "WORKING" if pane.busy else "")


class AppThreadAction(ManagedKeyAction):
    kind = "app_thread"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rendered_thread = None

    def _pressed(self):
        if self._rendered_thread is not None:
            self.plugin_base.manager.handle_app_thread(self._rendered_thread)

    def render(self, snapshot):
        thread = (
            snapshot.app_threads[self.slot]
            if self.slot < len(snapshot.app_threads)
            else None
        )
        self._rendered_thread = thread
        if thread is None:
            self._media("codex-dim.png", update=False)
            self.set_background_color([3, 8, 14, 255], update=False)
            self._labels()
            return
        self._media("codex-ready.png", update=False)
        self.set_background_color([24, 30, 72, 255], update=False)
        self._labels(thread.project, str(self.slot + 1), thread.title)


class AppDictationAction(ManagedKeyAction):
    kind = "app_dictation"

    def render(self, snapshot):
        if snapshot.dictation_state == "recording":
            self._media("codex-pulse.gif", fps=8, loop=True, update=False)
            self.set_background_color([110, 24, 34, 255], update=False)
            self._labels("MIC", "LISTENING", "tap to send")
            return
        if snapshot.dictation_state == "transcribing":
            self._media("codex-pulse.gif", fps=8, loop=True, update=False)
            self.set_background_color([66, 38, 12, 255], update=False)
            self._labels("MIC", "SENDING", "transcribing")
            return
        self._media("codex-ready.png", update=False)
        self.set_background_color([13, 62, 52, 255], update=False)
        self._labels("", "DICTATE", "tap to start")


class AudioAction(ManagedKeyAction):
    asset = ""
    title = ""

    def render(self, snapshot):
        self._media(self.asset, update=False)
        self.set_background_color([10, 35, 55, 255], update=False)
        value = "?" if snapshot.volume is None else f"{snapshot.volume}%"
        self._labels(self.title, "", value)


class VolumeDownAction(AudioAction):
    kind = "volume_down"
    asset = "volume-down.png"
    title = "VOL -"


class VolumeUpAction(AudioAction):
    kind = "volume_up"
    asset = "volume-up.png"
    title = "VOL +"


class OutputMuteAction(ManagedKeyAction):
    kind = "output_mute"

    def render(self, snapshot):
        muted = snapshot.output_muted
        self._media("output-mute.png", update=False)
        self.set_background_color(
            [110, 24, 34, 255] if muted else [13, 62, 52, 255], update=False
        )
        self._labels("OUTPUT", "MUTE" if muted else "ON", "tap")


class MicMuteAction(ManagedKeyAction):
    kind = "mic_mute"

    def render(self, snapshot):
        muted = snapshot.mic_muted
        self._media("mic-mute.png", update=False)
        self.set_background_color(
            [110, 24, 34, 255] if muted else [66, 38, 12, 255], update=False
        )
        self._labels("MIC", "MUTE" if muted else "ON", "tap")


class AirPodsAction(ManagedKeyAction):
    kind = "airpods"

    def render(self, snapshot):
        self._media("airpods.png", update=False)
        self.set_background_color(
            [15, 80, 55, 255] if snapshot.airpods_connected else [18, 36, 68, 255],
            update=False,
        )
        self._labels(
            "AIRPODS",
            "ON" if snapshot.airpods_connected else "OFF",
            "disconnect" if snapshot.airpods_connected else "connect",
        )
