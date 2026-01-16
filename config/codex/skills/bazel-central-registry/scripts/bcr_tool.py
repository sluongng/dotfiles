#!/usr/bin/env python3
"""Utilities for Bazel Central Registry (BCR) module discovery and updates.

This script is intended for use by the bazel-central-registry skill.
"""

from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from registry import UpstreamRegistry, RegistryClient, download
except Exception as exc:  # pragma: no cover - keeps CLI usable when registry.py changes
    raise SystemExit(f"Failed to import registry.py from {SCRIPT_DIR}: {exc}")

DEFAULT_REGISTRY_URL = "https://bcr.bazel.build/modules"

INCLUDE_RE = re.compile(r"include\(\s*([\"'])([^\"']+)\1\s*\)")


@dataclass
class Dep:
    name: str
    version: Optional[str]
    file: pathlib.Path
    call: str


@dataclass
class Update:
    name: str
    old_version: str
    new_version: str
    file: pathlib.Path
    call: str


def _resolve_label(label: str, workspace_root: pathlib.Path, current_dir: pathlib.Path) -> pathlib.Path:
    if label.startswith("//"):
        label = label[2:]
        if ":" in label:
            pkg, target = label.split(":", 1)
            if pkg:
                return workspace_root / pkg / target
            return workspace_root / target
        return workspace_root / label
    if label.startswith(":"):
        return current_dir / label[1:]
    return workspace_root / label


def _collect_module_files(root_module: pathlib.Path, workspace_root: pathlib.Path) -> List[pathlib.Path]:
    seen: Dict[pathlib.Path, None] = {}
    stack = [root_module]

    while stack:
        path = stack.pop()
        path = path.resolve()
        if path in seen:
            continue
        seen[path] = None
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for _, label in INCLUDE_RE.findall(content):
            include_path = _resolve_label(label, workspace_root, path.parent)
            if include_path.exists():
                stack.append(include_path)
    return list(seen.keys())


def _extract_calls(text: str, call_name: str) -> Iterable[Tuple[int, int, str]]:
    pattern = re.compile(rf"\b{re.escape(call_name)}\s*\(")
    idx = 0
    while True:
        match = pattern.search(text, idx)
        if not match:
            break
        start = match.start()
        i = match.end() - 1  # points at the opening paren
        depth = 0
        in_str: Optional[str] = None
        escape = False
        while i < len(text):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch in ("\"", "'"):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        yield start, end, text[start:end]
                        idx = end
                        break
            i += 1
        else:
            break


