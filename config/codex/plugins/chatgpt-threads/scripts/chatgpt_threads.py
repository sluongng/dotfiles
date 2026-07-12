#!/usr/bin/env python3
"""Inspect logged-in ChatGPT threads through the local Chrome Bridge."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from typing import Any


HOST = "codex-linux-extension-host"
DEFAULT_SESSION = "chatgpt-threads"
THREAD_URL_RE = re.compile(
    r"https://chatgpt\.com/(?:g/([^/?#]+)/)?c/([0-9a-fA-F-]{20,})(?:[/?#].*)?$"
)
THREAD_URL_SEARCH_RE = re.compile(
    r"https://chatgpt\.com/(?:g/([^/?#]+)/)?c/([0-9a-fA-F-]{20,})"
)
UUIDISH_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}")


ACCOUNT_HINT_JS = r"""
(() => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const selectors = [
    '[data-testid="profile-button"]',
    '[data-testid="user-menu-button"]',
    '[data-testid="account-menu-button"]',
    'button[aria-label="Open profile menu"]',
    'button[aria-label*="open profile" i]',
    'button[aria-label*="account menu" i]'
  ];
  const labels = [];
  for (const selector of selectors) {
    for (const el of document.querySelectorAll(selector)) {
      const value = clean(el.innerText || el.getAttribute("aria-label") || el.title || "");
      if (value && !labels.includes(value)) labels.push(value);
    }
  }
  return {
    title: document.title || "",
    url: location.href,
    account_label: labels[0] || null
  };
})()
"""


SIDEBAR_JS = r"""
(() => {
  const out = [];
  const seen = new Set();
  const anchors = Array.from(document.querySelectorAll('a[href*="/c/"]'));
  for (const a of anchors) {
    const href = a.href || "";
    const match = href.match(/https:\/\/chatgpt\.com\/(?:g\/([^/?#]+)\/)?c\/([0-9a-fA-F-]{20,})/);
    if (!match) continue;
    const id = match[2];
    if (seen.has(id)) continue;
    const title = (a.innerText || a.getAttribute("aria-label") || a.title || "")
      .replace(/\s+/g, " ")
      .trim();
    if (!title) continue;
    seen.add(id);
    out.push({
      id,
      project: match[1] || null,
      title,
      url: href
    });
  }
  return out;
})()
"""


THREAD_JS = r"""
(() => {
  const normalize = (s) => (s || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  const blocks = Array.from(
    document.querySelectorAll("[data-message-author-role][data-message-id]")
  );
  const messages = blocks.map((el, index) => ({
    index,
    id: el.getAttribute("data-message-id"),
    role: el.getAttribute("data-message-author-role"),
    text: normalize(el.innerText || "")
  }));
  const urlMatch = location.href.match(/https:\/\/chatgpt\.com\/(?:g\/([^/?#]+)\/)?c\/([0-9a-fA-F-]{20,})/);
  return {
    title: document.title || "",
    url: location.href,
    conversation_id: urlMatch ? urlMatch[2] : null,
    project: urlMatch ? (urlMatch[1] || null) : null,
    captured_at: new Date().toISOString(),
    message_count: messages.length,
    messages
  };
})()
"""


class CliError(RuntimeError):
    pass


def parse_json_output(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise CliError(f"{HOST} returned non-JSON output")


def run_host(args: list[str], *, input_text: str | None = None, timeout: int = 30) -> Any:
    proc = subprocess.run(
        [HOST, "--json", *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "").strip()
        if detail:
            try:
                parsed = json.loads(detail)
                detail = parsed.get("error") or parsed.get("message") or detail
            except json.JSONDecodeError:
                pass
        raise CliError(detail or f"{HOST} exited with status {proc.returncode}")
    return parse_json_output(proc.stdout)


def session_args(args: argparse.Namespace) -> list[str]:
    return ["--session", args.session, "--turn", args.turn]


def socket_args(args: argparse.Namespace) -> list[str]:
    socket_path = getattr(args, "socket_path", None)
    if not socket_path:
        return []
    return ["--socket-path", socket_path]


def tabs(args: argparse.Namespace) -> list[dict[str, Any]]:
    data = run_host(["tabs", *socket_args(args), *session_args(args)])
    if not isinstance(data, list):
        raise CliError("Chrome Bridge tabs response was not a list")
    return data


def is_chatgpt_tab(tab: dict[str, Any]) -> bool:
    url = str(tab.get("url") or "")
    return url.startswith("https://chatgpt.com/")


def chatgpt_tabs(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [tab for tab in tabs(args) if is_chatgpt_tab(tab)]


def tab_matches(tab: dict[str, Any], selector: str) -> bool:
    needle = selector.casefold()
    fields = [
        str(tab.get("id") or ""),
        str(tab.get("title") or ""),
        str(tab.get("url") or ""),
    ]
    return any(needle in field.casefold() for field in fields)


def select_chatgpt_tab(args: argparse.Namespace) -> dict[str, Any] | None:
    visible = chatgpt_tabs(args)
    tab_id = getattr(args, "tab_id", None)
    if tab_id is not None:
        for tab in visible:
            if int(tab.get("id") or -1) == int(tab_id):
                return tab
        raise CliError(f"ChatGPT tab {tab_id} was not found in the selected Chrome Bridge profile.")

    tab_match = getattr(args, "tab_match", None)
    if tab_match:
        matches = [tab for tab in visible if tab_matches(tab, tab_match)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            ids = ", ".join(str(tab.get("id")) for tab in matches)
            raise CliError(f"Tab selector {tab_match!r} matched multiple ChatGPT tabs: {ids}. Use --tab-id.")
        raise CliError(f"Tab selector {tab_match!r} did not match any visible ChatGPT tab.")

    if len(visible) <= 1:
        return visible[0] if visible else None

    ids = ", ".join(f"{tab.get('id')} ({tab.get('title')})" for tab in visible)
    raise CliError(
        f"Multiple visible ChatGPT tabs found: {ids}. "
        "Run list-tabs and pass --tab-id or --tab-match to choose the intended profile/account."
    )


def claim_and_attach(args: argparse.Namespace, tab_id: int) -> None:
    try:
        run_host(["claim-tab", *socket_args(args), *session_args(args), "--tab-id", str(tab_id)])
    except CliError as exc:
        message = str(exc)
        same_session = f"already part of browser session {args.session}" in message
        if not same_session:
            raise CliError(
                f"Could not claim tab {tab_id}: {message}. "
                "If another Bridge session owns it, end that session or open a fresh ChatGPT tab."
            ) from exc
    run_host(["attach", *socket_args(args), *session_args(args), "--tab-id", str(tab_id)])


def release_session(args: argparse.Namespace) -> None:
    try:
        run_host(["turn-ended", *socket_args(args), *session_args(args)], timeout=10)
    except Exception:
        pass


def cdp_eval(args: argparse.Namespace, tab_id: int, expression: str) -> Any:
    params = {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,
    }
    data = run_host(
        [
            "cdp",
            *socket_args(args),
            *session_args(args),
            "--tab-id",
            str(tab_id),
            "Runtime.evaluate",
            "--params",
            "-",
        ],
        input_text=json.dumps(params),
        timeout=max(30, args.timeout_ms // 1000 + 5),
    )
    if isinstance(data, dict) and data.get("exceptionDetails"):
        details = data["exceptionDetails"]
        text = details.get("text") or details.get("exception", {}).get("description")
        raise CliError(f"JavaScript evaluation failed: {text or details}")
    if not isinstance(data, dict) or "result" not in data:
        raise CliError("Unexpected CDP evaluation response")
    result = data["result"]
    if isinstance(result, dict) and "value" in result:
        return result["value"]
    if isinstance(result, dict) and "description" in result:
        return result["description"]
    return result


def navigate(args: argparse.Namespace, url: str, tab_id: int | None) -> dict[str, Any]:
    cmd = ["navigate", *socket_args(args), *session_args(args), "--timeout-ms", str(args.timeout_ms)]
    if tab_id is not None:
        cmd.extend(["--tab-id", str(tab_id)])
    cmd.append(url)
    data = run_host(cmd, timeout=max(30, args.timeout_ms // 1000 + 10))
    if not isinstance(data, dict):
        raise CliError("Chrome Bridge navigate response was not an object")
    return data


def wait_for_thread_data(args: argparse.Namespace, tab_id: int) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.0, args.wait)
    last: Any = None
    while True:
        last = cdp_eval(args, tab_id, THREAD_JS)
        if isinstance(last, dict) and int(last.get("message_count") or 0) > 0:
            return last
        if time.monotonic() >= deadline:
            break
        time.sleep(0.5)
    if not isinstance(last, dict):
        raise CliError("Thread extraction did not return an object")
    return last


def thread_id_from_value(value: str) -> str:
    match = THREAD_URL_SEARCH_RE.search(value)
    if match:
        return match.group(2)
    match = UUIDISH_RE.fullmatch(value.strip())
    if match:
        return value.strip()
    raise CliError(f"Could not parse ChatGPT thread id from {value!r}")


def thread_url_from_value(value: str) -> str:
    if THREAD_URL_RE.match(value):
        return value
    match = THREAD_URL_SEARCH_RE.search(value)
    if match:
        return match.group(0)
    return f"https://chatgpt.com/c/{thread_id_from_value(value)}"


def history_threads(args: argparse.Namespace) -> list[dict[str, Any]]:
    cmd = [
        "history",
        *socket_args(args),
        *session_args(args),
        "--query",
        args.query,
        "--limit",
        str(args.scan_limit),
    ]
    if args.from_:
        cmd.extend(["--from", args.from_])
    if args.to:
        cmd.extend(["--to", args.to])
    rows = run_host(cmd)
    if not isinstance(rows, list):
        raise CliError("Chrome Bridge history response was not a list")

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        url = str(row.get("url") or "")
        match = THREAD_URL_SEARCH_RE.search(url)
        if not match:
            continue
        thread_id = match.group(2)
        if thread_id in seen:
            continue
        seen.add(thread_id)
        out.append(
            {
                "id": thread_id,
                "project": match.group(1) or None,
                "title": row.get("title") or "",
                "url": match.group(0),
                "last_visited": row.get("dateVisited"),
            }
        )
        if len(out) >= args.limit:
            break
    return out


def summarize_text(text: str, limit: int) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    if len(one_line) <= limit:
        return one_line
    return one_line[: max(0, limit - 3)].rstrip() + "..."


def emit_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def emit_threads_summary(threads: list[dict[str, Any]], *, label: str) -> None:
    print(f"{label}: {len(threads)}")
    for thread in threads:
        visited = thread.get("last_visited")
        prefix = f"{visited} " if visited else ""
        print(f"- {prefix}{thread.get('id')}  {thread.get('title')}")
        print(f"  {thread.get('url')}")


def emit_tabs_summary(tabs_: list[dict[str, Any]], *, label: str) -> None:
    print(f"{label}: {len(tabs_)}")
    for tab in tabs_:
        account = tab.get("account_label")
        suffix = f"  account={account}" if account else ""
        print(f"- {tab.get('id')}  {tab.get('title')}{suffix}")
        print(f"  {tab.get('url')}")


def emit_thread_summary(thread: dict[str, Any], text_limit: int) -> None:
    print(f"Thread: {thread.get('title')}")
    print(f"URL: {thread.get('url')}")
    print(f"Conversation ID: {thread.get('conversation_id')}")
    print(f"Messages: {thread.get('message_count')}")
    for message in thread.get("messages", []):
        preview = summarize_text(str(message.get("text") or ""), text_limit)
        print(f"- [{message.get('index')}] {message.get('role')} {message.get('id')}: {preview}")


def bridge_info(args: argparse.Namespace) -> Any:
    return run_host(["info", *socket_args(args), *session_args(args)])


def annotate_tabs(args: argparse.Namespace, tabs_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not getattr(args, "inspect", False):
        return tabs_

    annotated = []
    for tab in tabs_:
        copy = dict(tab)
        tab_id = int(copy["id"])
        try:
            claim_and_attach(args, tab_id)
            hint = cdp_eval(args, tab_id, ACCOUNT_HINT_JS)
            if isinstance(hint, dict):
                copy.update(
                    {
                        "page_title": hint.get("title"),
                        "page_url": hint.get("url"),
                        "account_label": hint.get("account_label"),
                    }
                )
        except Exception as exc:
            copy["inspect_error"] = str(exc)
        finally:
            release_session(args)
        annotated.append(copy)
    return annotated


def cmd_doctor(args: argparse.Namespace) -> int:
    doctor = run_host(["doctor", *socket_args(args)])
    info = bridge_info(args)
    visible_tabs = chatgpt_tabs(args)
    data = {
        "bridge": doctor,
        "bridge_info": info,
        "chatgpt_tab_count": len(visible_tabs),
        "chatgpt_tabs": visible_tabs,
    }
    if args.format == "json":
        emit_json(data)
        return 0
    ok = not (isinstance(doctor, dict) and doctor.get("ok") is False)
    print(f"Bridge: {'ok' if ok else 'not ok'}")
    if isinstance(info, dict):
        metadata = info.get("metadata") if isinstance(info.get("metadata"), dict) else {}
        instance = metadata.get("extensionInstanceId")
        if instance:
            print(f"Extension instance: {instance}")
    emit_tabs_summary(visible_tabs, label="ChatGPT tabs")
    return 0


def cmd_list_tabs(args: argparse.Namespace) -> int:
    visible_tabs = annotate_tabs(args, chatgpt_tabs(args))
    if args.format == "json":
        emit_json({"tabs": visible_tabs, "count": len(visible_tabs), "bridge_info": bridge_info(args)})
    else:
        emit_tabs_summary(visible_tabs, label="ChatGPT tabs")
    return 0


def cmd_list_history(args: argparse.Namespace) -> int:
    threads = history_threads(args)
    if args.format == "json":
        emit_json({"threads": threads, "count": len(threads)})
    else:
        emit_threads_summary(threads, label="History threads")
    return 0


def cmd_list_sidebar(args: argparse.Namespace) -> int:
    tab = select_chatgpt_tab(args)
    if tab is None:
        raise CliError("No visible ChatGPT tab found. Open https://chatgpt.com/ in the intended Chrome profile.")
    tab_id = int(tab["id"])
    try:
        claim_and_attach(args, tab_id)
        threads = cdp_eval(args, tab_id, SIDEBAR_JS)
    finally:
        release_session(args)
    if not isinstance(threads, list):
        raise CliError("Sidebar extraction did not return a list")
    if args.format == "json":
        emit_json({"threads": threads, "count": len(threads), "tab": tab})
    else:
        emit_threads_summary(threads, label="Visible sidebar threads")
    return 0


def extract_thread(args: argparse.Namespace, *, thread_url: str | None) -> dict[str, Any]:
    tab_id = getattr(args, "tab_id", None)
    tab = None
    if tab_id is None:
        tab = select_chatgpt_tab(args)
        if tab is not None:
            tab_id = int(tab["id"])

    try:
        if tab_id is not None:
            claim_and_attach(args, tab_id)
            if thread_url:
                navigate(args, thread_url, tab_id)
        elif thread_url:
            tab = navigate(args, thread_url, None)
            tab_id = int(tab["id"])
            run_host(["attach", *socket_args(args), *session_args(args), "--tab-id", str(tab_id)])
        else:
            raise CliError("No visible ChatGPT tab found. Open https://chatgpt.com/ first.")

        data = wait_for_thread_data(args, tab_id)
    finally:
        release_session(args)

    return data


def cmd_current_thread(args: argparse.Namespace) -> int:
    thread = extract_thread(args, thread_url=None)
    if args.format == "json":
        emit_json(thread)
    else:
        emit_thread_summary(thread, args.text_limit)
    return 0


def cmd_get_thread(args: argparse.Namespace) -> int:
    url = thread_url_from_value(args.thread)
    thread = extract_thread(args, thread_url=url)
    if args.format == "json":
        emit_json(thread)
    else:
        emit_thread_summary(thread, args.text_limit)
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--socket-path", help="Chrome Bridge socket path for a specific extension/backend instance")
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Chrome Bridge session name")
    parser.add_argument("--turn", default="chatgpt-threads-cli", help="Chrome Bridge turn name")
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    parser.add_argument("--timeout-ms", type=int, default=10000, help="Chrome Bridge command timeout")


def add_tab_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tab-id", type=int, help="Specific visible ChatGPT tab id")
    parser.add_argument("--tab-match", help="Substring to match against visible ChatGPT tab id, title, or URL")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check Chrome Bridge and visible ChatGPT tabs")
    add_common(doctor)
    doctor.set_defaults(func=cmd_doctor)

    list_tabs = subparsers.add_parser("list-tabs", help="List visible ChatGPT tabs for profile/account selection")
    add_common(list_tabs)
    list_tabs.add_argument("--inspect", action="store_true", help="Inspect each tab for a visible ChatGPT account label")
    list_tabs.set_defaults(func=cmd_list_tabs)

    history = subparsers.add_parser("list-history", help="List ChatGPT threads from Chrome history")
    add_common(history)
    history.add_argument("--query", default="chatgpt.com", help="Chrome history query")
    history.add_argument("--from", dest="from_", help="Start timestamp for Chrome history search")
    history.add_argument("--to", help="End timestamp for Chrome history search")
    history.add_argument("--limit", type=int, default=25, help="Maximum deduplicated threads to print")
    history.add_argument("--scan-limit", type=int, default=200, help="Maximum raw history entries to scan")
    history.set_defaults(func=cmd_list_history)

    sidebar = subparsers.add_parser("list-sidebar", help="List visible ChatGPT sidebar threads")
    add_common(sidebar)
    add_tab_selection(sidebar)
    sidebar.set_defaults(func=cmd_list_sidebar)

    current = subparsers.add_parser("current-thread", help="Extract the current ChatGPT thread")
    add_common(current)
    add_tab_selection(current)
    current.add_argument("--wait", type=float, default=3.0, help="Maximum seconds to wait for messages")
    current.add_argument("--text-limit", type=int, default=220, help="Summary preview length per message")
    current.set_defaults(func=cmd_current_thread)

    get_thread = subparsers.add_parser("get-thread", help="Navigate to and extract a ChatGPT thread")
    add_common(get_thread)
    get_thread.add_argument("thread", help="ChatGPT thread id or URL")
    add_tab_selection(get_thread)
    get_thread.add_argument("--wait", type=float, default=8.0, help="Maximum seconds to wait for messages after navigation")
    get_thread.add_argument("--text-limit", type=int, default=220, help="Summary preview length per message")
    get_thread.set_defaults(func=cmd_get_thread)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (CliError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
