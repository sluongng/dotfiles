#!/usr/bin/env python3
"""Query Codex Security Cloud Aardvark APIs directly.

This helper reads the local Codex ChatGPT access token, then calls the
chatgpt.com backend with bearer auth and a browser-style User-Agent header.
Tokens stay in memory and are not printed or placed on the process command
line.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


CHATGPT_ORIGIN = "https://chatgpt.com"
DEFAULT_STATUSES = "new,triaged,in_progress"
DEFAULT_CRITICALITIES = "medium,high,critical,low"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)


class CloudError(RuntimeError):
    pass


def load_auth() -> tuple[str, str | None, str]:
    env_token = os.environ.get("CODEX_ACCESS_TOKEN")
    if env_token:
        return env_token, None, "CODEX_ACCESS_TOKEN"

    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    auth_path = codex_home / "auth.json"
    try:
        auth = json.loads(auth_path.read_text())
    except FileNotFoundError as exc:
        raise CloudError(f"Codex auth file not found: {auth_path}") from exc
    except json.JSONDecodeError as exc:
        raise CloudError(f"Codex auth file is not valid JSON: {auth_path}") from exc

    token = auth.get("tokens", {}).get("access_token")
    if not isinstance(token, str) or not token:
        raise CloudError("No ChatGPT access token found in Codex auth. Run codex login with ChatGPT auth.")
    account_id = auth.get("tokens", {}).get("account_id")
    if not isinstance(account_id, str):
        account_id = None
    mode = auth.get("auth_mode")
    if mode != "chatgpt":
        raise CloudError(f"Codex auth_mode is {mode!r}, not 'chatgpt'. API-key auth cannot access cloud findings.")
    return token, account_id, str(auth_path)


def normalize_repo(repo: str | None) -> str | None:
    if not repo:
        return None
    repo = repo.strip()
    if repo.startswith("https://"):
        return repo
    if repo.count("/") == 1:
        return f"https://github.com/{repo}"
    return repo


def resolve_user_agent(value: str | None = None) -> tuple[str, str]:
    if value:
        return value, "argument"
    env_value = os.environ.get("CODEX_SECURITY_CLOUD_USER_AGENT")
    if env_value:
        return env_value, "CODEX_SECURITY_CLOUD_USER_AGENT"
    return DEFAULT_USER_AGENT, "default"


def api_url(path: str) -> str:
    if path.startswith("https://") or path.startswith("http://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{CHATGPT_ORIGIN}{path}"


def parse_response_body(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text_preview": " ".join(text.split())[:500]}


def http_get(token: str, path: str, *, user_agent: str, timeout: int) -> dict[str, Any]:
    url = api_url(path)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": user_agent,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = parse_response_body(response.read())
            status = int(response.status)
            return {"ok": 200 <= status < 300, "status": status, "url": response.geturl(), "body": body}
    except urllib.error.HTTPError as exc:
        body = parse_response_body(exc.read())
        return {"ok": False, "status": int(exc.code), "url": exc.geturl(), "body": body}
    except urllib.error.URLError as exc:
        raise CloudError(f"Aardvark API request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise CloudError(f"Aardvark API request timed out after {timeout}s") from exc


def api_error_preview(body: Any) -> str:
    if isinstance(body, dict):
        for key in ("error", "message", "detail", "text_preview"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value[:500]
    return json.dumps(body, sort_keys=True)[:500]


def api_get(path: str, *, user_agent: str | None, timeout: int) -> dict[str, Any]:
    token, _account_id, _source = load_auth()
    resolved_user_agent, _user_agent_source = resolve_user_agent(user_agent)
    response = http_get(token, path, user_agent=resolved_user_agent, timeout=timeout)
    if response.get("status") == 401:
        raise CloudError("Aardvark API returned 401. Refresh Codex ChatGPT auth with codex login.")
    if response.get("status") == 403:
        raise CloudError(
            "Aardvark API returned 403. Direct HTTP was rejected; retry with "
            "CODEX_SECURITY_CLOUD_USER_AGENT set to a current Chrome User-Agent."
        )
    if not response.get("ok"):
        raise CloudError(f"Aardvark API returned {response.get('status')}: {api_error_preview(response.get('body'))}")
    return response


def finding_title(item: dict[str, Any]) -> str:
    commit_analysis = item.get("commit_analysis")
    if isinstance(commit_analysis, dict):
        title = commit_analysis.get("title")
        if isinstance(title, str) and title:
            return title
    title = item.get("title")
    return title if isinstance(title, str) and title else "<untitled>"


def finding_commit(item: dict[str, Any]) -> str:
    commit_analysis = item.get("commit_analysis")
    if isinstance(commit_analysis, dict):
        value = commit_analysis.get("commit_hash")
        if isinstance(value, str):
            return value[:12]
    return ""


def print_findings_summary(document: dict[str, Any]) -> None:
    items = document.get("items")
    if not isinstance(items, list):
        print(json.dumps(document, indent=2, sort_keys=True))
        return
    total = document.get("total")
    next_cursor = document.get("next_cursor")
    print(f"items={len(items)} total={total} next_cursor={next_cursor}")
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        hid = item.get("hid") or item.get("id") or ""
        criticality = item.get("criticality") or item.get("severity") or ""
        status = item.get("status") or ""
        commit = finding_commit(item)
        print(f"{idx}. [{criticality} {status}] {finding_title(item)}")
        print(f"   hid={hid} commit={commit}")


def print_repos_summary(document: Any) -> None:
    if isinstance(document, dict):
        candidates = [document.get("items"), document.get("repos"), document.get("repositories")]
        rows = next((row for row in candidates if isinstance(row, list)), None)
    elif isinstance(document, list):
        rows = document
    else:
        rows = None
    if rows is None:
        print(json.dumps(document, indent=2, sort_keys=True))
        return
    print(f"repos={len(rows)}")
    for row in rows:
        if isinstance(row, str):
            print(row)
        elif isinstance(row, dict):
            print(row.get("repo_url") or row.get("url") or row.get("name") or json.dumps(row, sort_keys=True))


def query_string(params: dict[str, Any]) -> str:
    clean = {key: value for key, value in params.items() if value is not None and value != ""}
    return urlencode(clean)


def command_doctor(args: argparse.Namespace) -> int:
    token, account_id, source = load_auth()
    user_agent, user_agent_source = resolve_user_agent(args.user_agent)
    print(f"auth_source={source}")
    print(f"access_token=present length={len(token)}")
    print(f"account_id={'present' if account_id else 'absent'}")
    print("http_client=direct")
    print(f"user_agent_source={user_agent_source} length={len(user_agent)}")
    if args.probe:
        path = "/backend-api/aardvark/scan-findings/list-accessible-repos?force_refresh=false"
        response = api_get(path, user_agent=args.user_agent, timeout=args.timeout)
        body = response.get("body")
        keys = sorted(body.keys()) if isinstance(body, dict) else []
        print(f"probe_status={response.get('status')} body_keys={','.join(keys)}")
    return 0


def command_list_repos(args: argparse.Namespace) -> int:
    path = "/backend-api/aardvark/scan-findings/list-accessible-repos?force_refresh=false"
    response = api_get(path, user_agent=args.user_agent, timeout=args.timeout)
    body = response.get("body")
    if args.format == "json":
        print(json.dumps(body, indent=2, sort_keys=True))
    else:
        print_repos_summary(body)
    return 0


def command_list_findings(args: argparse.Namespace) -> int:
    repo = normalize_repo(args.repo)
    params = {
        "limit": args.limit,
        "cursor": args.cursor,
        "repo": repo,
        "status": args.status,
        "criticality": args.criticality,
        "archived": "true" if args.archived else None,
    }
    path = f"/backend-api/aardvark/scan-findings?{query_string(params)}"
    response = api_get(path, user_agent=args.user_agent, timeout=args.timeout)
    body = response.get("body")
    if args.format == "json":
        print(json.dumps(body, indent=2, sort_keys=True))
    else:
        print_findings_summary(body if isinstance(body, dict) else {"body": body})
    return 0


def command_get_finding(args: argparse.Namespace) -> int:
    finding_id = args.finding_id.strip()
    path = f"/backend-api/aardvark/scan-findings/{finding_id}"
    response = api_get(path, user_agent=args.user_agent, timeout=args.timeout)
    body = response.get("body")
    if args.format == "json":
        print(json.dumps(body, indent=2, sort_keys=True))
        return 0
    if not isinstance(body, dict):
        print(json.dumps(body, indent=2, sort_keys=True))
        return 0
    commit_analysis = body.get("commit_analysis") if isinstance(body.get("commit_analysis"), dict) else {}
    print(f"title={commit_analysis.get('title') or '<untitled>'}")
    print(f"hid={body.get('hid') or body.get('id')}")
    print(f"criticality={body.get('criticality')} status={body.get('status')}")
    print(f"repo={body.get('repo_url')}")
    print(f"commit={commit_analysis.get('commit_hash')}")
    description = commit_analysis.get("description")
    if isinstance(description, str) and description:
        print()
        print(description.strip())
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--user-agent", help="Override the browser-style User-Agent header")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP request timeout in seconds")
    parser.add_argument("--session", help=argparse.SUPPRESS)
    parser.add_argument("--turn", help=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query Codex Security Cloud findings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local auth and direct HTTP readiness")
    add_common(doctor)
    doctor.add_argument("--probe", action="store_true", help="Run a non-secret API probe")
    doctor.set_defaults(func=command_doctor)

    repos = subparsers.add_parser("list-repos", help="List accessible repositories")
    add_common(repos)
    repos.add_argument("--format", choices=["summary", "json"], default="summary")
    repos.set_defaults(func=command_list_repos)

    findings = subparsers.add_parser("list-findings", help="List scan findings")
    add_common(findings)
    findings.add_argument("--repo", help="GitHub repo as owner/name or https://github.com/owner/name")
    findings.add_argument("--limit", type=int, default=20)
    findings.add_argument("--cursor", default="0")
    findings.add_argument("--status", default=DEFAULT_STATUSES)
    findings.add_argument("--criticality", default=DEFAULT_CRITICALITIES)
    findings.add_argument("--archived", action="store_true")
    findings.add_argument("--format", choices=["summary", "json"], default="summary")
    findings.set_defaults(func=command_list_findings)

    detail = subparsers.add_parser("get-finding", help="Get one finding by 32-character hid")
    add_common(detail)
    detail.add_argument("finding_id")
    detail.add_argument("--format", choices=["summary", "json"], default="summary")
    detail.set_defaults(func=command_get_finding)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CloudError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
