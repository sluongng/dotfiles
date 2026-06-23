#!/usr/bin/env python3
"""Query Codex Security Cloud Aardvark APIs through Chrome.

The ChatGPT backend is protected by a browser perimeter. This helper reads the
local Codex ChatGPT access token, then evaluates a fetch call inside a
chatgpt.com tab controlled by the Codex Chrome extension. Tokens are passed to
the extension over stdin, not printed or placed on the process command line.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


CHATGPT_ORIGIN = "https://chatgpt.com"
FINDINGS_PATH = "/codex/cloud/security/findings"
DEFAULT_STATUSES = "new,triaged,in_progress"
DEFAULT_CRITICALITIES = "medium,high,critical,low"
DEFAULT_SESSION = "codex-security-cloud"
DEFAULT_TURN = "query"
SESSION_GROUP_TITLE = "Codex Security Cloud"


class CloudError(RuntimeError):
    pass


def command_path() -> str:
    path = shutil.which("codex-linux-extension-host")
    if path:
        return path
    return str(Path.home() / ".local/bin/codex-linux-extension-host")


def run_host(args: list[str], params: dict[str, Any] | None = None, *, timeout: int = 30) -> Any:
    cmd = [command_path(), "--json", *args]
    input_text = None
    if params is not None:
        cmd.extend(["--params", "-"])
        input_text = json.dumps(params)
    proc = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    output = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise CloudError(f"Chrome bridge returned non-JSON output: {output[:500]}") from exc
    if isinstance(data, dict) and data.get("ok") is False:
        raise CloudError(str(data.get("error", data)))
    if proc.returncode != 0:
        raise CloudError(output[:500])
    return data


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


def tab_candidates(session: str, turn: str) -> list[dict[str, Any]]:
    data = run_host(["tabs", "--session", session, "--turn", turn])
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def claim_tab(tab_id: int, session: str, turn: str) -> None:
    run_host(["claim-tab", "--tab-id", str(tab_id), "--session", session, "--turn", turn])


def ensure_chatgpt_tab(session: str, turn: str, *, create: bool = True) -> int:
    tabs = tab_candidates(session, turn)
    for tab in tabs:
        url = str(tab.get("url", ""))
        if (
            tab.get("tabGroup") == SESSION_GROUP_TITLE
            and url.startswith(f"{CHATGPT_ORIGIN}/codex/cloud/security")
            and isinstance(tab.get("id"), int)
        ):
            tab_id = int(tab["id"])
            claim_tab(tab_id, session, turn)
            return tab_id
    for tab in tabs:
        url = str(tab.get("url", ""))
        if (
            tab.get("tabGroup") == SESSION_GROUP_TITLE
            and url.startswith(CHATGPT_ORIGIN)
            and isinstance(tab.get("id"), int)
        ):
            tab_id = int(tab["id"])
            claim_tab(tab_id, session, turn)
            return tab_id
    if not create:
        raise CloudError("No chatgpt.com tab is available to satisfy the browser perimeter.")
    run_host(["name-session", SESSION_GROUP_TITLE, "--session", session, "--turn", turn])
    result = run_host(
        [
            "navigate",
            f"{CHATGPT_ORIGIN}{FINDINGS_PATH}",
            "--session",
            session,
            "--turn",
            turn,
            "--timeout-ms",
            "20000",
        ],
        timeout=25,
    )
    tab_id = result.get("tabId") if isinstance(result, dict) else None
    if not isinstance(tab_id, int):
        raise CloudError(f"Chrome bridge did not return a tabId: {result!r}")
    return tab_id


def attach_tab(tab_id: int, session: str, turn: str) -> None:
    try:
        run_host(["attach", "--tab-id", str(tab_id), "--session", session, "--turn", turn])
    except CloudError as exc:
        message = str(exc)
        if "Another debugger" in message:
            return
        raise


def evaluate(tab_id: int, expression: str, session: str, turn: str, *, timeout_ms: int = 30000) -> Any:
    params = {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,
        "timeout": timeout_ms,
    }
    data = run_host(
        ["cdp", "--tab-id", str(tab_id), "Runtime.evaluate", "--session", session, "--turn", turn],
        params,
        timeout=max(35, timeout_ms // 1000 + 5),
    )
    if "exceptionDetails" in data:
        details = data["exceptionDetails"]
        text = details.get("text") if isinstance(details, dict) else str(details)
        raise CloudError(f"JavaScript evaluation failed: {text}")
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, dict):
        raise CloudError(f"Unexpected CDP result: {data!r}")
    if "value" in result:
        return result["value"]
    if "description" in result:
        raise CloudError(str(result["description"]))
    return result


def browser_fetch(tab_id: int, token: str, path: str, session: str, turn: str) -> dict[str, Any]:
    expression = (
        "(async () => {\n"
        f"  const token = {json.dumps(token)};\n"
        f"  const path = {json.dumps(path)};\n"
        "  const response = await fetch(path, {\n"
        "    method: 'GET',\n"
        "    credentials: 'omit',\n"
        "    headers: { Authorization: 'Bearer ' + token },\n"
        "  });\n"
        "  const text = await response.text();\n"
        "  let body = null;\n"
        "  try { body = JSON.parse(text); } catch (_) { body = { text_preview: text.slice(0, 500) }; }\n"
        "  return { ok: response.ok, status: response.status, url: response.url, body };\n"
        "})()"
    )
    value = evaluate(tab_id, expression, session, turn)
    if not isinstance(value, dict):
        raise CloudError(f"Unexpected fetch result: {value!r}")
    return value


def api_get(path: str, *, session: str, turn: str) -> dict[str, Any]:
    token, _account_id, _source = load_auth()
    tab_id = ensure_chatgpt_tab(session, turn)
    attach_tab(tab_id, session, turn)
    response = browser_fetch(tab_id, token, path, session, turn)
    if response.get("status") == 401:
        raise CloudError("Aardvark API returned 401. Refresh Codex ChatGPT auth with codex login.")
    if response.get("status") == 403:
        raise CloudError("Aardvark API returned 403. Open ChatGPT in Chrome and retry.")
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
    print(f"auth_source={source}")
    print(f"access_token=present length={len(token)}")
    print(f"account_id={'present' if account_id else 'absent'}")
    doctor = run_host(["doctor"], timeout=20)
    ok = bool(isinstance(doctor, dict) and doctor.get("ok"))
    print(f"chrome_bridge={'ok' if ok else 'not_ok'}")
    if args.probe:
        path = "/backend-api/aardvark/scan-findings/list-accessible-repos?force_refresh=false"
        response = api_get(path, session=args.session, turn=args.turn)
        body = response.get("body")
        keys = sorted(body.keys()) if isinstance(body, dict) else []
        print(f"probe_status={response.get('status')} body_keys={','.join(keys)}")
    return 0


def command_list_repos(args: argparse.Namespace) -> int:
    path = "/backend-api/aardvark/scan-findings/list-accessible-repos?force_refresh=false"
    response = api_get(path, session=args.session, turn=args.turn)
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
    response = api_get(path, session=args.session, turn=args.turn)
    body = response.get("body")
    if args.format == "json":
        print(json.dumps(body, indent=2, sort_keys=True))
    else:
        print_findings_summary(body if isinstance(body, dict) else {"body": body})
    return 0


def command_get_finding(args: argparse.Namespace) -> int:
    finding_id = args.finding_id.strip()
    path = f"/backend-api/aardvark/scan-findings/{finding_id}"
    response = api_get(path, session=args.session, turn=args.turn)
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
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Chrome browser-control session name")
    parser.add_argument("--turn", default=DEFAULT_TURN, help="Chrome browser-control turn name")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query Codex Security Cloud findings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local auth and Chrome bridge readiness")
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
    except (CloudError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
