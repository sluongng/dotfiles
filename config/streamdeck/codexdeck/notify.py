#!/usr/bin/env python3
"""Record Codex turn completion and show a privacy-preserving desktop notice."""

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


NOTIFICATION_WORKER_ARG = "--notification-worker"
THREAD_ID_PATTERN = re.compile(r"[0-9a-fA-F-]{36}")


@dataclass(frozen=True)
class ThreadLineage:
    kind: str
    parent_thread_id: str | None = None
    agent_path: str | None = None


def _subagent_lineage(source: object) -> ThreadLineage | None:
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return None
    if not isinstance(source, dict):
        return None
    subagent = source.get("subagent")
    if not isinstance(subagent, dict):
        return None
    thread_spawn = subagent.get("thread_spawn")
    if not isinstance(thread_spawn, dict):
        return ThreadLineage("subagent")
    return ThreadLineage(
        "subagent",
        parent_thread_id=thread_spawn.get("parent_thread_id"),
        agent_path=thread_spawn.get("agent_path"),
    )


def thread_lineage(thread_id: str) -> ThreadLineage:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    state_db = codex_home / "state_5.sqlite"
    if state_db.is_file():
        try:
            with closing(
                sqlite3.connect(f"file:{state_db}?mode=ro", uri=True, timeout=1)
            ) as connection:
                row = connection.execute(
                    """
                    SELECT threads.source,
                           threads.agent_path,
                           threads.thread_source,
                           thread_spawn_edges.parent_thread_id
                    FROM threads
                    LEFT JOIN thread_spawn_edges
                      ON thread_spawn_edges.child_thread_id = threads.id
                    WHERE threads.id = ?
                    """,
                    (thread_id,),
                ).fetchone()
            if row is not None:
                source, agent_path, thread_source, parent_thread_id = row
                lineage = _subagent_lineage(source)
                if lineage is not None:
                    return lineage
                if thread_source == "subagent" or parent_thread_id:
                    return ThreadLineage(
                        "subagent",
                        parent_thread_id=parent_thread_id,
                        agent_path=agent_path,
                    )
                return ThreadLineage("root")
        except sqlite3.Error:
            pass

    sessions_dir = codex_home / "sessions"
    for rollout_path in sessions_dir.glob(f"*/*/*/*{thread_id}*.jsonl"):
        try:
            with rollout_path.open() as rollout:
                metadata = json.loads(rollout.readline()).get("payload", {})
        except (OSError, json.JSONDecodeError):
            continue
        lineage = _subagent_lineage(metadata.get("source"))
        return lineage if lineage is not None else ThreadLineage("root")
    return ThreadLineage("unknown")


def notification_worker(body: str) -> int:
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name=Codex",
                "--icon=utilities-terminal",
                "Codex thread finished",
                body,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return 0


def post_notification(body: str) -> None:
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                NOTIFICATION_WORKER_ARG,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            text=True,
        )
        if process.stdin is not None:
            process.stdin.write(body)
            process.stdin.close()
    except (OSError, BrokenPipeError):
        pass


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == NOTIFICATION_WORKER_ARG:
        return notification_worker(sys.stdin.read(4096))
    if len(sys.argv) < 2:
        return 0
    try:
        payload = json.loads(sys.argv[-1])
    except json.JSONDecodeError:
        return 0
    pane = os.environ.get("TMUX_PANE", "")
    thread_id = payload.get("thread-id", "")
    if (
        payload.get("type") != "agent-turn-complete"
        or THREAD_ID_PATTERN.fullmatch(thread_id) is None
    ):
        return 0
    lineage = thread_lineage(thread_id)
    event = {
        "type": "agent-turn-complete",
        "thread-id": thread_id,
        "turn-id": payload.get("turn-id"),
        "cwd": payload.get("cwd", ""),
        "tmux-pane": pane if re.fullmatch(r"%\d+", pane) else None,
        "timestamp": time.time(),
        "session-kind": lineage.kind,
        "notification-policy": "show" if lineage.kind == "root" else "suppress",
    }
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    state_dir = state_home / "codex-deck"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "events.jsonl").open("a") as output:
        output.write(json.dumps(event, separators=(",", ":")) + "\n")

    if lineage.kind != "root":
        return 0

    cwd = payload.get("cwd", "")
    body = f"Finished in {cwd}" if cwd else "A Codex thread finished."
    post_notification(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
