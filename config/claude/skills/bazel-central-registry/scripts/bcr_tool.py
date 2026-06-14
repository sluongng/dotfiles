#!/usr/bin/env python3
"""Utilities for Bazel Central Registry (BCR) module discovery and updates.

This script is intended for use by the bazel-central-registry skill.
"""

from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_REGISTRY_URL = "https://bcr.bazel.build/modules"

INCLUDE_RE = re.compile(r"include\(\s*([\"'])([^\"']+)\1\s*\)")
PRERELEASE_RE = re.compile(r"-(?:rc|alpha|beta|pre)\d*", re.IGNORECASE)


@dataclass
class Dep:
    name: str
    version: Optional[str]
    file: pathlib.Path
    call: str
    line: int


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
        path = stack.pop().resolve()
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
        i = match.end() - 1
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


def _line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _parse_named_calls(text: str, file_path: pathlib.Path, call_name: str, name_key: str) -> List[Dep]:
    deps: List[Dep] = []
    for start, _, block in _extract_calls(text, call_name):
        name = _find_kwarg_string(block, name_key)
        if not name:
            continue
        deps.append(
            Dep(
                name=name,
                version=_find_kwarg_string(block, "version"),
                file=file_path,
                call=call_name,
                line=_line_number_for_offset(text, start),
            )
        )
    return deps


def _parse_deps_from_text(text: str, file_path: pathlib.Path) -> List[Dep]:
    return _parse_named_calls(text, file_path, "bazel_dep", "name")


def _parse_overrides_from_text(text: str, file_path: pathlib.Path) -> List[Dep]:
    return _parse_named_calls(text, file_path, "single_version_override", "module_name")


def _parse_archive_overrides_from_text(text: str, file_path: pathlib.Path) -> List[Dep]:
    return _parse_named_calls(text, file_path, "archive_override", "module_name")


def _load_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _load_json_url(url: str) -> Dict[str, object]:
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def _download_text_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def _metadata_url(module: str, registry_url: str) -> str:
    return f"{registry_url.rstrip('/')}/{module}/metadata.json"


def _pick_latest_version(
    versions: Sequence[str],
    yanked_versions: Sequence[str],
    *,
    include_prerelease: bool = False,
    include_yanked: bool = False,
) -> Optional[str]:
    yanked = set(yanked_versions)
    usable = [version for version in versions if include_yanked or version not in yanked]
    if not usable:
        return None
    if include_prerelease:
        return usable[-1]
    stable = [version for version in usable if not PRERELEASE_RE.search(version)]
    return stable[-1] if stable else usable[-1]


def _latest_versions(
    names: Sequence[str],
    registry_url: str,
    *,
    include_prerelease: bool = False,
    include_yanked: bool = False,
) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for name in names:
        try:
            metadata = _load_json_url(_metadata_url(name, registry_url))
        except urllib.error.HTTPError:
            continue
        latest = _pick_latest_version(
            metadata.get("versions", []),
            (metadata.get("yanked_versions") or {}).keys(),
            include_prerelease=include_prerelease,
            include_yanked=include_yanked,
        )
        if latest:
            results[name] = latest
    return results


def _local_registry_modules_dir(registry_path: str) -> pathlib.Path:
    modules_dir = pathlib.Path(registry_path) / "modules"
    if not modules_dir.is_dir():
        raise SystemExit(f"Registry path does not contain a modules/ directory: {registry_path}")
    return modules_dir


def _local_metadata(registry_path: str, module: str) -> Dict[str, object]:
    path = _local_registry_modules_dir(registry_path) / module / "metadata.json"
    if not path.exists():
        raise SystemExit(f"Module not found in local registry: {module}")
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_module_files(files: Sequence[pathlib.Path]) -> Tuple[List[Dep], List[Dep], List[Dep]]:
    deps: List[Dep] = []
    overrides: List[Dep] = []
    archive_overrides: List[Dep] = []
    for path in files:
        text = _load_text(path)
        deps.extend(_parse_deps_from_text(text, path))
        overrides.extend(_parse_overrides_from_text(text, path))
        archive_overrides.extend(_parse_archive_overrides_from_text(text, path))
    return deps, overrides, archive_overrides


