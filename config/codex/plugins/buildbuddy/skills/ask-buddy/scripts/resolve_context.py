#!/usr/bin/env python3
"""Print local BuildBuddy+Bazel research context as JSON."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


REPOS = [
    {
        "name": "bazel",
        "github": "bazelbuild/bazel",
        "env": "BAZEL_REPO",
        "relative": "bazelbuild/bazel",
    },
    {
        "name": "buildbuddy",
        "github": "buildbuddy-io/buildbuddy",
        "env": "BUILDBUDDY_REPO",
        "relative": "buildbuddy-io/buildbuddy",
    },
    {
        "name": "buildbuddy-toolchains",
        "github": "buildbuddy-io/buildbuddy-toolchains",
        "env": "BUILDBUDDY_TOOLCHAINS_REPO",
        "relative": "buildbuddy-io/buildbuddy-toolchains",
    },
    {
        "name": "buildbuddy-helm",
        "github": "buildbuddy-io/buildbuddy-helm",
        "env": "BUILDBUDDY_HELM_REPO",
        "relative": "buildbuddy-io/buildbuddy-helm",
    },
]


def run_git(repo: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def git_state(path: Path) -> dict[str, Any]:
    state: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return state

    top = run_git(path, ["rev-parse", "--show-toplevel"])
    if not top:
        state["git"] = False
        return state

    top_path = Path(top)
    status = run_git(top_path, ["status", "--porcelain"])
    state.update(
        {
            "git": True,
            "top_level": str(top_path),
            "head": run_git(top_path, ["rev-parse", "HEAD"]),
            "branch": run_git(top_path, ["branch", "--show-current"]),
            "origin": run_git(top_path, ["remote", "get-url", "origin"]),
            "dirty": bool(status),
        }
    )
    if status:
        state["status_porcelain"] = status.splitlines()[:20]
    return state


def find_upwards(start: Path, filename: str) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for path in [current, *current.parents]:
        candidate = path / filename
        if candidate.exists():
            return candidate
    return None


def first_value_line(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def parse_bazeliskrc(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith("USE_BAZEL") or key.startswith("BAZELISK_"):
            values[key] = value
    return values


def version_hints(project: Path) -> dict[str, Any]:
    hints: dict[str, Any] = {"project": str(project.resolve())}

    bazelversion = find_upwards(project, ".bazelversion")
    if bazelversion:
        hints["bazelversion"] = {
            "path": str(bazelversion),
            "version": first_value_line(bazelversion),
        }

    bazeliskrc = find_upwards(project, ".bazeliskrc")
    if bazeliskrc:
        hints["bazeliskrc"] = {
            "path": str(bazeliskrc),
            "values": parse_bazeliskrc(bazeliskrc),
        }

    selected = None
    source = None
    if hints.get("bazelversion", {}).get("version"):
        selected = hints["bazelversion"]["version"]
        source = ".bazelversion"
    elif hints.get("bazeliskrc", {}).get("values", {}).get("USE_BAZEL_VERSION"):
        selected = hints["bazeliskrc"]["values"]["USE_BAZEL_VERSION"]
        source = ".bazeliskrc:USE_BAZEL_VERSION"

    hints["selected_bazel_ref"] = selected or "HEAD"
    hints["selected_bazel_ref_source"] = source or "HEAD fallback"
    return hints


def repo_inventory(research_root: Path) -> list[dict[str, Any]]:
    inventory = []
    for repo in REPOS:
        candidates = []
        env_path = os.environ.get(repo["env"])
        if env_path:
            candidates.append({"source": repo["env"], "path": str(Path(env_path).expanduser())})
        default_path = research_root / repo["relative"]
        candidates.append({"source": "research_root", "path": str(default_path)})

        states = []
        selected = None
        for candidate in candidates:
            state = {**candidate, **git_state(Path(candidate["path"]).expanduser())}
            states.append(state)
            if selected is None and state.get("git"):
                selected = state

        inventory.append(
            {
                "name": repo["name"],
                "github": repo["github"],
                "env": repo["env"],
                "candidates": states,
                "selected": selected,
                "suggested_clone": str(research_root / repo["relative"]),
                "clone_url": f"https://github.com/{repo['github']}.git",
            }
        )
    return inventory


def default_research_root() -> Path:
    configured = os.environ.get("BUILDBUDDY_RESEARCH_ROOT") or os.environ.get("CODEX_RESEARCH_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "work"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        default=os.getcwd(),
        help="Workspace path used to discover .bazelversion and .bazeliskrc",
    )
    parser.add_argument(
        "--repo-root",
        default=str(default_research_root()),
        help="Generic parent directory for local clones; defaults to BUILDBUDDY_RESEARCH_ROOT, CODEX_RESEARCH_ROOT, then $HOME/work",
    )
    args = parser.parse_args()

    project = Path(args.project).expanduser()
    research_root = Path(args.repo_root).expanduser()
    result = {
        "research_root": str(research_root),
        "version_hints": version_hints(project),
        "repos": repo_inventory(research_root),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
