#!/usr/bin/env python3
"""Record Codex turn completion and show a privacy-preserving desktop notice."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    try:
        payload = json.loads(sys.argv[-1])
    except json.JSONDecodeError:
        return 0
    pane = os.environ.get("TMUX_PANE", "")
    thread_id = payload.get("thread-id", "")
    if payload.get("type") != "agent-turn-complete" or not re.fullmatch(
        r"[0-9a-fA-F-]{36}", thread_id
    ):
        return 0
    event = {
        "type": "agent-turn-complete",
        "thread-id": thread_id,
        "turn-id": payload.get("turn-id"),
        "cwd": payload.get("cwd", ""),
        "tmux-pane": pane if re.fullmatch(r"%\d+", pane) else None,
        "timestamp": time.time(),
    }
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    state_dir = state_home / "codex-deck"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "events.jsonl").open("a") as output:
        output.write(json.dumps(event, separators=(",", ":")) + "\n")

    cwd = payload.get("cwd", "")
    body = f"Finished in {cwd}" if cwd else "A Codex thread finished."
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


if __name__ == "__main__":
    raise SystemExit(main())
