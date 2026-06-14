#!/usr/bin/env python3
"""Link local-only worktree context without printing secret file contents."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SPECIAL_NAMES = {"user.bazelrc", ".bazelrc.user", ".buckconfig.local", "AGENTS.md"}


@dataclass(frozen=True)
class Candidate:
    rel: Path
    reason: str


def git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def repo_root(path: Path) -> Path:
    result = git(path, ["rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def tracked(repo: Path, rel: Path) -> bool:
    result = git(repo, ["ls-files", "--error-unmatch", "--", rel.as_posix()], check=False)
    return result.returncode == 0


def untracked_paths(repo: Path) -> set[Path]:
    result = git(repo, ["status", "--porcelain=v1", "--untracked-files=all"])
    paths: set[Path] = set()
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        paths.add(Path(line[3:]))
    return paths


def ignored_special_paths(repo: Path) -> set[Path]:
    result = git(
        repo,
        [
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            "user.bazelrc",
            ".bazelrc.user",
            ".buckconfig.local",
            "AGENTS.md",
            "*/AGENTS.md",
        ],
        check=False,
    )
    return {Path(line) for line in result.stdout.splitlines() if line}


def find_agents(repo: Path) -> set[Path]:
    rels: set[Path] = set()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        if "AGENTS.md" not in files:
            continue
        rel = Path(root, "AGENTS.md").relative_to(repo)
        if not tracked(repo, rel):
            rels.add(rel)
    return rels


def discover(primary: Path) -> list[Candidate]:
    paths = untracked_paths(primary) | ignored_special_paths(primary) | find_agents(primary)
    candidates: list[Candidate] = []
    for rel in sorted(paths):
        if rel.name in SPECIAL_NAMES:
            candidates.append(Candidate(rel, "special local context"))
    return candidates


def existing_link_ok(src: Path, dest: Path) -> bool:
    if not dest.exists() and not dest.is_symlink():
        return False
    try:
        if dest.is_symlink():
            return dest.resolve() == src.resolve()
        return src.stat().st_ino == dest.stat().st_ino and src.stat().st_dev == dest.stat().st_dev
    except OSError:
        return False


def link_one(src: Path, dest: Path, apply: bool) -> str:
    if existing_link_ok(src, dest):
        return "already-linked"
    if dest.exists() or dest.is_symlink():
        return "skipped-existing-destination"
    if not apply:
        return "would-link"

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dest)
        return "hardlinked"
    except OSError:
        os.symlink(src, dest)
        return "symlinked"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path, help="Primary checkout path")
    parser.add_argument("--worktree", required=True, type=Path, help="Target worktree path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report planned links")
    mode.add_argument("--apply", action="store_true", help="Create hardlinks or symlinks")
    args = parser.parse_args()

    primary = repo_root(args.primary)
    worktree = repo_root(args.worktree)
    candidates = discover(primary)

    if primary == worktree:
        print("primary and worktree resolve to the same checkout", file=sys.stderr)
        return 2

    for candidate in candidates:
        src = primary / candidate.rel
        dest = worktree / candidate.rel
        status = link_one(src, dest, apply=args.apply)
        print(f"{status}\t{candidate.rel.as_posix()}\t{candidate.reason}")

    if not candidates:
        print("no special local context files found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
