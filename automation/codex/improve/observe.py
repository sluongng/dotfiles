#!/usr/bin/env python3
"""Incrementally collect private, untrusted Codex evidence; never invoke a model.

Legacy fork prefixes have no universally reliable native-message boundary. Such
root rollouts are conservatively excluded, as are child and meta-job threads.
Event IDs deliberately omit storage paths, ordinals and timestamps: copied
messages and migration from JSONL to JSONL.zst must not create fresh evidence.
Repeated identical text within one native turn is therefore one observation.
"""
from __future__ import annotations

import argparse
import compression.zstd
from contextlib import closing
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import tomllib

ROOT_SOURCES = {"cli", "vscode", "exec"}
META_JOB = re.compile(r"(?:Aton\s+)?Automation\s+ID:\s*(codex-improve|codex-observe|codex-improvement-check)\b", re.I)
AUTOMATION = re.compile(r"(?:Aton\s+)?Automation\s+ID:", re.I)
INJECTED = ("# AGENTS.md instructions", "<environment_context>", "<permissions instructions>",
            "<skills_instructions>", "<available_skills>", "<recommended_plugins>",
            "<subagent_notification>", "<INSTRUCTIONS>")
MAX_TEXT = 16000


def utc(value: float | None = None) -> str:
    return dt.datetime.fromtimestamp(time.time() if value is None else value, dt.UTC).isoformat().replace("+00:00", "Z")


def timestamp(value: str) -> float:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def private_dir(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("state directory must not be a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def excluded_roots(state_dir: Path) -> set[str]:
    """Keep private thread identities in local state, never tracked source."""
    path = state_dir / "excluded-roots.json"
    if not path.exists():
        return set()
    value = json.loads(path.read_text())
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item)
        for item in value
    ):
        raise ValueError("excluded-roots.json must contain a list of thread IDs")
    return set(value)


