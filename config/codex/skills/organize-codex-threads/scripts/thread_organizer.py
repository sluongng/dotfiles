#!/usr/bin/env python3
"""Collect bounded Codex thread excerpts and apply validated thread names."""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_MAX_TURNS = 5
DEFAULT_MAX_NAME_COLUMNS = 48
MAX_PROMPT_CHARS = 600
MAX_RESPONSE_CHARS = 900
NONINTERACTIVE_SOURCE_KINDS = ["exec", "appServer", "unknown"]
GENERATED_THREAD_SOURCES = {"automation", "memory_consolidation", "subagent"}
AUTOMATION_PROMPT_PREFIX = "Aton automation ID:"


class RpcError(RuntimeError):
    pass


class AppServerClient:
    def __init__(self, codex_bin: str) -> None:
        self._process = subprocess.Popen(
            [codex_bin, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._next_id = 1
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex_thread_organizer",
                    "title": "Codex Thread Organizer",
                    "version": "1.0.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self.notify("initialized")

    def _send(self, message: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise RpcError("app-server stdin is unavailable")
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        self._send(message)

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"method": method, "id": request_id, "params": params})
        if self._process.stdout is None:
            raise RpcError("app-server stdout is unavailable")
        while True:
            line = self._process.stdout.readline()
            if not line:
                code = self._process.poll()
                raise RpcError(f"app-server exited before replying to {method} (status {code})")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RpcError(f"app-server emitted invalid JSON: {exc}") from exc
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise RpcError(f"{method} failed: {error}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise RpcError(f"{method} returned a non-object result")
            return result

    def close(self) -> None:
        if self._process.stdin is not None:
            self._process.stdin.close()
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)

    def __enter__(self) -> "AppServerClient":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def truncate_text(text: str, max_chars: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    os.chmod(path, 0o600)


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def list_thread_page_set(
    client: AppServerClient,
    source_kinds: list[str] | None,
) -> list[dict[str, Any]]:
    threads: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {
            "cursor": cursor,
            "limit": 100,
            "sortKey": "recency_at",
            "sortDirection": "desc",
            "archived": False,
            "useStateDbOnly": True,
        }
        if source_kinds is not None:
            params["sourceKinds"] = source_kinds
        result = client.request(
            "thread/list",
            params,
        )
        data = result.get("data", [])
        if not isinstance(data, list):
            raise RpcError("thread/list returned invalid data")
        threads.extend(thread for thread in data if isinstance(thread, dict))
        cursor = result.get("nextCursor")
        if not cursor:
            return threads


def list_threads(client: AppServerClient) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    # Omitted sourceKinds includes all interactive sources, including custom
    # first-party clients. A second query adds non-interactive user-resumable
    # sources without admitting subagents.
    for source_kinds in (None, NONINTERACTIVE_SOURCE_KINDS):
        for thread in list_thread_page_set(client, source_kinds):
            thread_id = thread.get("id")
            if isinstance(thread_id, str):
                by_id[thread_id] = thread
    return sorted(by_id.values(), key=timestamp_for_thread, reverse=True)


def list_turns(
    client: AppServerClient,
    thread_id: str,
    *,
    limit: int,
    sort_direction: str,
) -> list[dict[str, Any]]:
    result = client.request(
        "thread/turns/list",
        {
            "threadId": thread_id,
            "limit": limit,
            "sortDirection": sort_direction,
            "itemsView": "summary",
        },
    )
    data = result.get("data", [])
    if not isinstance(data, list):
        raise RpcError("thread/turns/list returned invalid data")
    return [turn for turn in data if isinstance(turn, dict)]


def prompt_from_item(item: dict[str, Any]) -> str:
    parts = []
    for content in item.get("content", []):
        if isinstance(content, dict) and content.get("type") == "text":
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return truncate_text("\n".join(parts), MAX_PROMPT_CHARS)


def dialogue_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current_prompt = ""
    last_response = ""
    final_response = ""

    def finish_record() -> None:
        nonlocal current_prompt, last_response, final_response
        if current_prompt:
            records.append(
                {
                    "user_prompt": current_prompt,
                    "model_response": final_response or last_response,
                }
            )
        current_prompt = ""
        last_response = ""
        final_response = ""

    for turn in turns:
        for item in turn.get("items", []):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "userMessage":
                finish_record()
                current_prompt = prompt_from_item(item)
            elif item_type == "agentMessage" and current_prompt:
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                response = truncate_text(text, MAX_RESPONSE_CHARS)
                last_response = response
                if item.get("phase") == "final_answer":
                    final_response = response
    finish_record()
    return records


def recent_dialogue(
    client: AppServerClient,
    thread_id: str,
) -> tuple[list[dict[str, str]], bool]:
    try:
        result = client.request(
            "thread/read",
            {"threadId": thread_id, "includeTurns": True},
        )
        thread = result.get("thread")
        turns = thread.get("turns", []) if isinstance(thread, dict) else []
        if not isinstance(turns, list):
            raise RpcError("thread/read returned invalid turns")
        return dialogue_from_turns(
            [turn for turn in turns if isinstance(turn, dict)]
        ), False
    except RpcError:
        # Paginated histories cannot be materialized by thread/read. Summary
        # fallback still provides the first user and final agent message for
        # each of the five latest turns, but cannot preserve same-turn steers.
        turns = list_turns(
            client,
            thread_id,
            limit=DEFAULT_MAX_TURNS,
            sort_direction="desc",
        )
        turns.reverse()
        return dialogue_from_turns(turns), True


def timestamp_for_thread(thread: dict[str, Any]) -> int:
    for key in ("recencyAt", "updatedAt", "createdAt"):
        value = thread.get(key)
        if isinstance(value, int):
            return value
    return 0


def is_automation_thread(
    thread: dict[str, Any], dialogue: list[dict[str, str]]
) -> bool:
    if thread.get("threadSource") == "automation":
        return True
    if not dialogue:
        return False
    return dialogue[0].get("user_prompt", "").startswith(AUTOMATION_PROMPT_PREFIX)


def collect_command(args: argparse.Namespace) -> int:
    cutoff = None if args.all else utc_now() - dt.timedelta(hours=args.since_hours)
    skipped = {
        "before_cutoff": 0,
        "generated_thread": 0,
        "automation_without_user_followup": 0,
        "without_user_prompt": 0,
        "read_error": 0,
        "summary_fallback": 0,
    }
    candidates = []
    with AppServerClient(args.codex_bin) as client:
        for thread in list_threads(client):
            timestamp = timestamp_for_thread(thread)
            if cutoff is not None and timestamp < int(cutoff.timestamp()):
                skipped["before_cutoff"] += 1
                continue

            thread_source = thread.get("threadSource")
            if thread_source in GENERATED_THREAD_SOURCES - {"automation"}:
                skipped["generated_thread"] += 1
                continue

            thread_id = thread.get("id")
            if not isinstance(thread_id, str):
                skipped["read_error"] += 1
                continue
            try:
                dialogue, used_summary_fallback = recent_dialogue(client, thread_id)
                if used_summary_fallback:
                    skipped["summary_fallback"] += 1
                if is_automation_thread(thread, dialogue):
                    dialogue = dialogue[1:]
                    if not dialogue:
                        skipped["automation_without_user_followup"] += 1
                        continue
            except RpcError:
                skipped["read_error"] += 1
                continue

            recent_turns = dialogue[-args.max_turns :]
            if not recent_turns:
                skipped["without_user_prompt"] += 1
                continue

            candidates.append(
                {
                    "thread_id": thread_id,
                    "current_name": thread.get("name"),
                    "cwd": thread.get("cwd"),
                    "source": thread.get("source"),
                    "thread_source": thread_source,
                    "recency_at": timestamp,
                    "recent_turns": recent_turns[-args.max_turns :],
                }
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now().isoformat(),
        "cutoff": cutoff.isoformat() if cutoff is not None else None,
        "max_turns": args.max_turns,
        "threads": candidates,
        "skipped": skipped,
    }
    output = Path(args.output).expanduser().resolve()
    write_private_json(output, payload)
    batch_count = 0
    if args.batch_dir:
        batch_dir = Path(args.batch_dir).expanduser().resolve()
        batch_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(batch_dir, 0o700)
        for stale_batch in batch_dir.glob("batch-*.json"):
            stale_batch.unlink()
        for start in range(0, len(candidates), args.batch_size):
            batch_count += 1
            write_private_json(
                batch_dir / f"batch-{batch_count:04d}.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "batch": batch_count,
                    "threads": candidates[start : start + args.batch_size],
                },
            )
    print(
        json.dumps(
            {
                "output": str(output),
                "candidate_count": len(candidates),
                "batch_count": batch_count,
                "skipped": skipped,
            },
            sort_keys=True,
        )
    )
    return 0


def normalized_name(value: Any, max_columns: int) -> str:
    if not isinstance(value, str):
        raise ValueError("name must be a string")
    name = re.sub(r"\s+", " ", value).strip()
    if not name:
        raise ValueError("name must not be empty")
    if any(unicodedata.category(char).startswith("C") for char in name):
        raise ValueError("name must not contain control characters")
    if display_width(name) > max_columns:
        raise ValueError(f"name exceeds {max_columns} display columns")
    words = name.split()
    if not 3 <= len(words) <= 9:
        raise ValueError("name must contain 3-9 words")
    if name[-1] in ".!?":
        raise ValueError("name must not end with punctuation")
    return name


def apply_command(args: argparse.Namespace) -> int:
    candidates_payload = load_json_object(Path(args.candidates))
    proposals_payload = load_json_object(Path(args.proposals))
    if candidates_payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported candidates schema_version")
    if proposals_payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported proposals schema_version")

    candidate_rows = candidates_payload.get("threads")
    proposal_rows = proposals_payload.get("proposals")
    if not isinstance(candidate_rows, list) or not isinstance(proposal_rows, list):
        raise ValueError("candidates threads and proposals must be arrays")
    candidates = {
        row.get("thread_id"): row
        for row in candidate_rows
        if isinstance(row, dict) and isinstance(row.get("thread_id"), str)
    }

    validated: list[tuple[str, str, str | None]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for row in proposal_rows:
        if not isinstance(row, dict):
            raise ValueError("each proposal must be an object")
        thread_id = row.get("thread_id")
        if not isinstance(thread_id, str) or thread_id not in candidates:
            raise ValueError(f"proposal thread id is not in candidates: {thread_id!r}")
        if thread_id in seen_ids:
            raise ValueError(f"duplicate proposal for thread {thread_id}")
        name = normalized_name(row.get("name"), args.max_name_columns)
        folded_name = name.casefold()
        if folded_name in seen_names:
            raise ValueError(f"duplicate proposed name: {name}")
        seen_ids.add(thread_id)
        seen_names.add(folded_name)
        current_name = candidates[thread_id].get("current_name")
        validated.append(
            (thread_id, name, current_name if isinstance(current_name, str) else None)
        )
    missing_ids = set(candidates) - seen_ids
    if missing_ids:
        raise ValueError(
            f"proposals are missing {len(missing_ids)} candidate thread(s)"
        )

    renamed = []
    unchanged = []
    failures = []
    with AppServerClient(args.codex_bin) as client:
        existing_names: dict[str, set[str]] = {}
        for thread in list_threads(client):
            name = thread.get("name")
            thread_id = thread.get("id")
            if isinstance(name, str) and isinstance(thread_id, str):
                existing_names.setdefault(name.casefold(), set()).add(thread_id)

        for thread_id, name, current_name in validated:
            if current_name == name:
                unchanged.append(thread_id)
                continue
            holders = existing_names.get(name.casefold(), set()) - {thread_id}
            if holders:
                failures.append(
                    {
                        "thread_id": thread_id,
                        "error": "proposed name already belongs to another active thread",
                    }
                )

        if failures:
            print(
                json.dumps(
                    {
                        "dry_run": args.dry_run,
                        "renamed": [],
                        "unchanged": unchanged,
                        "failures": failures,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 2

        for thread_id, name, current_name in validated:
            if current_name == name:
                continue
            if not args.dry_run:
                try:
                    client.request(
                        "thread/name/set",
                        {"threadId": thread_id, "name": name},
                    )
                except RpcError as exc:
                    failures.append({"thread_id": thread_id, "error": str(exc)})
                    continue
            renamed.append(
                {"thread_id": thread_id, "old_name": current_name, "new_name": name}
            )

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "renamed": renamed,
                "unchanged": unchanged,
                "failures": failures,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("CODEX_BIN", "codex"),
        help="Codex CLI executable (default: codex)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="write bounded thread excerpts")
    lookback = collect.add_mutually_exclusive_group()
    lookback.add_argument("--since-hours", type=float, default=36)
    lookback.add_argument("--all", action="store_true")
    collect.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS, choices=range(1, 6))
    collect.add_argument("--output", required=True)
    collect.add_argument("--batch-dir")
    collect.add_argument("--batch-size", type=int, default=4, choices=range(1, 9))
    collect.set_defaults(func=collect_command)

    apply_parser = subparsers.add_parser("apply", help="validate and apply names")
    apply_parser.add_argument("--candidates", required=True)
    apply_parser.add_argument("--proposals", required=True)
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument(
        "--max-name-columns",
        type=int,
        default=DEFAULT_MAX_NAME_COLUMNS,
    )
    apply_parser.set_defaults(func=apply_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, RpcError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
