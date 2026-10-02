#!/usr/bin/env python3
"""Snapshot complete conversational transcripts and receipt successful retrospectives.

No event queue, model invocation, or patch application. A failed/incomplete review
retains its immutable snapshot and never advances the successful watermark.
"""
import argparse
import compression.zstd
from contextlib import contextmanager, closing
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

import observe

HERE = Path(__file__).resolve().parent


def read_json(path):
    if path.is_symlink():
        raise ValueError(f"refusing symlink state: {path}")
    return json.loads(path.read_text())


@contextmanager
def locked(state):
    observe.private_dir(state)
    for name in ("run", "history"):
        observe.private_dir(state / name)
    fd = os.open(state / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def watermark(args, through):
    path = args.state_dir / "retrospective/state.json"
    if path.exists():
        return read_json(path)["watermark"]
    completed = []
    for path in (args.state_dir / "history").glob("*.json"):
        result = read_json(path)
        if result.get("finished_at"):
            completed.append(observe.timestamp(result["finished_at"]))
    if completed:
        return observe.utc(min(through, max(completed)))
    # Aton process/terminal success predates ExecStartPost, so neither proves
    # that the old host-side retrospective receipt was successfully committed.
    return observe.utc(through - 7 * 86400)


def chats(args, since, through):
    # Root chat surfaces are not a fixed whitelist (for example MCP sessions).
    databases = sorted(args.codex_home.glob("state_*.sqlite"),
                       key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else -1)
    if not databases:
        raise FileNotFoundError("Codex state database missing")
    with closing(sqlite3.connect(databases[-1].resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        columns = {row[1] for row in conn.execute("PRAGMA table_info(threads)")}
        required = {"id", "rollout_path", "source", "updated_at"}
        if not required <= columns:
            raise ValueError("unsupported threads schema")
        fields = sorted(required) + [key for key in ("agent_path", "first_user_message", "cwd", "title") if key in columns]
        rows = [dict(row) for row in conn.execute("SELECT " + ",".join(fields) + " FROM threads ORDER BY updated_at,id")]
    excluded = observe.excluded_roots(args.state_dir)
    for row in rows:
        source = row["source"]
        if isinstance(source, str) and source.lstrip().startswith("{"):
            source = json.loads(source)
        if (float(row["updated_at"]) < math.floor(since) or row["id"] in excluded
                or isinstance(source, dict) and "subagent" in source
                or row.get("agent_path") not in (None, "", "/root")
                or observe.META_JOB.search(row.get("first_user_message", "") or "")):
            continue
        yield row


def transcript(thread, since, through):
    source = observe.resolve_rollout(thread["rollout_path"])
    opener = compression.zstd.open if source.suffix == ".zst" else open
    primary, fallback = [], []
    cwd, title = thread.get("cwd", ""), thread.get("title", "")
    excluded, has_primary, fork = False, False, {}
    with opener(source, "rt", encoding="utf-8") as stream:
        for line, raw in enumerate(stream, 1):
            if not raw.endswith("\n"):
                raise ValueError(f"incomplete rollout record: {source}:{line}")
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError(f"invalid rollout record: {source}:{line}")
            payload = record.get("payload", {})
            if not isinstance(payload, dict):
                raise ValueError(f"invalid rollout payload: {source}:{line}")
            kind = record.get("type")
            if kind == "session_meta":
                excluded |= isinstance(payload.get("source"), dict)
                excluded |= payload.get("agent_path") not in (None, "", "/root")
                cwd = payload.get("cwd", cwd)
                fork = {key: payload[key] for key in ("forked_from_id", "history_base") if key in payload}
            elif kind == "turn_context":
                cwd = payload.get("cwd", cwd)
            role, text, target = None, "", primary
            if kind == "response_item" and payload.get("type") == "message" and payload.get("role") in {"user", "assistant"}:
                has_primary = True
                if payload.get("role") == "assistant" and payload.get("channel") == "analysis":
                    continue
                role, text = payload["role"], observe.text_content(payload)
            elif kind == "event_msg" and payload.get("type") in {"user_message", "agent_message"}:
                role = "user" if payload["type"] == "user_message" else "assistant"
                text, target = payload.get("message", ""), fallback
            if role is None:
                continue
            if not isinstance(text, str):
                raise ValueError(f"invalid message text: {source}:{line}")
            if role == "user" and observe.META_JOB.search(text):
                excluded = True
            when = record.get("timestamp")
            if not when:
                raise ValueError(f"missing message timestamp: {source}:{line}")
            if since < observe.timestamp(when) <= through and not observe.ignored_message(text):
                target.append({"role": role, "timestamp": when, "text": text,
                               "phase": payload.get("phase"), "source": {"path": str(source), "line": line}})
    return None if excluded else {"id": thread["id"], "cwd": cwd, "title": title,
                                 "source": str(source), "fork": fork, "messages": primary if has_primary else fallback}


def private_text(path, text):
    # Fixed private run files, not model-selected paths.
    if path.is_symlink():
        raise ValueError(f"refusing symlink output: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(text)


def completed(state, manifest):
    ledger = read_json(state / "state.json") if (state / "state.json").exists() else {}
    return (ledger.get("last_run_id") == manifest["run_id"] and ledger.get("watermark") == manifest["through"]
            and (state / "history" / (manifest["run_id"] + ".json")).is_file())


def prepare(args):
    state = args.state_dir / "retrospective"
    manifest_path = state / "run/manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else None
    if manifest is None or completed(state, manifest):
        through = time.time()
        since = watermark(args, through)
        captured = []
        for thread in chats(args, observe.timestamp(since), through):
            value = transcript(thread, observe.timestamp(since), through)
            if value and value["messages"]:
                captured.append(value)
        run_id = observe.digest({"since": since, "through": observe.utc(through), "chats": captured})
        directory = state / "run" / run_id
        observe.private_dir(directory)
        entries = []
        for index, value in enumerate(captured):
            path = directory / f"chat-{index:06d}.json"
            observe.atomic_json(path, value, immutable=True)
            entries.append({**{k: v for k, v in value.items() if k != "messages"},
                            "path": str(path), "messages": len(value["messages"])})
        manifest = {"run_id": run_id, "since": since, "through": observe.utc(through),
                    "chats": entries, "counts": {"chats": len(entries), "messages": sum(x["messages"] for x in entries)},
                    "source_root": str(args.source_root)}
        observe.atomic_json(manifest_path, manifest)
    prompt = state / "run/prompt.md"
    schema = state / "run/result.schema.json"
    private_text(prompt, (HERE / "retrospective-prompt.md").read_text() + "\n\n## Snapshot manifest\n\n```json\n" + json.dumps(manifest, indent=2) + "\n```\n")
    observe.atomic_json(schema, read_json(HERE / "run.schema.json"))
    return {**manifest, "status": "ready", "prompt": str(prompt), "schema": str(schema), "manifest": str(manifest_path)}


def validate(value, schema):
    """Validate the small standard JSON Schema subset used by this CLI's result."""
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if "type" in schema and not isinstance(value, types[schema["type"]]):
        raise ValueError("result has invalid field type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("result has invalid enum value")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if not set(schema.get("required", [])) <= value.keys() or (schema.get("additionalProperties") is False and value.keys() - props.keys()):
            raise ValueError("result has missing or unknown fields")
        for key, item in value.items():
            if key in props:
                validate(item, props[key])
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise ValueError("result array length out of range")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise ValueError("result array contains duplicates")
        for item in value:
            validate(item, schema.get("items", {}))
    if isinstance(value, str) and (len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf"))
                                  or ("pattern" in schema and not re.search(schema["pattern"], value))):
        raise ValueError("result string invalid")


def finish(args):
    state = args.state_dir / "retrospective"
    manifest = read_json(state / "run/manifest.json")
    result = read_json(args.result)
    validate(result, read_json(state / "run/result.schema.json"))
    if result["outcome"] != "completed":
        raise ValueError("incomplete review retained; successful watermark not advanced")
    expected = {chat["id"] for chat in manifest["chats"]}
    reviewed = result["reviewed_chat_ids"]
    if result["run_id"] != manifest["run_id"] or len(set(reviewed)) != len(reviewed) or set(reviewed) != expected:
        raise ValueError("result must cover exactly all captured chats from this run")
    if completed(state, manifest):
        return read_json(state / "history" / (manifest["run_id"] + ".json"))
    for assessment in result["assessments"]:
        if not set(assessment["chat_ids"]) <= expected:
            raise ValueError("assessment cites unknown chat")
    changed = []
    for filename in result["changed_files"]:
        path = Path(filename)
        if not path.is_absolute() or not path.is_file():
            raise ValueError("changed file must be an existing absolute path")
        changed.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if not result["validation"].strip():
        raise ValueError("validation must describe completed checks")
    receipt_path = state / "history" / (manifest["run_id"] + ".json")
    receipt = {"status": "completed", "run_id": manifest["run_id"], "since": manifest["since"],
               "through": manifest["through"], "finished_at": observe.utc(), "counts": manifest["counts"],
               "result": result, "changed_files": changed}
    lines = ["# Codex retrospective", "", result["summary"], "",
             f"Window: {manifest['since']} through {manifest['through']}",
             f"Coverage: {len(expected)} chats, {manifest['counts']['messages']} conversational messages.",
             "", "## Changes", ""]
    lines.extend([f"- {item['path']} (sha256 {item['sha256']})" for item in changed] or ["No changes needed."])
    lines.extend(["", "## Validation", "", result["validation"], "", "## Assessments", ""])
    lines.extend(f"- {item['disposition']}: {item['rationale']} (chats: {', '.join(item['chat_ids'])})" for item in result["assessments"])
    private_text(args.state_dir / "latest.md", "\n".join(lines) + "\n")
    # A receipt left by an interrupted state commit is not yet canonical. A
    # retry may include additional edits; keep its report and receipt consistent.
    observe.atomic_json(receipt_path, receipt)
    observe.atomic_json(state / "state.json", {"watermark": manifest["through"], "last_run_id": manifest["run_id"]})
    return read_json(receipt_path)


def status(args):
    state = args.state_dir / "retrospective"
    ledger = read_json(state / "state.json") if (state / "state.json").exists() else {}
    manifest = read_json(state / "run/manifest.json") if (state / "run/manifest.json").exists() else None
    return {"watermark": ledger.get("watermark"), "status": "idle" if manifest is None else
            "completed" if completed(state, manifest) else "ready",
            "current": manifest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (("state-dir", "~/.local/state/codex-improve"), ("codex-home", "~/.codex"),
                          ("source-root", "~/.dotfiles"), ("aton-state-dir", "~/.local/state/codex-automaton")):
        parser.add_argument("--" + name, type=lambda p: Path(p).expanduser(), default=Path(default).expanduser())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    commands.add_parser("finish").add_argument("--result", required=True, type=Path)
    commands.add_parser("status")
    args = parser.parse_args(argv)
    try:
        with locked(args.state_dir / "retrospective"):
            result = {"prepare": prepare, "finish": finish, "status": status}[args.command](args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
