#!/usr/bin/env python3
"""Link the Buck2 fork repo in BuildBuddy using the logged-in browser session."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time


DEFAULT_BUILDBUDDY_URL = "https://app.buildbuddy.io/workflows/new"
DEFAULT_GROUP_ID = "GR11680003611988151853"
DEFAULT_OWNER = "sluongng"
DEFAULT_REPO_URL = "https://github.com/sluongng/buck2"


def run_host(args: list[str], *, env: dict[str, str]) -> dict:
    proc = subprocess.run(
        ["codex-linux-extension-host", "--json", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    output = proc.stdout or proc.stderr
    if proc.returncode != 0:
        raise SystemExit(output.strip())
    if not output.strip() or output.strip() == "null":
        return {}
    return json.loads(output)


def runtime_evaluate(tab_id: int, expression: str, *, env: dict[str, str]) -> dict:
    params = json.dumps({"expression": expression, "awaitPromise": True, "returnByValue": True})
    result = run_host(
        [
            "cdp",
            "--tab-id",
            str(tab_id),
            "Runtime.evaluate",
            "--params",
            params,
        ],
        env=env,
    )
    value = result.get("result", {}).get("value")
    if not isinstance(value, dict):
        raise SystemExit(f"unexpected browser evaluation result: {result}")
    return value


def link_expression(group_id: str, owner: str, repo_url: str) -> str:
    return f"""
new Promise(resolve => setTimeout(async () => {{
  const svc = window._rpcService;
  if (!svc) return resolve({{ok: false, error: "missing _rpcService", href: location.href, title: document.title}});
  const restore = svc.overrideGroupId({json.dumps(group_id)});
  try {{
    const installs = await svc.service.getGitHubAppInstallations({{}});
    const linkedBefore = await svc.service.getLinkedGitHubRepos({{}});
    const alreadyLinked = (linkedBefore.repos || []).some(r => r.repoUrl === {json.dumps(repo_url)});
    if (alreadyLinked) {{
      return resolve({{ok: true, linked: true, changed: false}});
    }}
    const install = (installs.installations || []).find(i => i.owner === {json.dumps(owner)}) || {{}};
    if (!install.installationId) {{
      return resolve({{ok: false, error: "missing GitHub App installation for owner " + {json.dumps(owner)}}});
    }}
    const accessible = await svc.service.getAccessibleGitHubRepos({{installationId: install.installationId, query: "buck2"}});
    const repoUrls = accessible.repoUrls || [];
    if (!repoUrls.includes({json.dumps(repo_url)})) {{
      return resolve({{
        ok: false,
        linked: false,
        accessibleRepoUrls: repoUrls,
        error: "repository is not accessible through the BuildBuddy GitHub App installation"
      }});
    }}
    await svc.service.linkGitHubRepo({{repoUrl: {json.dumps(repo_url)}}});
    const linkedAfter = await svc.service.getLinkedGitHubRepos({{}});
    resolve({{
      ok: true,
      linked: (linkedAfter.repos || []).some(r => r.repoUrl === {json.dumps(repo_url)}),
      changed: true,
      linkedRepoUrls: (linkedAfter.repos || []).map(r => r.repoUrl)
    }});
  }} catch (e) {{
    resolve({{ok: false, error: String(e).slice(0, 1000)}});
  }} finally {{
    restore();
  }}
}}, 3000))
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buildbuddy-url", default=DEFAULT_BUILDBUDDY_URL)
    parser.add_argument("--group-id", default=DEFAULT_GROUP_ID)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--session", default="buck2-workflows")
    parser.add_argument("--turn", default=f"link-repo-{int(time.time())}")
    args = parser.parse_args()

    env = os.environ.copy()
    env["CODEX_CHROME_SESSION_ID"] = args.session
    env["CODEX_CHROME_TURN_ID"] = args.turn

    try:
        nav = run_host(["navigate", args.buildbuddy_url], env=env)
        tab_id = nav.get("tabId")
        if not isinstance(tab_id, int):
            raise SystemExit(f"could not determine Chrome tab id from: {nav}")
        result = runtime_evaluate(tab_id, link_expression(args.group_id, args.owner, args.repo_url), env=env)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") and result.get("linked") else 1
    finally:
        run_host(["turn-ended"], env=env)


if __name__ == "__main__":
    sys.exit(main())
