#!/usr/bin/env python3
"""Find the earliest shared AC miss between two cache scorecard JSON files."""
import argparse
import datetime as dt
import json
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_ts(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _get_results(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(doc, dict):
        for key in ("results", "result", "cacheResults"):
            value = doc.get(key)
            if isinstance(value, list):
                return value
    return []


def _is_ac_miss(entry: Dict[str, Any]) -> bool:
    if entry.get("requestType") != "READ":
        return False
    status = entry.get("status") or {}
    code = status.get("code")
    if code is None:
        return False
    if isinstance(code, str):
        # Handle enum-style strings.
        return code.upper() == "NOT_FOUND"
    return code == 5  # gRPC NOT_FOUND


def _key(entry: Dict[str, Any]) -> Tuple[str, str]:
    return (entry.get("targetId", ""), entry.get("actionMnemonic", ""))


def _sort_key(entry: Dict[str, Any]) -> Tuple[int, str]:
    ts = _parse_ts(entry.get("startTime"))
    if ts is None:
        return (1, "")
    return (0, ts.isoformat())


def _first_shared(
    left: Iterable[Dict[str, Any]], right: Iterable[Dict[str, Any]]
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    right_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for entry in right:
        right_by_key.setdefault(_key(entry), entry)
    for entry in left:
        match = right_by_key.get(_key(entry))
        if match:
            return entry, match
    return None


def _print_result(label: str, entry: Dict[str, Any]) -> None:
    print(f"{label}:")
    print(json.dumps(entry, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find the earliest shared AC miss (target+mnemonic) between two scorecards."
    )
    parser.add_argument("old", help="Path to old invocation scorecard JSON")
    parser.add_argument("new", help="Path to new invocation scorecard JSON")
    args = parser.parse_args()

    old_doc = _load(args.old)
    new_doc = _load(args.new)

    old_results = [e for e in _get_results(old_doc) if _is_ac_miss(e)]
    new_results = [e for e in _get_results(new_doc) if _is_ac_miss(e)]

    old_results.sort(key=_sort_key)
    new_results.sort(key=_sort_key)

    match = _first_shared(old_results, new_results)
    if not match:
        print("No shared AC misses found for target+mnemonic.")
        return 1

    old_entry, new_entry = match
    print("Shared key:")
    print(f"  targetId: {old_entry.get('targetId')}")
    print(f"  actionMnemonic: {old_entry.get('actionMnemonic')}")
    print(f"  oldActionId: {old_entry.get('actionId')}")
    print(f"  newActionId: {new_entry.get('actionId')}")
    print(f"  oldStartTime: {old_entry.get('startTime')}")
    print(f"  newStartTime: {new_entry.get('startTime')}")
    _print_result("oldEntry", old_entry)
    _print_result("newEntry", new_entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
