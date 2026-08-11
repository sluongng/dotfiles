from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import weakref
from dataclasses import dataclass
from pathlib import Path

from gi.repository import GLib
from loguru import logger as log


AIRPODS_MAC = "7C:F3:4D:84:BF:F9"
AIRPODS_DBUS_PATH = "/org/bluez/hci0/dev_7C_F3_4D_84_BF_F9"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "codex-deck"
EVENTS_PATH = STATE_DIR / "events.jsonl"
ACK_PATH = STATE_DIR / "acknowledged.json"
PANE_RE = re.compile(r"^%\d+$")


@dataclass(frozen=True)
class Pane:
    pane_id: str
    session: str
    window: str
    active: bool
    project: str
    title: str
    busy: bool = False
    pane_index: str = "0"


@dataclass(frozen=True)
class Pending:
    pane_id: str
    turn_id: str
    project: str
    timestamp: float


@dataclass(frozen=True)
class Snapshot:
    pending: tuple[Pending, ...] = ()
    panes: tuple[Pane, ...] = ()
    volume: int | None = None
    output_muted: bool = False
    mic_muted: bool = False
    airpods_connected: bool = False


def parse_volume(text: str) -> tuple[int | None, bool]:
    match = re.search(r"Volume:\s+([0-9.]+)", text)
    volume = round(float(match.group(1)) * 100) if match else None
    return volume, "[MUTED]" in text


def project_name(path: str) -> str:
    path = path.rstrip("/")
    return Path(path).name or "/"


def _run(argv: list[str], timeout: float = 5.0, check: bool = False) -> str:
    result = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )
    return result.stdout.strip()


def _parent_pid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def ancestor_root(pid: int, roots: set[int], parent_of=_parent_pid) -> int | None:
    seen = set()
    while pid > 1 and pid not in seen:
        if pid in roots:
            return pid
        seen.add(pid)
        parent = parent_of(pid)
        if parent is None:
            return None
        pid = parent
    return None


def busy_pane_ids(pane_roots: dict[int, str]) -> set[str]:
    try:
        candidates = _run(
            ["pgrep", "-f", "^systemd-inhibit .*Codex is running an active turn"]
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    busy = set()
    roots = set(pane_roots)
    for value in candidates.splitlines():
        try:
            root = ancestor_root(int(value), roots)
        except ValueError:
            continue
        if root is not None:
            busy.add(pane_roots[root])
    return busy


def list_codex_panes() -> tuple[Pane, ...]:
    fmt = "#{pane_id}\t#{session_name}\t#{window_index}\t#{window_active}\t#{pane_index}\t#{pane_pid}\t#{pane_current_command}\t#{pane_current_path}\t#{pane_title}"
    try:
        output = _run(["tmux", "list-panes", "-a", "-F", fmt])
    except (OSError, subprocess.SubprocessError):
        return ()
    rows = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 9 or fields[6] != "codex":
            continue
        rows.append(fields)
    pane_roots = {int(fields[5]): fields[0] for fields in rows}
    busy = busy_pane_ids(pane_roots)
    panes = []
    for fields in rows:
        panes.append(
            Pane(
                pane_id=fields[0],
                session=fields[1],
                window=fields[2],
                active=fields[3] == "1",
                project=project_name(fields[7]),
                title=fields[8],
                busy=fields[0] in busy,
                pane_index=fields[4],
            )
        )
    return tuple(panes)


def natural_key(value: str):
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", value)
        if part
    )


def order_panes(panes: tuple[Pane, ...]) -> tuple[Pane, ...]:
    """Keep slots deterministic regardless of focus or completion state."""
    return tuple(
        sorted(
            panes,
            key=lambda pane: (
                natural_key(pane.session),
                natural_key(pane.window),
                natural_key(pane.pane_index),
                int(pane.pane_id[1:]),
            ),
        )
    )


def attention_transitions(
    previous_busy: dict[str, bool], panes: tuple[Pane, ...]
) -> tuple[Pane, ...]:
    return tuple(
        pane for pane in panes if previous_busy.get(pane.pane_id) is True and not pane.busy
    )


