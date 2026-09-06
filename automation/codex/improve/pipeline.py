#!/usr/bin/env python3
"""Bounded, local instruction-review batches and draft-only patch validation.

Only private state and temporary scratch copies are written. No model output is
ever interpreted as a command, and no patch is applied to the source checkout.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
MAX_EVENTS = 200
MAX_BATCH_BYTES = 120_000
MAX_EXCERPT_CHARS = 600
MAX_FILE_BYTES = 128_000
MAX_TARGET_BYTES = 4_000_000
KINDS = {"user_message", "task_outcome", "health"}
BLOCKED_PARTS = {"cache", "vendor", "_vendor", "node_modules", ".git", "credentials", "secrets", "archived-skills"}
CHECKS = {"markdown", "frontmatter"}


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path, limit=2_000_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"unsafe or oversized JSON file: {path}")
    return json.loads(path.read_text())


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def atomic_bytes(path, value):
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"refusing symlink output parent: {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError(f"refusing symlink output: {path}")
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextlib.contextmanager
def locked(state):
    if state.is_symlink():
        raise ValueError("state directory must not be a symlink")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    # Lock files and fixed state directories cannot be redirected by a result.
    for name in ("pipeline.lock", "review", "candidates", "history"):
        if (state / name).is_symlink():
            raise ValueError(f"unsafe state symlink: {name}")
    fd = os.open(state / "pipeline.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def allowed_target(relative):
    path = PurePosixPath(relative)
    if (not relative or path.is_absolute() or str(path) != relative
            or any(part in {"..", "."} | BLOCKED_PARTS for part in path.parts)
            or any(c.isspace() for c in relative) or "\\" in relative):
        return False
    if relative == "config/codex/AGENTS.md":
        return True
    parts = path.parts
    if parts[:3] == ("config", "codex", "skills"):
        tail = parts[3:]
    elif parts[:3] == ("config", "codex", "plugins") and len(parts) > 5 and parts[4] == "skills":
        tail = parts[5:]
    elif (parts[:4] == ("config", "codex", "local", "buildbuddy-dev-marketplace")
          and len(parts) > 7 and parts[4] == "plugins" and parts[6] == "skills"):
        tail = parts[7:]
    else:
        return False
    return (len(tail) == 2 and tail[1] == "SKILL.md") or (
        len(tail) >= 3 and tail[1] == "references" and path.suffix == ".md")


def target_path(root, relative):
    if not allowed_target(relative):
        raise ValueError(f"target outside instruction allowlist: {relative}")
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"symlink target component: {relative}")
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"target missing or oversized: {relative}")
    return path


def inventory(root):
    found = {}
    total = 0
    for directory, dirs, files in os.walk(root / "config/codex", followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in BLOCKED_PARTS and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if not allowed_target(relative):
                continue
            try:
                data = target_path(root, relative).read_bytes()
                data.decode("utf-8")
            except (ValueError, UnicodeError):
                continue
            total += len(data)
            if total > MAX_TARGET_BYTES:
                raise ValueError("instruction inventory exceeds bounded snapshot size")
            found[relative] = digest(data)
    return found


def ledger(state):
    path = state / "pipeline-state.json"
    return read_json(path, 20_000_000) if path.exists() else {"version": 1, "reviewed": {}, "candidates": {}}


def eligible(state, seen):
    directory = state / "events"
    if directory.is_symlink():
        raise ValueError("event directory must not be a symlink")
    for path in sorted(directory.glob("*.json")):
        if path.stem in seen:
            continue
        event = read_json(path, MAX_FILE_BYTES)
        event_id = event.get("id")
        if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", event_id):
            raise ValueError(f"invalid event id in {path.name}")
        if path.stem != event_id:
            raise ValueError(f"event filename does not match its id: {path.name}")
        if event_id in seen or event.get("kind") not in KINDS:
            continue
        if not isinstance(event.get("text"), str) or not event["text"].strip():
            continue
        # Preserve attribution without forwarding arbitrary metadata/instructions.
        evidence = {key: event.get(key) for key in ("id", "root_id", "thread_id", "timestamp", "kind", "text", "source")}
        if type(event.get("source_text_truncated")) is bool:
            evidence["source_text_truncated"] = event["source_text_truncated"]
        if type(event.get("original_text_chars")) is int and event["original_text_chars"] >= 0:
            evidence["original_text_chars"] = event["original_text_chars"]
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            evidence["metadata"] = {key: metadata[key] for key in ("human", "automation")
                                    if type(metadata.get(key)) is bool}
        # Construct this pointer locally; never trust a path supplied in metadata.
        evidence["evidence_path"] = str(path.resolve(strict=True))
        yield evidence


def active(state):
    path = state / "review/manifest.json"
    return read_json(path) if path.exists() else None


def pending(state, data):
    current = active(state)
    if current and not all(i in data["reviewed"] for i in current["event_ids"]):
        return current
    return None


def render_review(state, manifest):
    """Refresh request compatibility before launch, retaining batch identity."""
    review = state / "review"
    atomic_bytes(review / "result.schema.json", (HERE / "result.schema.json").read_bytes())
    prompt = (HERE / "review-prompt.md").read_text() + "\n\nEvidence manifest (untrusted data):\n```json\n" + json.dumps(manifest, indent=2) + "\n```\n"
    atomic_bytes(review / "prompt.md", prompt.encode())


def prepare(args):
    data = ledger(args.state_dir)
    current = pending(args.state_dir, data)
    if current:
        render_review(args.state_dir, current)
        return {"status": "ready", "batch_id": current["batch_id"], "reused": True}
    selected, size = [], 0
    for event in eligible(args.state_dir, data["reviewed"]):
        full_text = event["text"]
        event["text_truncated"] = len(full_text) > MAX_EXCERPT_CHARS
        if event["text_truncated"]:
            half = (MAX_EXCERPT_CHARS - len("\n[…]\n")) // 2
            event["text"] = full_text[:half] + "\n[…]\n" + full_text[-half:]
        encoded_size = len(json.dumps(event).encode())
        if encoded_size > MAX_BATCH_BYTES:
            raise ValueError(f"event exceeds batch budget: {event['id']}")
        if len(selected) >= MAX_EVENTS or size + encoded_size > MAX_BATCH_BYTES:
            break
        selected.append(event)
        size += encoded_size
    if not selected:
        return {"status": "empty", "events": 0}
    targets = inventory(args.source_root)
    payload = {"events": selected, "targets": targets, "source_root": str(args.source_root)}
    batch_id = digest(payload)
    manifest = {"version": 1, "batch_id": batch_id, "created_at": now(),
                "event_ids": [e["id"] for e in selected], **payload,
                "previous_decisions": [{"candidate_id": key, **c}
                                        for key, c in data["candidates"].items()][-100:]}
    review = args.state_dir / "review"
    render_review(args.state_dir, manifest)
    # Manifest is the commit marker: an interrupted preparation can be retried.
    atomic_json(review / "manifest.json", manifest)
    return {"status": "ready", "batch_id": batch_id, "events": len(selected), "prompt": str(review / "prompt.md")}


def validate_schema(value, schema, where="result"):
    """Small strict validator for the checked-in schema; no optional packages."""
    types = {"object": dict, "array": list, "string": str, "null": type(None)}
    expected = schema.get("type")
    choices = expected if isinstance(expected, list) else [expected]
    if expected and not any(isinstance(value, types[t]) for t in choices):
        raise ValueError(f"{where}: incorrect type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{where}: unsupported value")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            raise ValueError(f"{where}: missing required fields")
        if schema.get("additionalProperties") is False and value.keys() - props.keys():
            raise ValueError(f"{where}: unexpected fields")
        for key, item in value.items():
            if key in props:
                validate_schema(item, props[key], f"{where}.{key}")
    if isinstance(value, (str, list)):
        low, high = ("minLength", "maxLength") if isinstance(value, str) else ("minItems", "maxItems")
        if not schema.get(low, 0) <= len(value) <= schema.get(high, sys.maxsize):
            raise ValueError(f"{where}: length out of bounds")
    if isinstance(value, str) and "pattern" in schema and not re.fullmatch(schema["pattern"], value):
        raise ValueError(f"{where}: invalid format")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({digest(v) for v in value}) != len(value):
            raise ValueError(f"{where}: duplicate items")
        for i, item in enumerate(value):
            validate_schema(item, schema["items"], f"{where}[{i}]")


def validate_patch(patch, relative):
    if not patch or "\x00" in patch or len(patch.encode()) > 32_000:
        raise ValueError("missing, binary, or oversized patch")
    lines = patch.splitlines()
    if lines[:2] != [f"--- a/{relative}", f"+++ b/{relative}"]:
        raise ValueError("patch must start with exact single-file old/new headers")
    if not any(line.startswith("@@ ") for line in lines[2:]):
        raise ValueError("patch has no unified diff hunks")
    # No extended headers, additional files, modes, renames, or binary patches.
    for line in lines[2:]:
        if line.startswith(("--- ", "+++ ", "diff ", "GIT binary", "index ", "new file", "deleted file", "rename ", "old mode", "new mode")):
            raise ValueError("patch contains unsupported metadata or extra files")
        if line and line[0] not in " +-@\\":
            raise ValueError("unsupported patch content")


def finish(args):
    data = ledger(args.state_dir)
    manifest = active(args.state_dir)
    if not manifest:
        raise ValueError("no prepared batch")
    result = read_json(args.result, 150_000)
    validate_schema(result, read_json(HERE / "result.schema.json"))
    if result["batch_id"] != manifest["batch_id"]:
        raise ValueError("result batch_id does not match prepared manifest")
    if result["outcome"] == "no_change" and result["candidates"]:
        raise ValueError("no_change result must have no candidates")
    if all(i in data["reviewed"] for i in manifest["event_ids"]):
        return {"status": "already_reviewed", "batch_id": manifest["batch_id"]}
    if str(args.source_root) != manifest["source_root"]:
        raise ValueError("source root differs from prepared batch")
    candidates = []
    for candidate in result["candidates"]:
        target = candidate["target"]
        for field in ("evidence_event_ids", "checks"):
            if len(set(candidate[field])) != len(candidate[field]):
                raise ValueError(f"candidate {field}: duplicate items")
        if not allowed_target(target) or target not in manifest["targets"]:
            raise ValueError("candidate target not in prepared allowlist")
        if not set(candidate["evidence_event_ids"]) <= set(manifest["event_ids"]):
            raise ValueError("candidate cites evidence outside prepared batch")
        if "frontmatter" in candidate["checks"] and not target.endswith("/SKILL.md"):
            raise ValueError("frontmatter check applies only to SKILL.md")
        if candidate["patch"] is not None:
            validate_patch(candidate["patch"], target)
        identity = {"target": target, "proposed_change": " ".join(candidate["proposed_change"].lower().split())}
        candidate_id = digest(identity)[:24]
        candidates.append((candidate_id, candidate))
    # Validate the whole result before writing candidates or acknowledging input.
    created, suppressed, validations = [], [], {}
    for candidate_id, candidate in candidates:
        if candidate_id in data["candidates"]:
            suppressed.append(candidate_id)
            continue
        artifact = {"version": 1, "candidate_id": candidate_id, "batch_id": manifest["batch_id"],
                    "created_at": now(), "baseline_sha256": manifest["targets"][candidate["target"]],
                    "source_root": manifest["source_root"], "status": "needsreview", **candidate}
        atomic_json(args.state_dir / "candidates" / candidate_id / "candidate.json", artifact)
        validation = check(SimpleNamespace(state_dir=args.state_dir, source_root=args.source_root, candidate_id=candidate_id))
        validations[candidate_id] = validation["status"]
        data["candidates"][candidate_id] = {"status": "needsreview", "target": candidate["target"],
                                           "proposed_change": candidate["proposed_change"], "batch_id": manifest["batch_id"]}
        created.append(candidate_id)
    atomic_json(args.state_dir / "history" / f"{manifest['batch_id']}.json", {
        "manifest": manifest, "result": result, "finished_at": now(),
        "admitted_candidate_ids": created, "suppressed_candidate_ids": suppressed})
    data["reviewed"].update({event_id: manifest["batch_id"] for event_id in manifest["event_ids"]})
    pending_count = sum(1 for _ in eligible(args.state_dir, data["reviewed"]))
    lines = ["# Instruction review", "", f"Batch: `{manifest['batch_id']}`", "",
             result["summary"], "",
             f"Coverage: {len(manifest['event_ids'])} events screened in this batch; {pending_count} eligible events remain pending.",
             "Screening uses bounded excerpts. Stored event files and original-record locators remain available for relevant follow-up; source capture truncation is marked when known. It does not imply every original message or the whole backlog was read.", ""]
    if not candidates:
        lines.extend(["No instruction changes proposed for this batch.", ""])
    for candidate_id, candidate in candidates:
        validation_status = validations.get(candidate_id, "previous proposal; duplicate suppressed")
        lines.extend([f"- `{candidate_id}` — `{candidate['target']}`: {validation_status}.",
                      f"  [Proposal](candidates/{candidate_id}/candidate.json) · [Validation](candidates/{candidate_id}/validation.json)"])
    lines.extend(["", "Behavioral validation: not performed; scenario-specific evaluation needed.",
                  "Accepted/applied/rejected decisions are included in later review batches for recurrence assessment.", ""])
    atomic_bytes(args.state_dir / "latest.md", "\n".join(lines).encode())
    atomic_json(args.state_dir / "pipeline-state.json", data)
    return {"status": "reviewed", "batch_id": manifest["batch_id"], "candidate_ids": created,
            "suppressed_candidate_ids": suppressed, "validation": validations, "events": len(manifest["event_ids"]),
            "pending_events": pending_count, "report": str(args.state_dir / "latest.md")}


def markdown_check(text):
    if "\x00" in text or not text.strip():
        raise ValueError("Markdown must be nonempty UTF-8 text without NUL bytes")
    if any(re.match(r"^(<<<<<<< |=======$|>>>>>>> )", line) for line in text.splitlines()):
        raise ValueError("unresolved merge conflict markers")


def frontmatter_check(text):
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("SKILL.md requires delimited frontmatter")
    try:
        import yaml
    except ImportError as error:
        raise ValueError("frontmatter validation unavailable: install Python PyYAML") from error
    try:
        fields = yaml.safe_load(text.split("\n---\n", 1)[0][4:])
    except yaml.YAMLError as error:
        raise ValueError(f"invalid frontmatter YAML: {error}") from error
    if not isinstance(fields, dict):
        raise ValueError("frontmatter must be a mapping")
    for key in ("name", "description"):
        if not isinstance(fields.get(key), str) or not fields[key].strip():
            raise ValueError(f"frontmatter requires nonempty {key}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]) or len(fields["name"]) > 64:
        raise ValueError("invalid skill name")
    if len(fields["description"]) > 1024:
        raise ValueError("skill description exceeds 1024 characters")


def candidate_artifact(args):
    if not re.fullmatch(r"[a-f0-9]{24}", args.candidate_id):
        raise ValueError("invalid candidate ID")
    directory = args.state_dir / "candidates" / args.candidate_id
    if directory.is_symlink():
        raise ValueError("candidate directory must not be a symlink")
    return directory, read_json(directory / "candidate.json")


def check(args):
    directory, candidate = candidate_artifact(args)
    report = {"candidate_id": args.candidate_id, "checked_at": now(), "status": "failed",
              "checks": [], "live_changes": False, "behavioral_validation": "not performed; scenario-specific evaluation needed"}
    try:
        if candidate["source_root"] != str(args.source_root):
            raise ValueError("source root differs from proposal baseline")
        relative = candidate["target"]
        path = target_path(args.source_root, relative)
        baseline = path.read_bytes()
        if digest(baseline) != candidate["baseline_sha256"]:
            raise ValueError("baseline changed: prepare a fresh proposal before validation")
        validate_patch(candidate["patch"], relative)
        with tempfile.TemporaryDirectory(prefix="codex-improve-check-") as scratch:
            target = Path(scratch) / relative
            target.parent.mkdir(parents=True)
            target.write_bytes(baseline)
            patch = Path(scratch) / "candidate.patch"
            patch.write_text(candidate["patch"])
            env = {"PATH": os.defpath, "HOME": scratch, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "LC_ALL": "C"}
            for mode in ("check", "apply"):
                command = ["git", "-c", "core.hooksPath=/dev/null", "apply", "--whitespace=error"]
                if mode == "check":
                    command.append("--check")
                command.append(str(patch))
                completed = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=10, check=False)
                if completed.returncode:
                    raise ValueError(f"git apply {mode} failed: {completed.stderr[:2000]}")
            report["checks"].append({"kind": "patch_apply", "status": "passed"})
            text = target.read_text()
            # Required checks cannot be removed through the model's checks list.
            requested = set(candidate["checks"]) | {"markdown"}
            if relative.endswith("/SKILL.md"):
                requested.add("frontmatter")
            if not requested <= CHECKS:
                raise ValueError("unsupported declarative check")
            for kind in sorted(requested):
                (frontmatter_check if kind == "frontmatter" else markdown_check)(text)
                report["checks"].append({"kind": kind, "status": "passed"})
            atomic_bytes(directory / "validated.patch", candidate["patch"].encode())
            report["status"] = "syntax_validated_needs_behavior_review"
            report["result_sha256"] = digest(text.encode())
    except (ValueError, OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
    atomic_json(directory / "validation.json", report)
    return report


def decision(args):
    directory, candidate = candidate_artifact(args)
    data = ledger(args.state_dir)
    if args.candidate_id not in data["candidates"]:
        raise ValueError("candidate missing from review ledger")
    if args.status == "applied":
        validation = read_json(directory / "validation.json")
        if validation.get("status") != "syntax_validated_needs_behavior_review":
            raise ValueError("applied requires a successfully validated patch")
        if candidate["source_root"] != str(args.source_root):
            raise ValueError("source root differs from candidate baseline")
        current_hash = digest(target_path(args.source_root, candidate["target"]).read_bytes())
        if current_hash != validation.get("result_sha256"):
            raise ValueError("live target does not match validated patch result")
        data["candidates"][args.candidate_id]["applied_sha256"] = current_hash
        data["candidates"][args.candidate_id]["applied_at"] = now()
    data["candidates"][args.candidate_id]["status"] = args.status
    data["candidates"][args.candidate_id]["decision_at"] = now()
    candidate["status"] = args.status
    atomic_json(directory / "candidate.json", candidate)
    atomic_json(args.state_dir / "pipeline-state.json", data)
    return {"candidate_id": args.candidate_id, "status": args.status, "live_changes": False}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--state-dir", type=Path, default=Path.home() / ".local/state/codex-improve")
    result.add_argument("--source-root", type=Path, default=HERE.parents[2])
    result.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("prepare", "gate", "status"):
        commands.add_parser(name)
    commands.add_parser("finish").add_argument("--result", required=True, type=Path)
    commands.add_parser("check").add_argument("candidate_id")
    decision_parser = commands.add_parser("decision")
    decision_parser.add_argument("candidate_id")
    decision_parser.add_argument("--status", choices=("accepted", "rejected", "needsreview", "applied"), required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    args.source_root = args.source_root.expanduser().resolve()
    args.state_dir = args.state_dir.expanduser().absolute()
    try:
        with locked(args.state_dir):
            if args.command in {"prepare", "finish", "check", "decision"}:
                output = globals()[args.command](args)
            else:
                data = ledger(args.state_dir)
                current = pending(args.state_dir, data)
                ready = bool(current) or next(eligible(args.state_dir, data["reviewed"]), None) is not None
                output = {"status": "ready" if ready else "empty", "reviewed_events": len(data["reviewed"]),
                          "candidates": data["candidates"], "active_batch": current["batch_id"] if current else None}
                if args.command == "gate":
                    print(json.dumps({"status": output["status"]}))
                    return 0 if ready else 1
                total_pending = sum(1 for _ in eligible(args.state_dir, data["reviewed"]))
                output.update({"pending_events": total_pending,
                               "active_batch_selected_events": len(current["event_ids"]) if current else 0,
                               "active_batch_total_pending_events": total_pending})
        print(json.dumps(output, sort_keys=True))
        return 2 if output.get("status") == "failed" else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 255 if args.command == "gate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
