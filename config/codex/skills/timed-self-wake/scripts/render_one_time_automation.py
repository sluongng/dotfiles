#!/usr/bin/env python3
"""Render a one-time codex-automaton TOML file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Automation id, lowercase letters/digits/hyphens.")
    parser.add_argument("--name", required=True, help="Human-readable automation name.")
    parser.add_argument("--description", default="One-time Codex wake-up automation.")
    parser.add_argument("--cwd", required=True, help="Working directory for the future Codex run.")
    parser.add_argument("--on-calendar", required=True, help="Absolute systemd OnCalendar expression.")
    parser.add_argument("--prompt-file", required=True, type=Path, help="Prompt text to embed.")
    parser.add_argument("--out", required=True, type=Path, help="Output TOML path.")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--service-tier", default="")
    parser.add_argument("--persistent", action="store_true", help="Set systemd Persistent=true.")
    return parser.parse_args()


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    args = parse_args()
    if not ID_RE.match(args.id):
        raise SystemExit("--id must be lowercase letters, digits, and hyphens, under 64 chars")

    prompt = args.prompt_file.read_text(encoding="utf-8").strip() + "\n"
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)

    service_tier = f"service_tier = {toml_string(args.service_tier)}" if args.service_tier else ""
    codex_lines = [
        "[codex]",
        'bin = "codex"',
        f"model = {toml_string(args.model)}",
        f"reasoning_effort = {toml_string(args.reasoning_effort)}",
    ]
    if service_tier:
        codex_lines.append(service_tier)
    codex_lines.extend(
        [
            'sandbox = "danger-full-access"',
            'approval_policy = "never"',
            "search = false",
            "skip_git_repo_check = false",
            "dangerous_bypass = false",
            "extra_args = []",
        ]
    )
    codex_block = "\n".join(codex_lines)

    content = f"""version = 1
id = {toml_string(args.id)}
name = {toml_string(args.name)}
description = {toml_string(args.description)}
cwd = {toml_string(args.cwd)}
on_calendar = {toml_string(args.on_calendar)}
persistent = {str(args.persistent).lower()}
prompt = {toml_string(prompt)}
status = "ACTIVE"
execution_environment = "local"

[source]
kind = "manual"
id = ""
imported_from = ""

[worktree]
enabled = false

{codex_block}

[output]
last_message = true
json = false
"""
    out.write_text(content, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
