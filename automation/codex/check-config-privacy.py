#!/usr/bin/env python3
"""Reject machine-local Codex project tables from tracked Git content."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10 on stock macOS and older Linux.
    from _vendor import tomli as tomllib


CONFIG_PATH = "config/codex/config.toml"
COMMENTED_PROJECTS_TABLE_RE = re.compile(
    r"^\s*(?:#\s*)+\[projects(?:\]|\.)"
)


def privacy_issues(text: str) -> tuple[bool, list[int], str | None]:
    commented_lines = [
        line_number
        for line_number, line in enumerate(text.splitlines(), 1)
        if COMMENTED_PROJECTS_TABLE_RE.match(line)
    ]
    try:
        active = "projects" in tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return False, commented_lines, str(error)
    return active, commented_lines, None


def check_text(label: str, text: str) -> bool:
    active, lines, parse_error = privacy_issues(text)
    if parse_error is not None:
        print(f"{label}: invalid TOML: {parse_error}", file=sys.stderr)
        return False
    if not active and not lines:
        return True
    location = f":{', '.join(str(line) for line in lines)}" if lines else ""
    print(
        f"{label}{location}: project trust tables are private; "
        "keep them in ~/.codex/projects.local.toml",
        file=sys.stderr,
    )
    return False


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def check_staged() -> bool:
    result = git("show", f":{CONFIG_PATH}")
    if result.returncode:
        return True
    return check_text(f"staged {CONFIG_PATH}", result.stdout)


def check_history(revisions: list[str]) -> bool:
    commits = git("rev-list", *revisions)
    if commits.returncode:
        print(commits.stderr.rstrip(), file=sys.stderr)
        return False

    checked_blobs: dict[str, tuple[bool, list[int], str | None]] = {}
    for commit in commits.stdout.splitlines():
        blob = git("rev-parse", f"{commit}:{CONFIG_PATH}")
        if blob.returncode:
            continue
        blob_id = blob.stdout.strip()
        issues = checked_blobs.get(blob_id)
        if issues is None:
            contents = git("show", blob_id)
            if contents.returncode:
                print(contents.stderr.rstrip(), file=sys.stderr)
                return False
            issues = privacy_issues(contents.stdout)
            checked_blobs[blob_id] = issues
        active, lines, parse_error = issues
        if parse_error is not None:
            print(
                f"commit {commit} {CONFIG_PATH}: invalid TOML: {parse_error}",
                file=sys.stderr,
            )
            return False
        if active or lines:
            location = (
                f":{', '.join(str(line) for line in lines)}" if lines else ""
            )
            print(
                f"commit {commit} {CONFIG_PATH}{location}: "
                "project trust tables are private; "
                "keep them in ~/.codex/projects.local.toml",
                file=sys.stderr,
            )
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--file", type=Path)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--history", nargs="+", metavar="REVISION")
    args = parser.parse_args()

    if args.file is not None:
        return 0 if check_text(str(args.file), args.file.read_text()) else 1
    if args.staged:
        return 0 if check_staged() else 1
    return 0 if check_history(args.history) else 1


if __name__ == "__main__":
    sys.exit(main())
