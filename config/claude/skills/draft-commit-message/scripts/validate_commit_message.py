#!/usr/bin/env python3
"""Validate commit messages against core MyFirstContribution rules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re

TRAILER_RE = re.compile(r"^[A-Za-z0-9-]+: .+")
TRAILER_CONTINUATION_RE = re.compile(r"^[ \t].+")


def read_message(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def strip_comment_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if not line.startswith("#")]


def body_without_trailers(lines: list[str]) -> list[str]:
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

    if saw_trailer:
        return lines[:cursor]
    return lines[:end]


def validate(lines: list[str], max_subject: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not lines or not lines[0].strip():
        return ["Subject line is missing."], warnings

    subject = lines[0]
    if len(subject) > max_subject:
        errors.append(
            f"Subject is {len(subject)} characters; keep it at {max_subject} or less."
        )

    if ": " not in subject:
        warnings.append("Subject does not contain a `component: summary` prefix.")

    if len(lines) > 1 and lines[1] != "":
        errors.append("Line 2 must be blank.")

    if len(lines) <= 2:
        warnings.append("Message body is missing; add context and explain why.")
        return errors, warnings

    body_lines = body_without_trailers(lines[2:])
    nonempty_body_lines = [line for line in body_lines if line.strip()]
    if not nonempty_body_lines:
        warnings.append("Message body is missing; add context and explain why.")
        return errors, warnings

    for index, line in enumerate(body_lines, start=3):
        if not line or line.startswith("> "):
            continue
        if len(line) > 72:
            errors.append(
                f"Body line {index} is {len(line)} characters; wrap to 72 or less."
            )

    lowered_body = "\n".join(nonempty_body_lines).lower()
    if not any(
        token in lowered_body
        for token in ("because", "so that", "why", "motivat", "in order to")
    ):
        warnings.append("Body may be missing explicit why/context language.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a commit message against Git-style structure rules."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="Path to a commit message file, or - to read from stdin.",
    )
    parser.add_argument(
        "--max-subject",
        type=int,
        default=50,
        help="Maximum allowed subject length (default: 50).",
    )
    args = parser.parse_args()

    content = read_message(args.path).rstrip("\n")
    raw_lines = content.splitlines()
    lines = strip_comment_lines(raw_lines)
    errors, warnings = validate(lines, args.max_subject)

    if errors:
        print("FAIL")
        for message in errors:
            print(f"- {message}")
        if warnings:
            print("WARN")
            for message in warnings:
                print(f"- {message}")
        return 1

    print("PASS")
    if warnings:
        print("WARN")
        for message in warnings:
            print(f"- {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
