#!/usr/bin/env python3
"""Merge the tracked Claude settings baseline into ~/.claude/settings.json.

Claude Code writes machine-managed keys (e.g. enabledPlugins, theme) into
~/.claude/settings.json at runtime, so this file is merged rather than
symlinked: tracked baseline keys are enforced while any other existing keys are
preserved.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import shutil
import sys


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text().strip()
    if not text:
        return {}
    return json.loads(text)


def deep_merge(base: dict, overlay: dict) -> dict:
    """Overlay wins. Nested dicts merge; everything else is replaced."""
    out = dict(base)
    for key, value in overlay.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    args = parser.parse_args()

    if not args.baseline.exists():
        raise SystemExit(f"missing baseline settings: {args.baseline}")

    baseline = load_json(args.baseline)
    existing = load_json(args.target)
    merged = deep_merge(existing, baseline)

    if merged == existing:
        print(f"Settings already up to date at {args.target}")
        return 0

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = args.target.with_name(f"{args.target.name}.bak.{stamp}")
        shutil.copy2(args.target, backup)
        print(f"Backed up {args.target} to {backup}")

    args.target.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"Merged Claude settings baseline into {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