def atomic_json(path: Path, value, *, immutable: bool = False) -> bool:
    """Atomic publication; existing immutable events are never overwritten."""
    fd, tmp = tempfile.mkstemp(prefix=".observe-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if immutable:
            try:
                os.link(tmp, path)
            except FileExistsError:
                return False
        else:
            os.replace(tmp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def event(thread_id: str, kind: str, text: str, when: str, source: dict,
          metadata: dict | None = None, *, turn_id: str = "") -> dict:
    identity = [thread_id, kind, turn_id, text]
    return {"id": digest(identity), "root_id": thread_id, "thread_id": thread_id,
            "timestamp": when, "kind": kind, "text": text[:MAX_TEXT], "source": source,
            "source_text_truncated": len(text) > MAX_TEXT, "original_text_chars": len(text),
            "metadata": metadata or {}}


def inventory(codex_home: Path) -> list[dict]:
    candidates = sorted(codex_home.glob("state_*.sqlite"),
                        key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else -1)
    if not candidates:
        raise FileNotFoundError("Codex state database missing")
    with closing(sqlite3.connect(candidates[-1].resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        columns = {row[1] for row in conn.execute("PRAGMA table_info(threads)")}
        required = {"id", "rollout_path", "source", "updated_at"}
        if not required <= columns:
            raise ValueError("unsupported threads schema")
        optional = [key for key in ("first_user_message", "created_at", "agent_path", "originator") if key in columns]
        fields = ",".join(sorted(required) + optional)
        return [dict(row) for row in conn.execute(f"SELECT {fields} FROM threads WHERE source IN ('cli','vscode','exec') ORDER BY updated_at,id")]


def resolve_rollout(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_file():
        return path
    compressed = Path(str(path) + ".zst")
    if compressed.is_file():
        return compressed
    raise FileNotFoundError("rollout missing")


def signature(path: Path) -> dict:
    info = path.stat()
    return {"path": str(path), "size": info.st_size, "mtime_ns": info.st_mtime_ns,
            "inode": info.st_ino, "device": info.st_dev}


def text_content(payload: dict) -> str:
    content = payload.get("content", [])
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and isinstance(c.get("text"), str))


def ignored_message(text: str) -> bool:
    return not text.strip() or text.lstrip().startswith(INJECTED)


def read_batch(path: Path, thread: dict, prior: dict, cutoff: float, *,
               max_lines: int, max_bytes: int) -> tuple[list[dict], dict, bool]:
    """Checkpoint only after the whole batch parses. Replay safely after rewrites.

    Plain append resumes with a byte offset after validating its last-line hash.
    Compressed files and changed inodes replay by logical line ordinal plus a
    bookmark hash. A mismatching bookmark restarts from zero, with event dedup.
    """
    sig = signature(path)
    oldsig = prior.get("signature", {})
    offset = prior.get("offset", 0)
    ordinal = prior.get("line", 0)
    context = dict(prior.get("context", {}))
    opener = compression.zstd.open if path.suffix == ".zst" else open
    with opener(path, "rb") as handle:
        if offset and path.suffix != ".zst" and oldsig.get("inode") == sig["inode"] and oldsig.get("device") == sig["device"] and sig["size"] >= offset:
            bookmark = prior.get("bookmark", "")
            length = prior.get("bookmark_bytes", 0)
            handle.seek(max(0, offset - length))
            if hashlib.sha256(handle.read(length)).hexdigest() != bookmark:
                offset = ordinal = 0
                context = {}
            handle.seek(offset)
        elif ordinal:
            # Compression changes bytes, not the logical record stream.
            last = b""
            for _ in range(ordinal):
                last = handle.readline(max_bytes + 1)
                if len(last) > max_bytes:
                    raise ValueError("rollout record exceeds batch byte limit")
                if not last:
                    break
            if hashlib.sha256(last).hexdigest() != prior.get("bookmark"):
                handle.seek(0)
                offset = ordinal = 0
                context = {}
            else:
                offset = handle.tell()
        events = []
        consumed = 0
        last_line = b""
        eof = False
        for _ in range(max_lines):
            begin = handle.tell()
            raw = handle.readline(max_bytes + 1)
            if not raw:
                eof = True
                break
            if len(raw) > max_bytes:
                raise ValueError("rollout record exceeds batch byte limit")
            if not raw.endswith(b"\n"):
                # Active writer has not completed this record. Retry after growth.
                handle.seek(begin)
                eof = True
                break
            obj = json.loads(raw)
            if not isinstance(obj, dict) or not isinstance(obj.get("payload", {}), dict):
                raise ValueError("invalid rollout record")
            ordinal += 1
            consumed += len(raw)
            last_line = raw
            payload = obj.get("payload", {})
            kind = obj.get("type")
            when = obj.get("timestamp", "")
            if kind == "session_meta":
                # Fail closed on copied/reference-based user forks and children.
                context["excluded_fork"] = bool(payload.get("forked_from_id") or payload.get("history_base"))
                context["excluded_child"] = isinstance(payload.get("source"), dict)
                if context["excluded_fork"] or context["excluded_child"]:
                    # No provable native boundary: do not traverse its copied prefix.
                    eof = True
                    break
            if kind == "turn_context":
                context["turn_id"] = payload.get("turn_id", "")
            text = ""
            output_kind = None
            if kind == "event_msg" and payload.get("type") == "user_message":
                text = payload.get("message", "")
                output_kind = "user_message"
            elif kind == "response_item" and payload.get("type") == "message":
                if payload.get("role") == "user":
                    text = text_content(payload)
                    output_kind = "user_message"
                elif payload.get("role") == "assistant" and payload.get("phase") == "final_answer":
                    text = text_content(payload)
                    output_kind = "task_outcome"
            elif kind == "event_msg" and payload.get("type") == "item_completed":
                item = payload.get("item", {})
                if isinstance(item, dict) and item.get("type") in {"user_message", "userMessage", "UserMessage"}:
                    text = text_content(item)
                    output_kind = "user_message"
                elif isinstance(item, dict) and item.get("type") in {"agent_message", "agentMessage", "AgentMessage"} and item.get("phase") == "final_answer":
                    text = text_content(item)
                    output_kind = "task_outcome"
            elif kind == "event_msg" and payload.get("type") in {"task_complete", "turn_complete"}:
                text = payload.get("last_agent_message") or ""
                output_kind = "task_outcome"
            if not isinstance(text, str):
                raise ValueError("invalid message text")
            if output_kind == "user_message":
                if META_JOB.search(text):
                    context["meta_job"] = True
                if AUTOMATION.search(text):
                    context["automation"] = True
            if text and output_kind and not ignored_message(text) and not any(context.get(x) for x in ("excluded_fork", "excluded_child", "meta_job")):
                if timestamp(when) >= cutoff:
                    automatic = bool(context.get("automation") or AUTOMATION.search(thread.get("first_user_message", "")))
                    metadata = {"automation": automatic, "human": not automatic,
                                "turn_id": context.get("turn_id", ""), "untrusted": True}
                    if output_kind == "user_message" and automatic:
                        metadata["original_kind"] = output_kind
                        output_kind = "task_outcome"
                    events.append(event(thread["id"], output_kind, text, when,
                                        {"path": str(path), "line": ordinal}, metadata,
                                        turn_id=context.get("turn_id", "")))
            if consumed >= max_bytes:
                break
        offset = handle.tell()
        updated = {"signature": sig, "offset": offset, "line": ordinal, "context": context,
                   "complete": eof, "updated_at": thread["updated_at"]}
        if last_line:
            updated.update(bookmark=hashlib.sha256(last_line).hexdigest(), bookmark_bytes=len(last_line))
        else:
            updated.update(bookmark=prior.get("bookmark", ""), bookmark_bytes=prior.get("bookmark_bytes", 0))
        if context.get("meta_job"):
            events = []
        return events, updated, eof


def health(codex_home: Path, source_root: Path) -> dict:
    """Only allowlisted model/effort fields are exposed; never config contents."""
    findings = []
    snapshots = {}
    for label, path in (("source", source_root / "config/codex/config.toml"), ("rendered", codex_home / "config.toml")):
        try:
            data = tomllib.loads(path.read_text())
            snapshots[label] = {key: data.get(key) for key in ("model", "model_reasoning_effort")}
        except (OSError, ValueError) as exc:
            findings.append({"check": "config", "side": label, "error": type(exc).__name__})
    if len(snapshots) == 2 and snapshots["source"] != snapshots["rendered"]:
        findings.append({"check": "model_drift", **snapshots})
    role_count = 0
    source_roles = source_root / "config/codex/agents"
    for expected in sorted(source_roles.glob("*.toml")):
        role_count += 1
        live = codex_home / "agents" / expected.name
        try:
            a, b = (tomllib.loads(p.read_text()) for p in (expected, live))
            keys = ("model", "model_reasoning_effort", "sandbox_mode")
            if any(a.get(k) != b.get(k) for k in keys):
                findings.append({"check": "role_drift", "role": expected.stem})
            if live.is_symlink():
                findings.append({"check": "role_symlink", "role": expected.stem})
        except (OSError, ValueError) as exc:
            findings.append({"check": "role", "role": expected.stem, "error": type(exc).__name__})
    for tree in ("agents", "skills"):
        directory = codex_home / tree
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_symlink() and not path.exists():
                    findings.append({"check": "broken_symlink", "tree": tree, "name": path.name})
    return {"status": "ok" if not findings else "attention", "findings": findings,
            "models": snapshots, "roles_checked": role_count}


def collect(args, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    state_dir, codex_home, source_root = map(lambda p: Path(p).expanduser(), (args.state_dir, args.codex_home, args.source_root))
    private_dir(state_dir)
    private_dir(state_dir / "events")
    lock_path = state_dir / "collector.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        os.fchmod(lock.fileno(), 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "events_created": 0}
        state_file = state_dir / "collector-state.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {"version": 1, "cutoff": now - args.bootstrap_days * 86400, "threads": {}}
        state.setdefault("attempts", {})
        counts = {"threads_read": 0, "events_created": 0, "threads_unchanged": 0, "threads_excluded": 0, "pending": 0}
        failures = []
        excluded = excluded_roots(state_dir) | set(args.exclude_root)
        try:
            rows = inventory(codex_home)
        except (OSError, sqlite3.Error, ValueError) as exc:
            rows = []
            failures.append({"check": "database", "error": type(exc).__name__})
        # Incomplete and least-recently-attempted threads get fair bounded catch-up.
        rows.sort(key=lambda row: max(state["threads"].get(row["id"], {}).get("attempted_at", 0), state["attempts"].get(row["id"], 0)))
        for row in rows:
            tid = row["id"]
            prior = state["threads"].get(tid, {})
            if tid in excluded or META_JOB.search(row.get("first_user_message", "")) or row.get("agent_path") or any(prior.get("context", {}).get(key) for key in ("excluded_fork", "excluded_child", "meta_job")):
                counts["threads_excluded"] += 1
                continue
            if not prior and row["updated_at"] < state["cutoff"]:
                continue
            try:
                path = resolve_rollout(row["rollout_path"])
                sig = signature(path)
                if prior.get("complete") and prior.get("signature") == sig:
                    counts["threads_unchanged"] += 1
                    continue
                if counts["threads_read"] >= args.max_threads:
                    counts["pending"] += 1
                    continue
                counts["threads_read"] += 1
                state["attempts"][tid] = now
                events, updated, complete = read_batch(path, row, prior, state["cutoff"], max_lines=args.max_lines, max_bytes=args.max_bytes)
                for item in events:
                    counts["events_created"] += atomic_json(state_dir / "events" / (item["id"] + ".json"), item, immutable=True)
                updated["attempted_at"] = now
                state["threads"][tid] = updated
                state["attempts"].pop(tid, None)
                if not complete:
                    counts["pending"] += 1
                if updated["context"].get("excluded_fork"):
                    counts["threads_excluded"] += 1
            except (OSError, ValueError, EOFError, compression.zstd.ZstdError) as exc:
                failures.append({"thread_id": tid, "error": type(exc).__name__})
                # Neither read cursor nor success acknowledgement advances on error.
        check = health(codex_home, source_root)
        if check["findings"]:
            item = event("collector-health", "health", "Codex source/render model or role health needs attention.", utc(now),
                         {"path": str(codex_home / "config.toml"), "line": 1}, check)
            # Distinct deterministic findings must not collapse into one health event.
            item["id"] = digest(["health", check])
            counts["events_created"] += atomic_json(state_dir / "events" / (item["id"] + ".json"), item, immutable=True)
        observation = {"version": 1, "timestamp": utc(now), "status": "attention" if failures or check["findings"] else "ok",
                       "counts": counts, "health": check, "errors": failures, "bootstrap_cutoff": utc(state["cutoff"])}
        atomic_json(state_file, state)
        atomic_json(state_dir / "observation.json", observation)
        return {"status": observation["status"], **counts, "errors": len(failures)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir", default="~/.local/state/codex-improve")
    p.add_argument("--codex-home", default="~/.codex")
    p.add_argument("--source-root", default="~/.dotfiles")
    p.add_argument("--exclude-root", action="append", default=[])
    p.add_argument("--bootstrap-days", type=int, default=7)
    p.add_argument("--max-threads", type=int, default=32)
    p.add_argument("--max-lines", type=int, default=20000)
    p.add_argument("--max-bytes", type=int, default=16 * 1024 * 1024)
    return p


def main() -> int:
    p = parser()
    args = p.parse_args()
    if min(args.bootstrap_days, args.max_threads, args.max_lines, args.max_bytes) < 1:
        p.error("bootstrap and batch limits must be positive")
    try:
        result = collect(args)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "error", "error": type(exc).__name__}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
