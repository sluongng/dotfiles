from __future__ import annotations

import fcntl
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import weakref
from contextlib import closing
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
CODEX_STATE_DB = Path.home() / ".codex/state_5.sqlite"
CODEX_DESKTOP_LOG_ROOT = STATE_DIR.parent / "codex/logs"
THREAD_REFRESH_SECONDS = 2.0
ACTIVE_APP_THREAD_RE = re.compile(
    r"thread_stream_view_activity_changed active=true conversationId=([0-9a-f-]{36})"
)
RENDERER_WINDOW_ID_RE = re.compile(r"rendererWindowId=(\d+)")


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
class AppThread:
    thread_id: str
    title: str
    project: str = ""


@dataclass(frozen=True)
class AppActivity:
    thread_id: str
    renderer_window_id: int


@dataclass(frozen=True)
class Snapshot:
    pending: tuple[Pending, ...] = ()
    panes: tuple[Pane, ...] = ()
    app_threads: tuple[AppThread, ...] = ()
    dictation_state: str = "idle"
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


def send_return_to_window(window_address: str) -> None:
    """Send Return to one exact Hyprland window instead of global focus."""
    if re.fullmatch(r"0x[0-9a-fA-F]+", window_address) is None:
        raise ValueError("invalid Hyprland window address")
    _run(
        [
            "hyprctl",
            "eval",
            "return hl.dispatch(hl.dsp.send_shortcut({ "
            f'mods = "", key = "Return", window = "address:{window_address}" '
            "}))",
        ],
        timeout=3,
        check=True,
    )


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


def focus_codex_app(
    attempts: int = 20,
    delay: float = 0.25,
    window_address: str | None = None,
) -> bool:
    for attempt in range(attempts):
        try:
            clients = json.loads(
                _run(["hyprctl", "-j", "clients"], timeout=3, check=True)
            )
            matches = [
                client
                for client in clients
                if client.get("class") == "Chatgpt" and client.get("mapped", True)
                and (window_address is None or client.get("address") == window_address)
            ]
            if not matches:
                raise RuntimeError("ChatGPT window is not mapped yet")
            target = min(
                matches,
                key=lambda client: (
                    client.get("title") != "ChatGPT",
                    client.get("focusHistoryID", 1_000_000),
                ),
            )
            active_workspace = json.loads(
                _run(["hyprctl", "-j", "activeworkspace"], timeout=3, check=True)
            )
            target_workspace = target.get("workspace", {}).get("id")
            if (
                isinstance(target_workspace, int)
                and active_workspace.get("id") != target_workspace
            ):
                _run(
                    [
                        "hyprctl",
                        "dispatch",
                        f'hl.dsp.focus({{ workspace = "{target_workspace}" }})',
                    ],
                    timeout=3,
                    check=True,
                )
            address = target.get("address")
            if not isinstance(address, str) or not address.startswith("0x"):
                raise RuntimeError("ChatGPT window has no usable address")
            _run(
                [
                    "hyprctl",
                    "eval",
                    f'return hl.dispatch(hl.dsp.focus({{window = "address:{address}"}}))',
                ],
                timeout=3,
                check=True,
            )
            active = json.loads(
                _run(["hyprctl", "-j", "activewindow"], timeout=3, check=True)
            )
            if active.get("class") == "Chatgpt" and active.get("address") == address:
                return True
        except (
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ):
            pass
        if attempt + 1 < attempts:
            time.sleep(delay)
    return False


