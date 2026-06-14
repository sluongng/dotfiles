#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://app.buildbuddy.io"


def run_git_config(key: str) -> str:
    try:
        p = subprocess.run(
            ["git", "config", "--local", "--get", key],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def infer_repo_url() -> str:
    url = run_git_config("remote.origin.url")
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url[len("git@github.com:") :]
    if url.endswith(".git"):
        url = url[:-4]
    return url


def get_api_key() -> str:
    for name in ("BUILDBUDDY_API_KEY", "BUILD_BUDDY_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return run_git_config("buildbuddy.api-key")


def parse_time(value: str) -> dt.datetime:
    raw = value.strip()
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        parsed = dt.datetime.combine(dt.date.fromisoformat(raw), dt.time.min)
        return parsed.replace(tzinfo=dt.timezone.utc)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_timezone_offset_minutes() -> int:
    offset = dt.datetime.now().astimezone().utcoffset()
    if offset is None:
        return 0
    return -int(offset.total_seconds() // 60)


class BuildBuddyClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def rpc(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/rpc/BuildBuddyService/{method}"
        body = json.dumps(payload, separators=(",", ":")).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-buildbuddy-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:2000]
            raise RuntimeError(f"{method} failed with HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"{method} failed: {e}") from e


def request_context(group_id: str, tz_offset: int, timezone: str) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "timezoneOffsetMinutes": tz_offset,
    }
    if group_id:
        ctx["groupId"] = group_id
    if timezone:
        ctx["timezone"] = timezone
    return ctx


def first_nonempty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def resolve_group_id(client: BuildBuddyClient, args: argparse.Namespace) -> str:
    group_id = first_nonempty(args.group_id, os.environ.get("BUILDBUDDY_GROUP_ID"), os.environ.get("BUILD_BUDDY_GROUP_ID"))
    if group_id:
        return group_id

    org_slug = first_nonempty(args.org_slug, os.environ.get("BUILDBUDDY_ORG_SLUG"), os.environ.get("BUILD_BUDDY_ORG_SLUG"))
    if org_slug:
        rsp = client.rpc("GetGroup", {"requestContext": {}, "urlIdentifier": org_slug})
        group_id = first_nonempty(rsp.get("id"), rsp.get("groupId"))
        if group_id:
            return group_id
        raise RuntimeError(f"GetGroup did not return a group id for org slug {org_slug!r}")

    rsp = client.rpc("GetUser", {"requestContext": {}})
    selected = rsp.get("selectedGroup") or rsp.get("selected_group") or {}
    group_id = first_nonempty(selected.get("groupId"), selected.get("group_id"), rsp.get("selectedGroupId"), rsp.get("selected_group_id"))
    if group_id:
        return group_id
    for group in rsp.get("userGroup", []) or rsp.get("user_group", []) or []:
        group_id = first_nonempty(group.get("id"), group.get("groupId"), group.get("group_id"))
        if group_id:
            return group_id
    raise RuntimeError("Could not infer group ID. Pass --group-id GR... or --org-slug <url-identifier>.")


def as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def enrich_stat(stat: dict[str, Any]) -> dict[str, Any]:
    data = stat.get("data") or {}
    flaky = as_int(data.get("flakyRuns"))
    likely = as_int(data.get("likelyFlakyRuns"))
    total = as_int(data.get("totalRuns"))
    runtime = as_int(data.get("totalFlakeRuntimeUsec"))
    out = dict(stat)
    out["metrics"] = {
        "flakyRuns": flaky,
        "likelyFlakyRuns": likely,
        "totalFlakes": flaky + likely,
        "totalRuns": total,
        "failedRuns": as_int(data.get("failedRuns")),
        "flakePercent": (flaky + likely) / total if total else 0,
        "totalFlakeRuntimeUsec": runtime,
    }
    return out


def sort_stats(stats: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    def key(stat: dict[str, Any]) -> tuple[Any, ...]:
        m = stat["metrics"]
        if sort == "flake-percent":
            return (m["flakePercent"], m["totalFlakes"], m["totalRuns"])
        if sort == "flaky-runs":
            return (m["flakyRuns"], m["likelyFlakyRuns"], m["totalRuns"])
        if sort == "runtime":
            return (m["totalFlakeRuntimeUsec"], m["totalFlakes"], m["totalRuns"])
        return (m["totalFlakes"], m["flakyRuns"], m["likelyFlakyRuns"], m["totalRuns"])

    return sorted(stats, key=key, reverse=True)


def sample_summary(sample: dict[str, Any], base_url: str) -> dict[str, Any]:
    event = sample.get("event") or {}
    test_result = event.get("testResult") or {}
    outputs = []
    for output in test_result.get("testActionOutput", []) or []:
        outputs.append({"name": output.get("name", ""), "uri": output.get("uri", "")})
    invocation_id = sample.get("invocationId", "")
    return {
        "status": sample.get("status", ""),
        "invocationId": invocation_id,
        "invocationUrl": f"{base_url.rstrip('/')}/invocation/{invocation_id}" if invocation_id else "",
        "invocationStartTimeUsec": sample.get("invocationStartTimeUsec", ""),
        "testActionOutput": outputs,
    }


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def print_markdown(result: dict[str, Any]) -> None:
    query = result["query"]
    print("# BuildBuddy flaky tests")
    print()
    print(f"- Window: `{query['startedAfter']}` to `{query['startedBefore']}`")
    print(f"- Repo: `{query.get('repo') or '<all>'}`")
    print(f"- Branch: `{query.get('branchName') or '<all>'}`")
    print(f"- Sort: `{result['sort']}`")
    print()
    stats = result["stats"]
    if not stats:
        print("No flaky targets found for this window.")
        return

    print("| Rank | Label | Total flakes | Flaky | Likely | Total runs | Flake % | Sample invocations |")
    print("| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for i, stat in enumerate(stats, start=1):
        m = stat["metrics"]
        samples = stat.get("samples") or []
        sample_links = ", ".join(f"[{s['invocationId']}]({s['invocationUrl']})" for s in samples if s.get("invocationId"))
        print(
            f"| {i} | `{stat.get('label', '')}` | {m['totalFlakes']} | {m['flakyRuns']} | "
            f"{m['likelyFlakyRuns']} | {m['totalRuns']} | {pct(m['flakePercent'])} | {sample_links or ''} |"
        )

    daily = result.get("dailyStats") or []
    if daily:
        print()
        print("## Daily totals")
        print()
        print("| Date | Total flakes | Flaky | Likely | Total runs |")
        print("| --- | ---: | ---: | ---: | ---: |")
        for row in daily:
            m = enrich_stat({"data": row.get("data") or {}})["metrics"]
            print(f"| {row.get('date', '')} | {m['totalFlakes']} | {m['flakyRuns']} | {m['likelyFlakyRuns']} | {m['totalRuns']} |")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch recent BuildBuddy flaky-test stats.")
    parser.add_argument("--base-url", default=os.environ.get("BUILDBUDDY_BASE_URL") or os.environ.get("BUILD_BUDDY_BASE_URL") or DEFAULT_BASE_URL)
    parser.add_argument("--group-id", default="")
    parser.add_argument("--org-slug", default="")
    parser.add_argument("--repo", default="auto", help="Repo URL filter, 'auto' from git remote, or empty for all repos.")
    parser.add_argument("--branch", default="", help="Branch filter, for example master or main.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--started-after", default="")
    parser.add_argument("--started-before", default="")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--samples-for-top", type=int, default=3, help="Number of top target labels to fetch sample invocations for.")
    parser.add_argument("--sort", choices=("total-flakes", "flake-percent", "flaky-runs", "runtime"), default="total-flakes")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--out", default="", help="Optional path for the full JSON result.")
    parser.add_argument("--timezone", default=os.environ.get("TZ", ""))
    parser.add_argument("--timezone-offset-minutes", type=int, default=local_timezone_offset_minutes())
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("No BuildBuddy API key found. Run `bb login` in this repo or set BUILDBUDDY_API_KEY.", file=sys.stderr)
        return 2

    before = parse_time(args.started_before) if args.started_before else dt.datetime.now(dt.timezone.utc)
    after = parse_time(args.started_after) if args.started_after else before - dt.timedelta(days=args.days)
    repo = infer_repo_url() if args.repo == "auto" else args.repo

    client = BuildBuddyClient(args.base_url, api_key)
    try:
        group_id = resolve_group_id(client, args)
        ctx = request_context(group_id, args.timezone_offset_minutes, args.timezone)
        base_payload: dict[str, Any] = {
            "requestContext": ctx,
            "repo": repo,
            "branchName": args.branch,
            "startedAfter": iso_z(after),
            "startedBefore": iso_z(before),
        }
        stats_rsp = client.rpc("GetTargetStats", base_payload)
        daily_rsp = client.rpc("GetDailyTargetStats", base_payload)

        stats = [enrich_stat(s) for s in stats_rsp.get("stats", [])]
        stats = sort_stats(stats, args.sort)[: args.limit]

        sample_count = max(0, min(args.samples_for_top, len(stats)))
        for stat in stats[:sample_count]:
            sample_payload = dict(base_payload)
            sample_payload["label"] = stat.get("label", "")
            sample_rsp = client.rpc("GetTargetFlakeSamples", sample_payload)
            stat["samples"] = [sample_summary(s, args.base_url) for s in sample_rsp.get("samples", [])]
            if sample_rsp.get("nextPageToken"):
                stat["nextPageToken"] = sample_rsp["nextPageToken"]

        result = {
            "query": {
                "baseUrl": args.base_url,
                "groupId": group_id,
                "repo": repo,
                "branchName": args.branch,
                "startedAfter": iso_z(after),
                "startedBefore": iso_z(before),
                "timezoneOffsetMinutes": args.timezone_offset_minutes,
                "timezone": args.timezone,
            },
            "sort": args.sort,
            "stats": stats,
            "dailyStats": daily_rsp.get("stats", []),
        }
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")

    if args.format == "json":
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        print()
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
