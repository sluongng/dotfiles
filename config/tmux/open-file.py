#!/usr/bin/env python3
"""Open a terminal path in a reusable Neovim pane beside its source pane."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import unicodedata
from urllib.parse import unquote, urlsplit


def tmux(*args: str) -> str:
    return subprocess.check_output(["tmux", *args], text=True, stderr=subprocess.PIPE).rstrip("\n")


def resolve_location(value: str, cwd: Path) -> tuple[Path, int, int]:
    value = value.strip()
    quoted = re.fullmatch(r'''(["'`])(.*?)\1(?::(\d+)(?::(\d+))?)?''', value)
    if quoted:
        value = quoted[2]
        if quoted[3]:
            value += ":" + quoted[3] + (":" + quoted[4] if quoted[4] else "")
    if any(c in value for c in ("\n", "\r", "\0")):
        raise ValueError("Select a single file path")
    line, column = 1, 1
    if value.startswith("file://"):
        url = urlsplit(value)
        if url.netloc not in ("", "localhost"):
            raise ValueError("Only local file URLs are supported")
        value = unquote(url.path)
        if url.fragment:
            match = re.fullmatch(r"L?(\d+)(?::(\d+))?", url.fragment)
            if not match:
                raise ValueError("Unsupported file URL fragment")
            line, column = int(match[1]), int(match[2] or 1)
    elif "://" in value:
        raise ValueError("Select a local file, not a URL")
    # Prefer an existing literal filename (a colon is legal in Unix filenames).
    path = Path(value).expanduser()
    path = path if path.is_absolute() else cwd / path
    if not path.is_file():
        match = re.fullmatch(r"(.+?):(\d+)(?::(\d+))?", value)
        if match:
            value, line, column = match[1], int(match[2]), int(match[3] or 1)
            path = Path(value).expanduser()
            path = path if path.is_absolute() else cwd / path
    if not path.is_file():
        raise ValueError(f"Not an existing file: {path}")
    return path.resolve(), max(1, line), max(1, column)


def character_at_cell(text: str, cell: int) -> int:
    width = 0
    for index, char in enumerate(text):
        size = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
        if width + size > cell:
            return index
        width += size
    return len(text)


def mouse_location(text: str, cell: int, cwd: Path) -> tuple[Path, int, int]:
    index = character_at_cell(text, cell)
    # Quoted filenames can contain spaces. Plain paths can be inside Markdown
    # parentheses or backticks; those delimiters are not part of the filename.
    pattern = r'''(?:"[^"\n]+"|'[^'\n]+'|`[^`\n]+`)(?::\d+(?::\d+)?)?|[^\s()<>\[\]{}]+'''
    for match in re.finditer(pattern, text):
        if match.start() <= index < match.end():
            return resolve_location(match[0].rstrip(",;"), cwd)
    raise ValueError("No file path under the mouse")


def wrapped_mouse_location(source: str, text: str, cell: int, row: int, scroll: int,
                           cwd: Path) -> tuple[Path, int, int]:
    height = int(tmux("display-message", "-p", "-t", source, "#{pane_height}"))
    # -J joins only soft wraps, not independent output lines. Capture on either
    # side of the clicked row to recover that row's complete logical line.
    head = tmux("capture-pane", "-p", "-J", "-t", source, "-S", str(-scroll), "-E", str(row - scroll)).splitlines()
    tail = tmux("capture-pane", "-p", "-J", "-t", source, "-S", str(row - scroll), "-E", str(height - 1 - scroll)).splitlines()
    visible = text.rstrip()
    if not visible or not head or not tail or not head[-1].endswith(visible) or not tail[0].startswith(visible):
        raise ValueError("No complete file path under the mouse")
    before = head[-1][:-len(visible)]
    cells = sum(0 if unicodedata.combining(c) else (2 if unicodedata.east_asian_width(c) in "WF" else 1) for c in before)
    return mouse_location(before + tail[0], cells + cell, cwd)


def remote_expression(path: Path, line: int, column: int) -> str:
    # JSON is decoded inside Neovim, so filenames never become Ex/Lua code.
    payload = json.dumps([str(path), line, column], ensure_ascii=True).replace("'", "''")
    lua = (
        "(function() local a=vim.json.decode(_A); "
        "local b=vim.fn.bufadd(a[1]); vim.fn.bufload(b); "
        "vim.cmd('hide buffer '..b); "
        "local row=math.min(a[2],vim.api.nvim_buf_line_count(b)); "
        "local s=vim.api.nvim_buf_get_lines(b,row-1,row,false)[1] or ''; "
        "vim.api.nvim_win_set_cursor(0,{row,math.min(a[3]-1,#s)}); return 1 end)()"
    ).replace("'", "''")
    return f"luaeval('{lua}', '{payload}')"


def nvim_request(socket: str, expression: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["nvim", "--server", socket, "--remote-expr", expression],
        capture_output=True, text=True, timeout=5,
    )


def open_file(source: str, location: tuple[Path, int, int], focus: bool = True) -> str:
    if not re.fullmatch(r"%\d+", source):
        raise ValueError("Missing source tmux pane")
    window = tmux("display-message", "-p", "-t", source, "#{window_id}")
    cwd = tmux("display-message", "-p", "-t", source, "#{pane_current_path}")
    server = tmux("display-message", "-p", "-t", source, "#{socket_path}")
    identity = hashlib.sha256(server.encode()).hexdigest()[:12]
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/tmux-file-open-{os.getuid()}")) / "tmux-file-open"
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (runtime / f"{identity}-{window[1:]}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        editor = tmux("show-options", "-wqv", "-t", window, "@file-editor-pane")
        panes = tmux("list-panes", "-t", window, "-F", "#{pane_id}").splitlines()
        socket = ""
        if editor in panes:
            socket = tmux("show-options", "-pqv", "-t", editor, "@file-editor-socket")
            command = tmux("display-message", "-p", "-t", editor, "#{pane_current_command}")
            if not socket or command != "nvim" or nvim_request(socket, "1").returncode:
                socket = ""  # Never respawn or commandeer a changed/closed pane.
        if not socket:
            socket = str(runtime / f"{identity}-{window[1:]}-{time.time_ns()}.sock")
            command = shlex.join(["nvim", "--listen", socket, "--", str(location[0])])
            editor = tmux("split-window", "-h", "-d", "-p", "45", "-t", source, "-c", cwd,
                          "-P", "-F", "#{pane_id}", "exec " + command)
            tmux("set-option", "-w", "-t", window, "@file-editor-pane", editor)
            tmux("set-option", "-p", "-t", editor, "@file-editor-socket", socket)
        expression = remote_expression(*location)
        deadline = time.monotonic() + 10
        while True:
            result = nvim_request(socket, expression)
            if result.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise ValueError("Neovim did not become ready: " + result.stderr.strip())
            time.sleep(0.1)
        if focus:
            tmux("select-pane", "-t", editor)
        return editor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="File[:line[:column]], or read one path from stdin")
    parser.add_argument("--pane", default=os.environ.get("TMUX_PANE", ""))
    parser.add_argument("--window", help="Source window captured before tmux-fingers swaps panes")
    parser.add_argument("--mouse-line")
    parser.add_argument("--mouse-column", type=int, default=0)
    parser.add_argument("--mouse-row", type=int, default=0)
    parser.add_argument("--scroll-position", type=int, default=0)
    parser.add_argument("--hyperlink", default="")
    parser.add_argument("--no-focus", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"%\d+", args.pane):
            raise ValueError("Missing source tmux pane")
        if args.window:
            # Fingers temporarily moves the original pane into a scratch window.
            # Its action is asynchronous: wait for restoration before splitting.
            deadline = time.monotonic() + 5
            while True:
                state = tmux("display-message", "-p", "-t", args.pane, "#{window_id} #{client_key_table}").split()
                if state[0] == args.window and (len(state) < 2 or state[1] != "fingers"):
                    break
                if time.monotonic() >= deadline:
                    raise ValueError("Source pane has not returned from file selection")
                time.sleep(0.05)
        cwd = Path(tmux("display-message", "-p", "-t", args.pane, "#{pane_current_path}"))
        if args.hyperlink.startswith(("https://", "http://")):
            # Preserve browser opening when Ctrl-clicking a real web hyperlink.
            if not args.dry_run:
                subprocess.Popen(["xdg-open", args.hyperlink], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 0
        if args.hyperlink:
            location = resolve_location(args.hyperlink, cwd)
        elif args.mouse_line is not None:
            try:
                location = mouse_location(args.mouse_line, args.mouse_column, cwd)
            except ValueError:
                location = wrapped_mouse_location(args.pane, args.mouse_line, args.mouse_column,
                                                  args.mouse_row, args.scroll_position, cwd)
        else:
            location = resolve_location(args.path if args.path is not None else sys.stdin.read(), cwd)
        if args.dry_run:
            print(json.dumps({"path": str(location[0]), "line": location[1], "column": location[2]}))
        else:
            print(open_file(args.pane, location, not args.no_focus))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        message = f"Open file: {error}"
        print(message, file=sys.stderr)
        if args.pane and not args.dry_run:
            subprocess.run(["tmux", "display-message", "-l", "-t", args.pane, "--", message], capture_output=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
