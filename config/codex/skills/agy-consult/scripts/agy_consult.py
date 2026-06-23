#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


DEFAULT_MODEL = "Gemini 3.5 Flash (High)"
DEFAULT_TIMEOUT = "5m"
DEFAULT_OUTPUT_DIR = Path("~/.cache/codex/agy-consult").expanduser()


SCOUT_CONTRACT = """\
You are an advisory scout invoked by Codex through Antigravity CLI.

Operate as a fast, lower-depth scout. Do not make final decisions. Do not edit
files. Do not run destructive commands. Focus on bounded reconnaissance and
evidence extraction.

Return concise JSON or JSON-compatible Markdown with this shape:
{
  "summary": "...",
  "findings": [
    {
      "claim": "...",
      "evidence": ["path:line or command output summary"],
      "confidence": "low|medium|high",
      "needs_codex_verification": true
    }
  ],
  "recommended_next_step": "...",
  "limitations": "..."
}
"""


def parse_duration(value: str) -> int:
    value = value.strip()
    match = re.fullmatch(r"(\d+)([smh]?)", value)
    if not match:
        raise argparse.ArgumentTypeError("duration must look like 300, 300s, 5m, or 1h")
    amount = int(match.group(1))
    unit = match.group(2) or "s"
    multiplier = {"s": 1, "m": 60, "h": 3600}[unit]
    return amount * multiplier


def duration_for_agy(seconds: int) -> str:
    return f"{seconds}s"


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return slug[:64] or "run"


def read_prompt(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.prompt_file:
        chunks.append(Path(args.prompt_file).read_text())
    if args.prompt:
        chunks.append(args.prompt)
    if not chunks:
        raise SystemExit("provide --prompt or --prompt-file")
    return "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()


def build_prompt(user_prompt: str, repo: Path, no_contract: bool) -> str:
    if no_contract:
        return user_prompt
    return (
        f"{SCOUT_CONTRACT}\n"
        f"Workspace path exposed read-only: {repo}\n\n"
        f"Task:\n{user_prompt}\n"
    )


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"required command not found on PATH: {name}")
    return path


def ensure_path(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    return resolved


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def make_run_dir(output_dir: Path, name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = uuid.uuid4().hex[:8]
    run_dir = output_dir.expanduser() / f"{timestamp}-{slugify(name)}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def build_bwrap_command(
    *,
    bwrap: str,
    agy: str,
    repo: Path,
    gemini_dir: Path,
    run_dir: Path,
    model: str,
    timeout_seconds: int,
    prompt: str,
) -> list[str]:
    return [
        bwrap,
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--dev-bind",
        "/dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(gemini_dir),
        str(gemini_dir),
        "--bind",
        str(run_dir),
        str(run_dir),
        "--chdir",
        str(repo),
        agy,
        "--model",
        model,
        "--add-dir",
        str(repo),
        "--log-file",
        str(run_dir / "agy.log"),
        "--print-timeout",
        duration_for_agy(timeout_seconds),
        "--print",
        prompt,
    ]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run agy as a read-only advisory scout for Codex."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repo/workspace path")
    parser.add_argument("--prompt", help="inline scout prompt")
    parser.add_argument("--prompt-file", type=Path, help="file containing the scout prompt")
    parser.add_argument("--name", default="scout", help="label for saved artifacts")
    parser.add_argument("--model", default=os.environ.get("AGY_CONSULT_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--timeout",
        default=os.environ.get("AGY_CONSULT_TIMEOUT", DEFAULT_TIMEOUT),
        type=parse_duration,
        help="agy print timeout, such as 300s or 5m",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--no-contract",
        action="store_true",
        help="do not prepend the standard Codex scout contract",
    )
    args = parser.parse_args()

    repo = ensure_path(args.repo, "repo")
    if not repo.is_dir():
        raise SystemExit(f"repo is not a directory: {repo}")
    if is_under(repo, Path("/tmp")):
        raise SystemExit("repo paths under /tmp are not supported with the read-only wrapper")

    gemini_dir = ensure_path(Path("~/.gemini").expanduser(), "Antigravity/Gemini state dir")
    bwrap = require_command("bwrap")
    agy = require_command("agy")

    user_prompt = read_prompt(args)
    full_prompt = build_prompt(user_prompt, repo, args.no_contract)
    run_dir = make_run_dir(args.output_dir, args.name)
    (run_dir / "prompt.txt").write_text(full_prompt)

    command = build_bwrap_command(
        bwrap=bwrap,
        agy=agy,
        repo=repo,
        gemini_dir=gemini_dir,
        run_dir=run_dir,
        model=args.model,
        timeout_seconds=args.timeout,
        prompt=full_prompt,
    )
    write_json(
        run_dir / "command.json",
        {
            "agy": agy,
            "bwrap": bwrap,
            "model": args.model,
            "repo": str(repo),
            "timeout_seconds": args.timeout,
            "argv": command[:-1] + ["<prompt omitted; see prompt.txt>"],
        },
    )

    try:
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout + 60,
        )
    except subprocess.TimeoutExpired as exc:
        (run_dir / "response.md").write_text(exc.stdout or "")
        (run_dir / "stderr.log").write_text(exc.stderr or "")
        write_json(run_dir / "result.json", {"exit_code": None, "timed_out": True})
        print(f"agy-consult timed out; artifacts: {run_dir}", file=sys.stderr)
        return 124

    (run_dir / "response.md").write_text(proc.stdout)
    (run_dir / "stderr.log").write_text(proc.stderr)
    write_json(run_dir / "result.json", {"exit_code": proc.returncode, "timed_out": False})

    print(f"agy-consult artifacts: {run_dir}")
    if proc.stdout.strip():
        print("\n--- agy response ---")
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print("\n--- agy stderr ---", file=sys.stderr)
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