def _format_location(dep: Dep) -> str:
    return f"{dep.file}:{dep.line}"


def _format_effective_location(dep: Dep, source: Optional[Dep] = None) -> str:
    if source is None or source.file == dep.file and source.line == dep.line:
        return _format_location(dep)
    return f"dep {_format_location(dep)}; override {_format_location(source)}"


def _update_text(
    text: str,
    updates: Dict[str, str],
    call_name: str,
    key_name: str,
) -> Tuple[str, List[Update]]:
    if not updates:
        return text, []

    changes: List[Update] = []
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
        changes.append(
            Update(
                name=name,
                old_version=old_version,
                new_version=new_version,
                file=pathlib.Path(""),
                call=call_name,
            )
        )
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
    modules_dir = _local_registry_modules_dir(args.registry_path)
    query = args.query.lower()
    matches = [path.name for path in modules_dir.iterdir() if path.is_dir() and query in path.name.lower()]
    for name in sorted(matches):
        print(name)


def cmd_list_versions(args: argparse.Namespace) -> None:
    metadata = _local_metadata(args.registry_path, args.module)
    yanked = set((metadata.get("yanked_versions") or {}).keys())
    versions = metadata.get("versions", [])
    for version in versions:
        if args.include_yanked or version not in yanked:
            print(version)


def _load_module_files(args: argparse.Namespace) -> List[pathlib.Path]:
    root_module = pathlib.Path(args.module_file).resolve()
    workspace_root = pathlib.Path(args.workspace_root).resolve() if args.workspace_root else root_module.parent
    files = _collect_module_files(root_module, workspace_root)
    return sorted(files)