def _find_kwarg_string(block: str, key: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*([\"'])([^\"']+)\1", block)
    if not match:
        return None
    return match.group(2)


def _replace_version(block: str, new_version: str) -> str:
    pattern = re.compile(r"(\bversion\s*=\s*)([\"'])([^\"']+)(\2)")
    return pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{new_version}{m.group(2)}", block, count=1)


def _parse_deps_from_text(text: str, file_path: pathlib.Path) -> List[Dep]:
    deps: List[Dep] = []
    for _, _, block in _extract_calls(text, "bazel_dep"):
        name = _find_kwarg_string(block, "name")
        if not name:
            continue
        version = _find_kwarg_string(block, "version")
        deps.append(Dep(name=name, version=version, file=file_path, call="bazel_dep"))
    return deps


def _parse_overrides_from_text(text: str, file_path: pathlib.Path) -> List[Dep]:
    deps: List[Dep] = []
    for _, _, block in _extract_calls(text, "single_version_override"):
        name = _find_kwarg_string(block, "module_name")
        if not name:
            continue
        version = _find_kwarg_string(block, "version")
        if version:
            deps.append(Dep(name=name, version=version, file=file_path, call="single_version_override"))
    return deps


def _load_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _latest_versions(names: Sequence[str], registry_url: str) -> Dict[str, str]:
    registry = UpstreamRegistry(registry_url)
    results: Dict[str, str] = {}
    for name in names:
        snapshot = registry.get_latest_module_version(name)
        if snapshot:
            results[name] = snapshot.version
    return results


def _update_text(
    text: str,
    updates: Dict[str, str],
    call_name: str,
    key_name: str,
) -> Tuple[str, List[Update]]:
    if not updates:
        return text, []

    changes: List[Update] = []
    # Apply edits from the end of the file to keep indices stable.
    blocks = list(_extract_calls(text, call_name))
    for start, end, block in reversed(blocks):
        name = _find_kwarg_string(block, key_name)
        if not name or name not in updates:
            continue
        old_version = _find_kwarg_string(block, "version")
        if not old_version:
            continue
        new_version = updates[name]
        if old_version == new_version:
            continue
        new_block = _replace_version(block, new_version)
        text = text[:start] + new_block + text[end:]
        changes.append(Update(name=name, old_version=old_version, new_version=new_version, file=pathlib.Path(""), call=call_name))
    return text, changes


def _diff(old: str, new: str, path: pathlib.Path) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def cmd_find(args: argparse.Namespace) -> None:
    registry = RegistryClient(args.registry_path)
    modules = registry.get_all_modules()
    query = args.query.lower()
    matches = [m for m in modules if query in m.lower()]
    for name in sorted(matches):
        print(name)


def cmd_list_versions(args: argparse.Namespace) -> None:
    registry = RegistryClient(args.registry_path)
    versions = registry.get_module_versions(args.module, include_yanked=args.include_yanked)
    for _, version in versions:
        print(version)


def _load_module_files(args: argparse.Namespace) -> List[pathlib.Path]:
    root_module = pathlib.Path(args.module_file).resolve()
    workspace_root = pathlib.Path(args.workspace_root).resolve() if args.workspace_root else root_module.parent
    files = _collect_module_files(root_module, workspace_root)
    return sorted(files)


def cmd_list_deps(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps: List[Dep] = []
    for path in files:
        text = _load_text(path)
        deps.extend(_parse_deps_from_text(text, path))
    for dep in sorted(deps, key=lambda d: d.name):
        version = dep.version or "(no version)"
        print(f"{dep.name} {version}  # {dep.file}")


def cmd_deps_tree(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps: List[Dep] = []
    for path in files:
        text = _load_text(path)
        deps.extend(_parse_deps_from_text(text, path))

    roots: Dict[str, Optional[str]] = {}
    for dep in deps:
        if dep.name not in roots or (roots[dep.name] is None and dep.version):
            roots[dep.name] = dep.version
    registry_url = args.registry_url

    visited: Dict[Tuple[str, str], None] = {}

    def walk(name: str, version: Optional[str], depth: int) -> List[str]:
        indent = "  " * depth
        label = f"{name}@{version}" if version else name
        lines = [f"{indent}- {label}"]
        if version is None or depth >= args.max_depth:
            return lines
        key = (name, version)
        if key in visited:
            lines[-1] += " (visited)"
            return lines
        visited[key] = None
        module_url = f"{registry_url}/{name}/{version}/MODULE.bazel"
        try:
            content = download(module_url)
        except Exception:
            return lines
        try:
            text = content.decode("utf-8")
        except Exception:
            return lines
        child_deps = _parse_deps_from_text(text, pathlib.Path(module_url))
        for child in sorted(child_deps, key=lambda d: d.name):
            lines.extend(walk(child.name, child.version, depth + 1))
        return lines

    for name, version in sorted(roots.items()):
        for line in walk(name, version, 0):
            print(line)


def cmd_upgrade(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps: List[Dep] = []
    overrides: List[Dep] = []
    for path in files:
        text = _load_text(path)
        deps.extend(_parse_deps_from_text(text, path))
        if args.include_overrides:
            overrides.extend(_parse_overrides_from_text(text, path))

    selected = {d.name for d in deps}
    if args.module:
        selected = {d.name for d in deps if d.name in set(args.module)}
    if args.include_overrides:
        selected.update({d.name for d in overrides})

    latest = _latest_versions(sorted(selected), args.registry_url)

    for path in files:
        text = _load_text(path)
        new_text = text
        changes: List[Update] = []
        new_text, dep_changes = _update_text(new_text, latest, "bazel_dep", "name")
        changes.extend(dep_changes)
        if args.include_overrides:
            new_text, override_changes = _update_text(new_text, latest, "single_version_override", "module_name")
            changes.extend(override_changes)

        if not changes:
            continue

        if args.write:
            _write_text(path, new_text)
        else:
            diff = _diff(text, new_text, path)
            if diff:
                print(diff, end="")


def cmd_latest(args: argparse.Namespace) -> None:
    latest = _latest_versions(args.module, args.registry_url)
    for name in args.module:
        version = latest.get(name)
        if version:
            print(f"{name} {version}")
        else:
            print(f"{name} (not found)")


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bazel Central Registry helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    find = subparsers.add_parser("find", help="Find modules in a local registry clone")
    find.add_argument("--registry-path", required=True, help="Path to bazel-central-registry checkout")
    find.add_argument("--query", required=True, help="Substring to match")
    find.set_defaults(func=cmd_find)

    list_versions = subparsers.add_parser("list-versions", help="List versions for a module in a local registry clone")
    list_versions.add_argument("--registry-path", required=True, help="Path to bazel-central-registry checkout")
    list_versions.add_argument("--module", required=True, help="Module name")
    list_versions.add_argument("--include-yanked", action="store_true", help="Include yanked versions")
    list_versions.set_defaults(func=cmd_list_versions)

    latest = subparsers.add_parser("latest", help="Fetch latest versions from BCR")
    latest.add_argument("--module", action="append", required=True, help="Module name (repeatable)")
    latest.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    latest.set_defaults(func=cmd_latest)

    list_deps = subparsers.add_parser("list-deps", help="List direct bazel_dep entries from MODULE.bazel")
    list_deps.add_argument("--module-file", required=True, help="Path to root MODULE.bazel")
    list_deps.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    list_deps.set_defaults(func=cmd_list_deps)

    deps_tree = subparsers.add_parser("deps-tree", help="Build a best-effort dependency tree")
    deps_tree.add_argument("--module-file", required=True, help="Path to root MODULE.bazel")
    deps_tree.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    deps_tree.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    deps_tree.add_argument("--max-depth", type=int, default=2, help="Maximum tree depth")
    deps_tree.set_defaults(func=cmd_deps_tree)

    upgrade = subparsers.add_parser("upgrade", help="Update bazel_dep versions to latest")
    upgrade.add_argument("--module-file", required=True, help="Path to root MODULE.bazel")
    upgrade.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    upgrade.add_argument("--module", action="append", help="Only upgrade named module(s)")
    upgrade.add_argument("--include-overrides", action="store_true", help="Also update single_version_override entries")
    upgrade.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    upgrade.add_argument("--write", action="store_true", help="Write updates to files instead of printing diffs")
    upgrade.set_defaults(func=cmd_upgrade)

    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = _parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