def record_attention(pane: Pane, timestamp: float | None = None) -> None:
    timestamp = time.time() if timestamp is None else timestamp
    event = {
        "type": "agent-attention",
        "thread-id": None,
        "turn-id": f"tmux-{pane.pane_id[1:]}-{int(timestamp * 1_000_000)}",
        "cwd": pane.project,
        "tmux-pane": pane.pane_id,
        "timestamp": timestamp,
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a") as output:
        output.write(json.dumps(event, separators=(",", ":")) + "\n")


def load_acknowledged() -> dict[str, str]:
    try:
        data = json.loads(ACK_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_pending(panes: tuple[Pane, ...]) -> tuple[Pending, ...]:
    pane_map = {pane.pane_id: pane for pane in panes}
    acknowledged = load_acknowledged()
    latest = {}
    try:
        lines = EVENTS_PATH.read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        pane_id = resolve_event_pane(event, panes)
        turn_id = event.get("turn-id")
        if pane_id not in pane_map or not isinstance(turn_id, str):
            continue
        candidate = Pending(
            pane_id=pane_id,
            turn_id=turn_id,
            project=project_name(event.get("cwd", "")),
            timestamp=float(event.get("timestamp", 0)),
        )
        current = latest.get(pane_id)
        if current is None or candidate.timestamp >= current.timestamp:
            latest[pane_id] = candidate
    unacknowledged = (
        item
        for item in latest.values()
        if acknowledged.get(item.pane_id) != item.turn_id
    )
    return tuple(sorted(unacknowledged, key=lambda item: item.timestamp, reverse=True))


def resolve_event_pane(event: dict, panes: tuple[Pane, ...]) -> str | None:
    pane_id = event.get("tmux-pane")
    pane_ids = {pane.pane_id for pane in panes}
    if pane_id in pane_ids:
        return pane_id
    thread_id = event.get("thread-id", "")
    if not isinstance(thread_id, str):
        return None
    # Codex truncates the terminal-title thread ID to a unique 29-char prefix.
    matches = [pane.pane_id for pane in panes if pane.title.startswith(thread_id[:29])]
    return matches[0] if len(matches) == 1 else None


def airpods_connected() -> bool:
    try:
        return _run(
            [
                "busctl",
                "get-property",
                "org.bluez",
                AIRPODS_DBUS_PATH,
                "org.bluez.Device1",
                "Connected",
            ],
            check=True,
        ).endswith(" true")
    except (OSError, subprocess.SubprocessError):
        return False


def audio_state() -> tuple[int | None, bool, bool]:
    try:
        volume, muted = parse_volume(_run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]))
    except (OSError, subprocess.SubprocessError):
        volume, muted = None, False
    try:
        _, mic_muted = parse_volume(_run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"]))
    except (OSError, subprocess.SubprocessError):
        mic_muted = False
    return volume, muted, mic_muted


def switch_to_pane(pane: Pane) -> bool:
    try:
        _run(["tmux", "select-window", "-t", f"{pane.session}:{pane.window}"], check=True)
        _run(["tmux", "select-pane", "-t", pane.pane_id], check=True)
        clients = _run(
            ["tmux", "list-clients", "-F", "#{client_tty}\t#{client_activity}"]
        ).splitlines()
        if clients:
            client_tty = max(clients, key=lambda row: int(row.split("\t")[1])).split("\t")[0]
            _run(["tmux", "switch-client", "-c", client_tty, "-t", pane.session], check=True)
        _run(
            [
                "hyprctl",
                "eval",
                'return hl.dispatch(hl.dsp.focus({window = "class:^(com.mitchellh.ghostty)$"}))',
            ],
            timeout=3,
            check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        log.error(f"Failed to switch to {pane.pane_id}: {error}")
        return False


def acknowledge(pane_id: str, turn_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = load_acknowledged()
    data[pane_id] = turn_id
    temporary = ACK_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, sort_keys=True) + "\n")
    temporary.replace(ACK_PATH)


class DeckStateManager:
    def __init__(self):
        self._actions = weakref.WeakSet()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._busy: dict[str, bool] = {}
        self.snapshot = Snapshot()

    def start(self):
        if self._thread is not None:
            return
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._watch, name="codex-deck-state", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def register(self, action):
        with self._lock:
            self._actions.add(action)
        GLib.idle_add(self._render_one, action, self.snapshot)

    @staticmethod
    def _render_one(action, snapshot):
        try:
            action.render(snapshot)
        except Exception as error:
            log.error(f"Codex Deck render failed: {error}")
        return False

    def _render_all(self, snapshot):
        with self._lock:
            actions = list(self._actions)
        for action in actions:
            GLib.idle_add(self._render_one, action, snapshot)

    def _watch(self):
        while not self._stop.wait(0.75):
            panes = list_codex_panes()
            for pane in attention_transitions(self._busy, panes):
                record_attention(pane)
            self._busy = {pane.pane_id: pane.busy for pane in panes}
            pending = load_pending(panes)
            panes = order_panes(panes)
            volume, output_muted, mic_muted = audio_state()
            snapshot = Snapshot(
                pending=pending,
                panes=panes,
                volume=volume,
                output_muted=output_muted,
                mic_muted=mic_muted,
                airpods_connected=airpods_connected(),
            )
            if snapshot != self.snapshot:
                self.snapshot = snapshot
                self._render_all(snapshot)

    def handle(self, kind: str, slot: int):
        threading.Thread(
            target=self._handle, args=(kind, slot), name=f"codex-deck-{kind}", daemon=True
        ).start()

    def _handle(self, kind: str, slot: int):
        if kind == "pane" and slot < len(self.snapshot.panes):
            pane = self.snapshot.panes[slot]
            if switch_to_pane(pane):
                pending = next(
                    (item for item in self.snapshot.pending if item.pane_id == pane.pane_id),
                    None,
                )
                if pending is not None:
                    acknowledge(pending.pane_id, pending.turn_id)
        elif kind == "volume_down":
            _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"])
        elif kind == "volume_up":
            _run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"])
        elif kind == "output_mute":
            _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
        elif kind == "mic_mute":
            _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"])
        elif kind == "airpods":
            self._toggle_airpods()

    def _toggle_airpods(self):
        method = "Disconnect" if airpods_connected() else "Connect"
        try:
            _run(
                [
                    "busctl",
                    "call",
                    "org.bluez",
                    AIRPODS_DBUS_PATH,
                    "org.bluez.Device1",
                    method,
                ],
                timeout=20,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            log.error(f"AirPods {method.lower()} failed: {error}")
            return
        if method != "Connect":
            return
        card = "bluez_card." + AIRPODS_MAC.replace(":", "_")
        for _ in range(20):
            try:
                cards = _run(["pactl", "list", "cards", "short"])
                if card in cards:
                    _run(["pactl", "set-card-profile", card, "a2dp-sink"])
                    break
            except (OSError, subprocess.SubprocessError):
                pass
            time.sleep(0.25)
        for _ in range(20):
            try:
                sinks = _run(["pactl", "list", "sinks", "short"])
                sink = next(
                    (line.split("\t")[1] for line in sinks.splitlines() if AIRPODS_MAC.replace(":", "_") in line),
                    None,
                )
                if sink:
                    _run(["pactl", "set-default-sink", sink])
                    break
            except (OSError, subprocess.SubprocessError, IndexError):
                pass
            time.sleep(0.25)