def cmd_list_deps(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps, _, _ = _scan_module_files(files)
    for dep in sorted(deps, key=lambda d: (d.name, str(d.file), d.line)):
        version = dep.version or "(no version)"
        print(f"{dep.name} {version}  # {_format_location(dep)}")


def cmd_deps_tree(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps, _, _ = _scan_module_files(files)

    roots: Dict[str, Optional[str]] = {}
    for dep in deps:
        if dep.name not in roots or (roots[dep.name] is None and dep.version):
            roots[dep.name] = dep.version

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
        module_url = f"{args.registry_url.rstrip('/')}/{name}/{version}/MODULE.bazel"
        try:
            text = _download_text_url(module_url)
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
    deps, overrides, _ = _scan_module_files(files)

    dep_names = {dep.name for dep in deps}
    override_names = {dep.name for dep in overrides}
    selected = set(args.module) if args.module else set(dep_names)
    if args.include_overrides:
        selected &= dep_names | override_names
    else:
        selected &= dep_names

    latest = _latest_versions(
        sorted(selected),
        args.registry_url,
        include_prerelease=args.include_prerelease,
        include_yanked=args.include_yanked,
    )

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
    latest = _latest_versions(
        args.module,
        args.registry_url,
        include_prerelease=args.include_prerelease,
        include_yanked=args.include_yanked,
    )
    for name in args.module:
        version = latest.get(name)
        if version:
            print(f"{name} {version}")
        else:
            print(f"{name} (not found)")


def cmd_check_upgrades(args: argparse.Namespace) -> None:
    files = _load_module_files(args)
    deps, overrides, archive_overrides = _scan_module_files(files)

    selected = set(args.module) if args.module else {dep.name for dep in deps}
    override_by_name = {dep.name: dep for dep in overrides if dep.version}
    archive_by_name = {dep.name: dep for dep in archive_overrides}

    effective_names = []
    for dep in deps:
        if dep.name not in selected:
            continue
        effective = override_by_name.get(dep.name, dep)
        if effective.version:
            effective_names.append(dep.name)

    latest = _latest_versions(
        sorted(set(effective_names)),
        args.registry_url,
        include_prerelease=args.include_prerelease,
        include_yanked=args.include_yanked,
    )

    upgradeable = []
    current = []
    custom = []
    missing = []

    for dep in deps:
        if dep.name not in selected:
            continue
        source = override_by_name.get(dep.name, dep)
        current_version = source.version
        if not current_version:
            reason = archive_by_name.get(dep.name)
            custom.append((dep, reason, reason.call if reason else "no-version"))
            continue
        latest_version = latest.get(dep.name)
        if not latest_version:
            missing.append((dep, source, current_version))
            continue
        marker = source.call if source.call != "bazel_dep" else ""
        entry = (dep, source, current_version, latest_version, marker)
        if current_version == latest_version:
            current.append(entry)
        else:
            upgradeable.append(entry)

    if upgradeable:
        print("UPGRADEABLE")
        for dep, source, current_version, latest_version, marker in upgradeable:
            suffix = f" ({marker})" if marker else ""
            print(f"{dep.name} {current_version} -> {latest_version}{suffix}  # {_format_effective_location(dep, source)}")

    if current:
        if upgradeable:
            print()
        print("CURRENT")
        for dep, source, current_version, _, marker in current:
            suffix = f" ({marker})" if marker else ""
            print(f"{dep.name} {current_version}{suffix}  # {_format_effective_location(dep, source)}")

    if custom:
        if upgradeable or current:
            print()
        print("CUSTOM")
        for dep, source, reason in custom:
            print(f"{dep.name} {reason}  # {_format_effective_location(dep, source)}")

    if missing:
        if upgradeable or current or custom:
            print()
        print("NOT_FOUND")
        for dep, source, current_version in missing:
            print(f"{dep.name} {current_version}  # {_format_effective_location(dep, source)}")


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

    latest = subparsers.add_parser("latest", help="Fetch latest versions from BCR metadata")
    latest.add_argument("--module", action="append", required=True, help="Module name (repeatable)")
    latest.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    latest.add_argument("--include-prerelease", action="store_true", help="Allow prerelease versions such as rc/beta")
    latest.add_argument("--include-yanked", action="store_true", help="Allow yanked versions")
    latest.set_defaults(func=cmd_latest)

    list_deps = subparsers.add_parser("list-deps", help="List direct bazel_dep entries from MODULE.bazel")
    list_deps.add_argument("--module-file", required=True, help="Path to root MODULE.bazel or an included module file")
    list_deps.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    list_deps.set_defaults(func=cmd_list_deps)

    deps_tree = subparsers.add_parser("deps-tree", help="Build a best-effort dependency tree")
    deps_tree.add_argument("--module-file", required=True, help="Path to root MODULE.bazel or an included module file")
    deps_tree.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    deps_tree.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    deps_tree.add_argument("--max-depth", type=int, default=2, help="Maximum tree depth")
    deps_tree.set_defaults(func=cmd_deps_tree)

    check_upgrades = subparsers.add_parser(
        "check-upgrades",
        help="Compare direct deps against live BCR metadata and report upgradeable modules",
    )
    check_upgrades.add_argument("--module-file", required=True, help="Path to root MODULE.bazel or an included module file")
    check_upgrades.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    check_upgrades.add_argument("--module", action="append", help="Only inspect named module(s)")
    check_upgrades.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    check_upgrades.add_argument("--include-prerelease", action="store_true", help="Allow prerelease versions such as rc/beta")
    check_upgrades.add_argument("--include-yanked", action="store_true", help="Allow yanked versions")
    check_upgrades.set_defaults(func=cmd_check_upgrades)

    upgrade = subparsers.add_parser("upgrade", help="Update bazel_dep versions to latest")
    upgrade.add_argument("--module-file", required=True, help="Path to root MODULE.bazel or an included module file")
    upgrade.add_argument("--workspace-root", help="Workspace root (defaults to MODULE.bazel directory)")
    upgrade.add_argument("--module", action="append", help="Only upgrade named module(s)")
    upgrade.add_argument("--include-overrides", action="store_true", help="Also update single_version_override entries")
    upgrade.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL)
    upgrade.add_argument("--include-prerelease", action="store_true", help="Allow prerelease versions such as rc/beta")
    upgrade.add_argument("--include-yanked", action="store_true", help="Allow yanked versions")
    upgrade.add_argument("--write", action="store_true", help="Write updates to files instead of printing diffs")
    upgrade.set_defaults(func=cmd_upgrade)

    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = _parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