def recent_app_threads(limit: int = 4) -> tuple[AppThread, ...]:
    """Return the newest root tasks, ordered oldest-to-newest for the deck."""
    try:
        uri = f"file:{CODEX_STATE_DB}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=1)) as connection:
            rows = connection.execute(
                """
                SELECT id, COALESCE(NULLIF(TRIM(name), ''), TRIM(title)), cwd
                  FROM threads
                 WHERE archived = 0
                   AND TRIM(preview) <> ''
                   AND COALESCE(thread_source, '') <> 'subagent'
                   AND NOT EXISTS (
                       SELECT 1
                         FROM thread_spawn_edges edge
                        WHERE edge.child_thread_id = threads.id
                   )
                 ORDER BY recency_at_ms DESC, id DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except sqlite3.Error as error:
        log.debug(f"Failed to read recent ChatGPT tasks: {error}")
        return ()
    threads = []
    for thread_id, title, cwd in reversed(rows):
        try:
            uuid.UUID(thread_id)
        except (ValueError, TypeError, AttributeError):
            continue
        clean_title = " ".join((title or "Untitled task").split())
        threads.append(AppThread(thread_id, clean_title, project_name(cwd)))
    return tuple(threads)


def open_app_thread(thread: AppThread) -> bool:
    """Open one exact task in the existing ChatGPT app and focus it."""
    try:
        uuid.UUID(thread.thread_id)
        _run(
            ["xdg-open", f"codex://threads/{thread.thread_id}"],
            timeout=5,
            check=True,
        )
        return focus_app_thread(thread.thread_id)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        log.error(f"Failed to open ChatGPT task {thread.title}: {error}")
        return False


def current_app_thread_id() -> str | None:
    activity = latest_app_activity()
    return activity.thread_id if activity is not None else None


def desktop_log_marker() -> tuple[tuple[Path, int], ...]:
    markers = []
    for path in desktop_log_paths():
        try:
            markers.append((path, path.stat().st_size))
        except OSError:
            continue
    return tuple(markers)


def turn_started_since(
    marker: tuple[tuple[Path, int], ...] | None, thread_id: str | None
) -> bool:
    if marker is None or thread_id is None:
        return False
    offsets = dict(marker)
    paths = set(offsets)
    paths.update(desktop_log_paths())
    for path in paths:
        try:
            with path.open("rb") as source:
                source.seek(offsets.get(path, 0))
                text = source.read().decode(errors="replace")
        except OSError:
            continue
        if any(
            "method=turn/start" in line
            and f"conversationId={thread_id}" in line
            for line in text.splitlines()
        ):
            return True
    return False


def desktop_log_paths() -> tuple[Path, ...]:
    paths = tuple(CODEX_DESKTOP_LOG_ROOT.rglob("codex-desktop-*.log"))
    try:
        clients = json.loads(_run(["hyprctl", "-j", "clients"], timeout=3, check=True))
        pids = {
            client.get("pid")
            for client in clients
            if client.get("class") == "Chatgpt" and isinstance(client.get("pid"), int)
        }
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pids = set()
    live_paths = tuple(
        path for path in paths if any(f"-{pid}-" in path.name for pid in pids)
    )
    return live_paths or paths


def latest_app_activity(
    marker: tuple[tuple[Path, int], ...] | None = None,
) -> AppActivity | None:
    offsets = dict(marker or ())
    paths = set(desktop_log_paths())
    paths.update(offsets)
    latest: tuple[str, str, int, AppActivity] | None = None
    for path in paths:
        try:
            with path.open("rb") as source:
                if marker is None:
                    source.seek(max(0, path.stat().st_size - 512_000))
                else:
                    source.seek(offsets.get(path, 0))
                text = source.read().decode(errors="replace")
        except OSError:
            continue
        for index, line in enumerate(text.splitlines()):
            thread_match = ACTIVE_APP_THREAD_RE.search(line)
            window_match = RENDERER_WINDOW_ID_RE.search(line)
            if (
                thread_match is None
                or window_match is None
                or "rendererWindowFocused=true" not in line
            ):
                continue
            activity = AppActivity(thread_match.group(1), int(window_match.group(1)))
            candidate = (line.partition(" ")[0], path.name, index, activity)
            if latest is None or candidate[:3] > latest[:3]:
                latest = candidate
    return latest[3] if latest is not None else None


def focused_app_activity_since(
    marker: tuple[tuple[Path, int], ...],
    window_address: str,
    attempts: int = 10,
    delay: float = 0.05,
) -> AppActivity | None:
    latest = None
    for attempt in range(attempts):
        activity = latest_app_activity(marker)
        if active_codex_window_address() != window_address:
            return None
        if activity is not None:
            latest = activity
        if attempt + 1 < attempts:
            time.sleep(delay)
    return latest


def codex_app_window_addresses() -> tuple[str, ...]:
    try:
        clients = json.loads(_run(["hyprctl", "-j", "clients"], timeout=3, check=True))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return ()
    matches = [
        client
        for client in clients
        if client.get("class") == "Chatgpt"
        and client.get("mapped", True)
        and isinstance(client.get("address"), str)
    ]
    matches.sort(
        key=lambda client: (
            client.get("title") != "ChatGPT",
            client.get("focusHistoryID", 1_000_000),
        )
    )
    return tuple(client["address"] for client in matches)


def focus_app_thread(thread_id: str, attempts: int = 20, delay: float = 0.25) -> bool:
    """Focus the app window that reports the routed task as active."""
    for attempt in range(attempts):
        addresses = codex_app_window_addresses()
        if len(addresses) == 1 and active_codex_window_address() == addresses[0]:
            activity = latest_app_activity()
            if activity is not None and activity.thread_id == thread_id:
                return True
        for address in addresses:
            marker = desktop_log_marker()
            if not focus_codex_app(
                attempts=1, delay=0, window_address=address
            ):
                continue
            activity = focused_app_activity_since(marker, address)
            if activity is not None and activity.thread_id == thread_id:
                return True
        if attempt + 1 < attempts:
            time.sleep(delay)
    return False


def active_codex_window_address() -> str | None:
    try:
        active = json.loads(
            _run(["hyprctl", "-j", "activewindow"], timeout=3, check=True)
        )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    address = active.get("address")
    if active.get("class") != "Chatgpt" or not isinstance(address, str):
        return None
    return address


def app_thread_context_matches(
    thread_id: str, window_address: str, renderer_window_id: int
) -> bool:
    if active_codex_window_address() != window_address:
        return False
    activity = latest_app_activity()
    return (
        activity is not None
        and activity.thread_id == thread_id
        and activity.renderer_window_id == renderer_window_id
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
        if event.get("notification-policy") == "suppress":
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
    lock_path = ACK_PATH.with_suffix(".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load_acknowledged()
        data[pane_id] = turn_id
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{ACK_PATH.name}.", suffix=".tmp", dir=ACK_PATH.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w") as output:
                output.write(json.dumps(data, sort_keys=True) + "\n")
            temporary.replace(ACK_PATH)
        finally:
            temporary.unlink(missing_ok=True)


def acknowledge_focused_pane(
    client_name: str, expected_pane_id: str | None = None
) -> bool:
    """Acknowledge a pending completion only when its Codex pane is being viewed."""
    if expected_pane_id and PANE_RE.fullmatch(expected_pane_id) is None:
        return False
    try:
        if client_name:
            clients = (
                _run(
                    [
                        "tmux",
                        "display-message",
                        "-p",
                        "-c",
                        client_name,
                        "#{client_flags}\t#{pane_id}",
                    ],
                    check=True,
                ),
            )
        else:
            clients = tuple(
                _run(
                    ["tmux", "list-clients", "-F", "#{client_flags}\t#{pane_id}"],
                    check=True,
                ).splitlines()
            )
    except (OSError, subprocess.SubprocessError):
        return False

    focused_panes = []
    for client in clients:
        fields = client.split("\t")
        if len(fields) != 2:
            continue
        flags = set(fields[0].split(","))
        pane_id = fields[1]
        if "focused" in flags and PANE_RE.fullmatch(pane_id):
            focused_panes.append(pane_id)
    if expected_pane_id:
        if expected_pane_id not in focused_panes:
            return False
        pane_id = expected_pane_id
    elif len(focused_panes) == 1:
        pane_id = focused_panes[0]
    else:
        return False

    panes = list_codex_panes()
    if not any(pane.pane_id == pane_id for pane in panes):
        return False
    pending = next((item for item in load_pending(panes) if item.pane_id == pane_id), None)
    if pending is None:
        return False
    acknowledge(pending.pane_id, pending.turn_id)
    return True


class DeckStateManager:
    def __init__(self):
        self._actions = weakref.WeakSet()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._busy: dict[str, bool] = {}
        self._app_threads: tuple[AppThread, ...] = ()
        self._app_threads_refreshed_at = 0.0
        self._app_interaction_lock = threading.Lock()
        self._dictation_lock = threading.Lock()
        self._dictation_process = None
        self._dictation_state = "idle"
        self._dictation_thread_id = None
        self._dictation_window_address = None
        self._dictation_renderer_window_id = None
        self.snapshot = Snapshot()

    def start(self):
        if self._thread is not None:
            return
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._watch, name="codex-deck-state", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._dictation_lock:
            process = self._dictation_process
            self._dictation_process = None
            self._dictation_state = "idle"
            self._dictation_thread_id = None
            self._dictation_window_address = None
            self._dictation_renderer_window_id = None
        if process is not None:
            try:
                process.stdin.close()
                process.wait(timeout=3)
            except (OSError, subprocess.SubprocessError):
                process.terminate()

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
            now = time.monotonic()
            if now - self._app_threads_refreshed_at >= THREAD_REFRESH_SECONDS:
                self._app_threads = recent_app_threads()
                self._app_threads_refreshed_at = now
            volume, output_muted, mic_muted = audio_state()
            snapshot = Snapshot(
                pending=pending,
                panes=panes,
                app_threads=self._app_threads,
                dictation_state=self._dictation_state,
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
            target=self._handle,
            args=(kind, slot),
            name=f"codex-deck-{kind}",
            daemon=True,
        ).start()

    def handle_app_thread(self, thread: AppThread):
        worker = threading.Thread(
            target=self._handle_app_thread,
            args=(thread,),
            name="codex-deck-app-thread",
            daemon=True,
        )
        worker.start()
        return worker

    def _handle_app_thread(self, thread: AppThread):
        with self._app_interaction_lock:
            return open_app_thread(thread)

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
        elif kind == "app_dictation":
            if not self._app_interaction_lock.acquire(blocking=False):
                return
            try:
                self._toggle_dictation()
            finally:
                self._app_interaction_lock.release()
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

    def _toggle_dictation(self):
        with self._dictation_lock:
            if self._dictation_state == "transcribing":
                return
            process = self._dictation_process
            if process is None:
                marker = desktop_log_marker()
                if not focus_codex_app():
                    return
                window_address = active_codex_window_address()
                activity = (
                    focused_app_activity_since(marker, window_address)
                    if window_address is not None
                    else None
                )
                if activity is None and window_address is not None:
                    addresses = codex_app_window_addresses()
                    if len(addresses) == 1 and addresses[0] == window_address:
                        time.sleep(0.2)
                        activity = latest_app_activity()
                if (
                    window_address is None
                    or active_codex_window_address() != window_address
                    or activity is None
                ):
                    log.error("Cannot safely start ChatGPT dictation without an exact task")
                    return
                try:
                    process = subprocess.Popen(
                        [
                            "wtype",
                            "-M",
                            "ctrl",
                            "-M",
                            "shift",
                            "-P",
                            "d",
                            "-m",
                            "shift",
                            "-m",
                            "ctrl",
                            "-",
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(0.15)
                    if process.poll() is not None:
                        raise subprocess.SubprocessError("wtype exited early")
                except (OSError, subprocess.SubprocessError) as error:
                    log.error(f"Failed to start ChatGPT dictation: {error}")
                    return
                self._dictation_process = process
                self._dictation_state = "recording"
                self._dictation_thread_id = activity.thread_id
                self._dictation_window_address = window_address
                self._dictation_renderer_window_id = activity.renderer_window_id
                return
            self._dictation_process = None
            self._dictation_state = "transcribing"
            thread_id = self._dictation_thread_id
            self._dictation_thread_id = None
            window_address = self._dictation_window_address
            self._dictation_window_address = None
            renderer_window_id = self._dictation_renderer_window_id
            self._dictation_renderer_window_id = None
        focused = (
            window_address is not None
            and focus_codex_app(window_address=window_address)
        )
        context_matches = (
            focused
            and thread_id is not None
            and renderer_window_id is not None
            and app_thread_context_matches(
                thread_id, window_address, renderer_window_id
            )
        )
        if not context_matches and thread_id is not None:
            open_app_thread(AppThread(thread_id, "Dictation target"))
        marker = desktop_log_marker() if thread_id is not None else None
        try:
            process.stdin.close()
            process.wait(timeout=3)
        except (OSError, subprocess.SubprocessError) as error:
            log.error(f"Failed to stop ChatGPT dictation: {error}")
            process.terminate()
            self._dictation_state = "idle"
            return
        # Key-up requests ChatGPT's native transcribe-and-insert action. Enter
        # is ignored while transcription is in flight. If focus or the visible
        # task changes, restore the original task instead of cancelling the
        # pending submission. Send Enter once, then passively wait for its exact
        # turn/start event so a missing log event cannot submit repeatedly.
        if marker is None or thread_id is None:
            log.error("Cannot safely auto-submit ChatGPT dictation without an exact task marker")
            self._dictation_state = "idle"
            return
        try:
            for _ in range(60):
                if self._stop.is_set():
                    break
                time.sleep(0.5)
                if self._stop.is_set():
                    break
                if not app_thread_context_matches(
                    thread_id, window_address, renderer_window_id
                ):
                    if not open_app_thread(AppThread(thread_id, "Dictation target")):
                        continue
                if not app_thread_context_matches(
                    thread_id, window_address, renderer_window_id
                ):
                    continue
                send_return_to_window(window_address)
                break
            else:
                log.error("Could not restore the ChatGPT dictation target")
                return

            for _ in range(300):
                if self._stop.is_set():
                    return
                time.sleep(0.1)
                if turn_started_since(marker, thread_id):
                    return
            log.error("ChatGPT dictation submission was not confirmed")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            log.error(f"Failed to submit ChatGPT dictation: {error}")
        finally:
            self._dictation_state = "idle"

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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "acknowledge-focused-pane":
        return 2
    client_name = argv[1] if len(argv) > 1 else ""
    expected_pane_id = argv[2] if len(argv) > 2 else None
    acknowledge_focused_pane(client_name, expected_pane_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
