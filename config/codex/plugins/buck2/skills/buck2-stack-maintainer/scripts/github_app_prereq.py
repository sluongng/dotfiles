#!/usr/bin/env python3
"""Check GitHub-side prerequisites for Buck2 BuildBuddy Workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


DEFAULT_REPOSITORY = "sluongng/buck2"
DEFAULT_REPOSITORY_ID = "634428231"
DEFAULT_INSTALLATION_ID = "36994646"
DEFAULT_INSTALLATION_URL = "https://github.com/settings/installations/36994646"
DEFAULT_BUILDBUDDY_LINK_URL = "https://app.buildbuddy.io/workflows/new"


def gh_api(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["gh", "api", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout, proc.stderr


def load_repo(repository: str) -> dict:
    code, stdout, stderr = gh_api([f"/repos/{repository}"])
    if code != 0:
        raise SystemExit(f"failed to inspect GitHub repository {repository}:\n{stderr or stdout}")
    return json.loads(stdout)


def print_repo_status(repo: dict, expected_repo_id: str) -> None:
    repo_id = str(repo.get("id", ""))
    permissions = repo.get("permissions") or {}
    print(f"Repository: {repo.get('full_name')}")
    print(f"Repository id: {repo_id}")
    print(f"Admin permission: {bool(permissions.get('admin'))}")
    if repo_id != expected_repo_id:
        raise SystemExit(f"unexpected repository id: {repo_id} != {expected_repo_id}")


def attempt_add_repository(installation_id: str, repository_id: str) -> None:
    endpoint = f"/user/installations/{installation_id}/repositories/{repository_id}"
    code, stdout, stderr = gh_api(["-X", "PUT", endpoint, "--silent"])
    if code == 0:
        print("GitHub App installation now includes the repository.")
        return
    detail = stderr or stdout
    print("Failed to add repository to GitHub App installation:")
    print(detail.rstrip())
    raise SystemExit(code)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--repository-id", default=DEFAULT_REPOSITORY_ID)
    parser.add_argument("--installation-id", default=DEFAULT_INSTALLATION_ID)
    parser.add_argument("--installation-url", default=DEFAULT_INSTALLATION_URL)
    parser.add_argument("--buildbuddy-link-url", default=DEFAULT_BUILDBUDDY_LINK_URL)
    parser.add_argument(
        "--attempt-add",
        action="store_true",
        help="Attempt to add the repository to the GitHub App installation using gh auth",
    )
    args = parser.parse_args()

    repo = load_repo(args.repository)
    print_repo_status(repo, args.repository_id)
    print(f"GitHub App installation URL: {args.installation_url}")
    print(f"BuildBuddy link URL: {args.buildbuddy_link_url}")

    if args.attempt_add:
        attempt_add_repository(args.installation_id, args.repository_id)
        print("Next: link the repository in BuildBuddy, then run sync_stack.py --check-buildbuddy-setup.")
    else:
        print()
        print("If BuildBuddy still reports the repo as unknown, complete GitHub sudo-mode")
        print("in the installation URL above and grant the app access to this repository.")
        print("After that, link the repo in BuildBuddy and run sync_stack.py --check-buildbuddy-setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
