#!/usr/bin/env python3
"""Wrap commit-message prose with fmt while preserving structured text."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIST_RE = re.compile(r"^((?:[-+*]|[0-9]+[.)])\s+)(.*)$")
TRAILER_RE = re.compile(r"^[A-Za-z0-9-]+: .+")
TRAILER_CONTINUATION_RE = re.compile(r"^[ \t].+")
FENCE_RE = re.compile(r"^(?:```|~~~)")


def read_message(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def trailer_start(lines: list[str]) -> int:
    end = len(lines)
    while end > 0 and lines[end - 1] == "":
        end -= 1

    cursor = end
    saw_trailer = False
    while cursor > 0:
        line = lines[cursor - 1]
        if saw_trailer and line == "":
            cursor -= 1
            break
        if TRAILER_RE.match(line):
            saw_trailer = True
            cursor -= 1
            continue
        if saw_trailer and TRAILER_CONTINUATION_RE.match(line):
            cursor -= 1
            continue
        break

    return cursor if saw_trailer else len(lines)


def run_fmt(lines: list[str], width: int) -> list[str]:
    fmt = shutil.which("fmt")
    if fmt is None:
        raise RuntimeError("fmt is required to format commit-message prose")

    result = subprocess.run(
        [fmt, "-w", str(width)],
        check=True,
        input="\n".join(lines) + "\n",
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.rstrip("\n").splitlines()


def is_protected(line: str, in_fence: bool) -> bool:
    return (
        in_fence
        or not line
        or line.startswith("#")
        or line.startswith(">")
        or line[:1].isspace()
    )


def format_prose(lines: list[str], width: int) -> list[str]:
    formatted: list[str] = []
    cursor = 0
    in_fence = False

    while cursor < len(lines):
        line = lines[cursor]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            formatted.append(line)
            cursor += 1
            continue

        if is_protected(line, in_fence):
            formatted.append(line)
            cursor += 1
            continue

        list_match = LIST_RE.match(line)
        if list_match:
            prefix, text = list_match.groups()
            if not text.strip() or len(prefix) >= width:
                formatted.append(line)
                cursor += 1
                continue
            wrapped = run_fmt([text], width - len(prefix))
            formatted.append(prefix + wrapped[0])
            formatted.extend(" " * len(prefix) + item for item in wrapped[1:])
            cursor += 1
            continue

        paragraph: list[str] = []
        while cursor < len(lines):
            candidate = lines[cursor]
            if (
                FENCE_RE.match(candidate)
                or is_protected(candidate, in_fence)
                or LIST_RE.match(candidate)
            ):
                break
            paragraph.append(candidate)
            cursor += 1
        formatted.extend(run_fmt(paragraph, width))

    return formatted


def format_message(content: str, width: int) -> str:
    had_final_newline = content.endswith("\n")
    lines = content.splitlines()
    if len(lines) <= 2:
        return content

    body = lines[2:]
    protected_tail = len(body)
    for index, line in enumerate(body):
        if line == "---" or (line.startswith("#") and ">8" in line):
            protected_tail = index
            break

    permanent_body = body[:protected_tail]
    trailers = trailer_start(permanent_body)
    result = (
        lines[:2]
        + format_prose(permanent_body[:trailers], width)
        + permanent_body[trailers:]
        + body[protected_tail:]
    )
    formatted = "\n".join(result)
    if had_final_newline:
        formatted += "\n"
    return formatted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wrap commit-message prose with fmt without changing structure."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="Path to a commit message file, or - to read from stdin.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=72,
        help="Maximum prose width (default: 72).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Replace the input file with the formatted message.",
    )
    args = parser.parse_args()

    if args.width < 20:
        parser.error("--width must be at least 20")
    if args.write and args.path == "-":
        parser.error("--write requires a file path")

    try:
        formatted = format_message(read_message(args.path), args.width)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.write:
        Path(args.path).write_text(formatted)
    else:
        sys.stdout.write(formatted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
