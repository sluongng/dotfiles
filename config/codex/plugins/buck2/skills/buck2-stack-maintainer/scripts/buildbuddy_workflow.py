#!/usr/bin/env python3
"""Trigger and poll a BuildBuddy Workflow invocation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://sluongng.buildbuddy.io/api/v1"
BUCK2_REPO_URL = "https://github.com/sluongng/buck2"
BUCK2_GITHUB_INSTALLATION_URL = "https://github.com/settings/installations/36994646"
BUCK2_GITHUB_REPO_ID = "634428231"


def diagnose_http_error(endpoint: str, detail: str) -> str:
    if endpoint != "ExecuteWorkflow":
        return ""
    if "repo " not in detail or " not found" not in detail:
        return ""
    if BUCK2_REPO_URL not in detail and f"{BUCK2_REPO_URL}.git" not in detail:
        return ""

    return (
        "\n\nBuildBuddy workflow setup diagnosis:\n"
        f"- BuildBuddy does not have a linked Workflow repo for {BUCK2_REPO_URL}.\n"
        "- The BuildBuddy GitHub App installation for the sluongng account "
        "must include sluongng/buck2 before ExecuteWorkflow can work.\n"
        f"- Current GitHub installation URL: {BUCK2_GITHUB_INSTALLATION_URL}.\n"
        f"- Current GitHub repo id: {BUCK2_GITHUB_REPO_ID}.\n"
        "- After granting the app access to that repo, link it from "
        "https://sluongng.buildbuddy.io/workflows/new in the sluongng org, "
        "then rerun this command.\n"
    )


def parse_api_key_file(path: Path) -> str:
    if not path.exists():
        return ""
    current_section = ""
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            continue
        if current_section == "buildbuddy":
            match = re.match(r"api_key\s*=\s*(\S+)", line)
            if match:
                return match.group(1).strip().strip('"').strip("'")
    return ""


def load_api_key(env_name: str, api_key_file: str) -> str:
    api_key = os.environ.get(env_name, "")
    if not api_key:
        api_key = parse_api_key_file(Path(api_key_file)) if api_key_file else ""
    if not api_key:
        raise SystemExit(f"{env_name} is not set and no API key was found in {api_key_file}")
    return api_key


def post_json(base_url: str, endpoint: str, payload: dict, api_key: str) -> dict:
    url = f"{base_url.rstrip('/')}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-buildbuddy-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        diagnosis = diagnose_http_error(endpoint, detail)
        raise SystemExit(f"{endpoint} failed with HTTP {e.code}: {detail}{diagnosis}") from e

    if not body:
        return {}
    return json.loads(body)


def get_field(obj: dict, *names: str):
    for name in names:
        if name in obj:
            return obj[name]
    return None


def execute(args: argparse.Namespace, api_key: str) -> list[str]:
    payload = {
        "repo_url": args.repo_url,
        "branch": args.branch,
        "commit_sha": args.commit_sha,
        "action_names": args.action_name,
        "async": args.poll,
    }
    env = {}
    for item in args.env:
        if "=" not in item:
            raise SystemExit(f"--env must be KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        env[key] = value
    if env:
        payload["env"] = env
    if args.visibility:
        payload["visibility"] = args.visibility

    response = post_json(args.base_url, "ExecuteWorkflow", payload, api_key)
    statuses = get_field(response, "action_statuses", "actionStatuses") or []
    invocation_ids: list[str] = []
    for status in statuses:
        action_name = get_field(status, "action_name", "actionName") or "<unknown>"
        invocation_id = get_field(status, "invocation_id", "invocationId")
        grpc_status = status.get("status") or {}
        code = grpc_status.get("code", 0)
        message = grpc_status.get("message", "")
        print(f"{action_name}: invocation={invocation_id or '<none>'} status={code} {message}".rstrip())
        if code not in (0, "0"):
            raise SystemExit(f"BuildBuddy refused to start action {action_name}: {message}")
        if invocation_id:
            invocation_ids.append(invocation_id)
    if not invocation_ids:
        raise SystemExit("ExecuteWorkflow returned no invocation IDs")
    return invocation_ids


def poll_invocation(args: argparse.Namespace, api_key: str, invocation_id: str) -> bool:
    deadline = time.monotonic() + args.timeout_seconds
    payload = {
        "selector": {"invocation_id": invocation_id},
        "include_metadata": True,
        "include_build_tool_logs": False,
        "include_child_invocations": True,
    }
    while True:
        response = post_json(args.base_url, "GetInvocation", payload, api_key)
        invocations = get_field(response, "invocation", "invocations") or []
        if invocations:
            invocation = invocations[0]
            status = get_field(invocation, "invocationStatus", "invocation_status")
            success = bool(invocation.get("success"))
            url = invocation.get("url") or f"https://sluongng.buildbuddy.io/invocation/{invocation_id}"
            print(f"{invocation_id}: {status} success={success} {url}")
            if status == "COMPLETE_INVOCATION_STATUS" or status == 1:
                return success
            if status == "DISCONNECTED_INVOCATION_STATUS" or status == 3:
                # Workflow invocations can briefly report DISCONNECTED while the
                # runner is still alive and later return to PARTIAL. Keep polling
                # until the invocation completes or the overall timeout expires.
                pass
        else:
            print(f"{invocation_id}: not visible yet")

        if time.monotonic() >= deadline:
            raise SystemExit(f"Timed out waiting for invocation {invocation_id}")
        time.sleep(args.poll_interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-url", default="https://github.com/sluongng/buck2")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--action-name", action="append", default=[])
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--visibility", default="")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default="BUILDBUDDY_API_KEY")
    parser.add_argument("--api-key-file", default=".buckconfig.local")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=60 * 60 * 3)
    parser.add_argument("--poll-interval-seconds", type=int, default=30)
    args = parser.parse_args()

    if not args.action_name:
        args.action_name = ["Buck2 Stack Test"]

    api_key = load_api_key(args.api_key_env, args.api_key_file)
    invocation_ids = execute(args, api_key)
    if not args.poll:
        return 0

    ok = True
    for invocation_id in invocation_ids:
        ok = poll_invocation(args, api_key, invocation_id) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
