#!/usr/bin/env python3
"""Maintain the Buck2 stack and bazel-rbe-style merge branch."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WORKFLOW_HARNESS_PATHS = (
    "buildbuddy.yaml",
    ".buckconfig.buildbuddy",
    "buildbuddy/BUCK",
    "buildbuddy/defs.bzl",
    "buildbuddy/run_buck2_test_matrix.sh",
    "shim/BUCK",
    "shim/git_fetch.bzl",
    "shim/rust-toolchain",
    "shim/rust_toolchain.bzl",
    "shim/third-party/rust/BUCK.reindeer",
)


def quote(argv: list[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


class Git:
    def __init__(self, repo: Path, dry_run: bool) -> None:
        self.repo = repo
        self.dry_run = dry_run

    def run(self, args: list[str], *, capture: bool = False, check: bool = True) -> str:
        cmd = ["git", *args]
        if self.dry_run and not capture:
            print(f"+ {quote(cmd)}")
            return ""
        proc = subprocess.run(
            cmd,
            cwd=self.repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
        if check and proc.returncode != 0:
            if capture:
                sys.stderr.write(proc.stdout)
                sys.stderr.write(proc.stderr)
            raise subprocess.CalledProcessError(proc.returncode, cmd)
        return proc.stdout.strip() if capture else ""

    def ref(self, refname: str) -> str:
        return self.run(["rev-parse", "--verify", refname], capture=True)

    def maybe_ref(self, refname: str) -> str | None:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", refname],
            cwd=self.repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()


class BuildBuddyWorkflowError(SystemExit):
    def __init__(self, returncode: int, output: str = "") -> None:
        super().__init__(returncode)
        self.returncode = returncode
        self.output = output


def require_tracked_clean(git: Git) -> None:
    dirty = git.run(["status", "--porcelain", "--untracked-files=no"], capture=True)
    if dirty:
        raise SystemExit(f"Tracked worktree changes must be handled first:\n{dirty}")


def fetch_ref(git: Git, remote: str, branch: str) -> None:
    git.run(["fetch", "--no-tags", remote, f"refs/heads/{branch}:refs/remotes/{remote}/{branch}"])


def local_ref(remote: str, branch: str) -> str:
    return f"refs/remotes/{remote}/{branch}"


def checkout_stack(git: Git, args: argparse.Namespace, source_ref: str) -> None:
    git.run(["checkout", "-B", args.work_stack_branch, source_ref])
    git.run(["rebase", "--rebase-merges", args.upstream_ref])


def rebase_conflict_message(git: Git, error: subprocess.CalledProcessError) -> str:
    conflicts = git.run(["diff", "--name-only", "--diff-filter=U"], capture=True, check=False)
    lines = [
        f"Rebase failed while running: {quote(error.cmd)}",
        "Resolve the conflicted stack commit, then continue with:",
        "  git add <resolved-files>",
        "  GIT_EDITOR=true git rebase --continue",
        "",
        "Or abort with:",
        "  git rebase --abort",
    ]
    if conflicts:
        lines.extend(["", "Conflicted paths:", conflicts])
    return "\n".join(lines)


def commits_between(git: Git, base_ref: str, tip_ref: str, limit: int = 0) -> list[str]:
    output = git.run(
        ["rev-list", "--reverse", f"{base_ref}..{tip_ref}"],
        capture=True,
    )
    commits = [line for line in output.splitlines() if line]
    if limit:
        commits = commits[:limit]
    return commits


def commit_subject(git: Git, commit: str) -> str:
    return git.run(["log", "-1", "--format=%s", commit], capture=True)


def has_staged_changes(git: Git) -> bool:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=git.repo,
        check=False,
    )
    if proc.returncode == 0:
        return False
    if proc.returncode == 1:
        return True
    raise subprocess.CalledProcessError(proc.returncode, ["git", "diff", "--cached", "--quiet"])


def overlay_workflow_harness(git: Git, args: argparse.Namespace) -> None:
    if not args.workflow_harness_paths:
        return
    git.run(["checkout", args.workflow_harness_ref, "--", *args.workflow_harness_paths])
    git.run(["add", "--", *args.workflow_harness_paths])
    if has_staged_changes(git):
        git.run(["commit", "--amend", "--no-edit"])


def create_merge_for_prefix(git: Git, args: argparse.Namespace, prefix_commit: str) -> str:
    git.run(["checkout", "-B", args.work_merge_branch, args.upstream_ref])
    git.run(["merge", "--no-ff", "--no-edit", prefix_commit])
    overlay_workflow_harness(git, args)
    merge_sha = git.ref("HEAD")
    first_parent = git.ref("HEAD^1")
    second_parent = git.ref("HEAD^2")
    upstream_sha = git.ref(args.upstream_ref)
    if first_parent != upstream_sha:
        raise SystemExit(f"Bad merge first parent: {first_parent} != {upstream_sha}")
    if second_parent != prefix_commit:
        raise SystemExit(f"Bad merge second parent: {second_parent} != {prefix_commit}")
    return merge_sha


def backup_remote_main(git: Git, args: argparse.Namespace, expected_main: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = f"refs/heads/backup/buck2-main-before-stack-sync-{timestamp}"
    git.run(["push", args.fork_remote, f"{expected_main}:{backup}"])
    print(f"Backed up {args.fork_remote}/{args.merge_branch} to {backup}")


def push_main(git: Git, args: argparse.Namespace, expected_old: str) -> str:
    merge_sha = git.ref("HEAD")
    lease = f"refs/heads/{args.merge_branch}:{expected_old}"
    git.run([
        "push",
        f"--force-with-lease={lease}",
        args.fork_remote,
        f"HEAD:refs/heads/{args.merge_branch}",
    ])
    return merge_sha


def restore_main(
    git: Git,
    args: argparse.Namespace,
    expected_current: str,
    restore_to: str,
) -> None:
    lease = f"refs/heads/{args.merge_branch}:{expected_current}"
    git.run([
        "push",
        f"--force-with-lease={lease}",
        args.fork_remote,
        f"{restore_to}:refs/heads/{args.merge_branch}",
    ])
    print(f"Restored {args.fork_remote}/{args.merge_branch} to {restore_to}")


def push_stack(git: Git, args: argparse.Namespace) -> None:
    git.run([
        "push",
        "--force-with-lease",
        args.fork_remote,
        f"{args.work_stack_branch}:refs/heads/{args.stack_branch}",
    ])


def run_buildbuddy(
    args: argparse.Namespace,
    merge_sha: str,
    prefix_sha: str,
    *,
    poll: bool,
    capture_output: bool = False,
) -> None:
    script = Path(__file__).with_name("buildbuddy_workflow.py")
    cmd = [
        sys.executable,
        str(script),
        "--repo-url",
        args.repo_url,
        "--branch",
        args.merge_branch,
        "--commit-sha",
        merge_sha,
        "--action-name",
        args.action_name,
        "--env",
        f"BUCK2_STACK_PREFIX={prefix_sha}",
        "--env",
        f"BUCK2_UPSTREAM={args.upstream_sha}",
    ]
    if poll:
        cmd.append("--poll")
    print(f"+ {quote(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=args.repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
    )
    if capture_output and proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise BuildBuddyWorkflowError(proc.returncode, proc.stdout or "")


def is_buildbuddy_repo_not_found(args: argparse.Namespace, output: str) -> bool:
    return (
        "ExecuteWorkflow failed" in output
        and "repo " in output
        and " not found" in output
        and (args.repo_url in output or f"{args.repo_url}.git" in output)
    )


def attempt_link_buildbuddy_repo(args: argparse.Namespace) -> bool:
    script = Path(__file__).with_name("buildbuddy_link_repo_browser.py")
    cmd = [
        sys.executable,
        str(script),
        "--repo-url",
        args.repo_url,
    ]
    print("Attempting to link the repository in BuildBuddy before retrying preflight", flush=True)
    print(f"+ {quote(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=args.repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stdout.write("\n")
    return proc.returncode == 0


def preflight_buildbuddy(args: argparse.Namespace, current_merge_sha: str) -> None:
    print("Preflighting BuildBuddy workflow setup before rewriting fork/main", flush=True)
    try:
        run_buildbuddy(args, current_merge_sha, current_merge_sha, poll=False, capture_output=True)
        return
    except BuildBuddyWorkflowError as e:
        if not args.attempt_buildbuddy_link or not is_buildbuddy_repo_not_found(args, e.output):
            raise
        if not attempt_link_buildbuddy_repo(args):
            raise
    print("Retrying BuildBuddy workflow preflight after repository link attempt", flush=True)
    run_buildbuddy(args, current_merge_sha, current_merge_sha, poll=False)


def verify_current_merge(git: Git, args: argparse.Namespace) -> None:
    first_parent = git.ref(f"{args.merge_ref}^1")
    second_parent = git.ref(f"{args.merge_ref}^2")
    upstream_sha = git.ref(args.upstream_ref)
    stack_sha = git.ref(args.stack_ref)
    if first_parent != upstream_sha:
        raise SystemExit(f"Bad remote merge first parent: {first_parent} != {upstream_sha}")
    if second_parent != stack_sha:
        raise SystemExit(f"Bad remote merge second parent: {second_parent} != {stack_sha}")
    print(f"Verified {args.merge_ref} first-parent={upstream_sha[:12]} second-parent={stack_sha[:12]}")


def current_merge_validated_prefix(git: Git, args: argparse.Namespace, commits: list[str]) -> int:
    if not args.push or not args.wait_buildbuddy:
        return 0
    try:
        first_parent = git.ref(f"{args.merge_ref}^1")
        second_parent = git.ref(f"{args.merge_ref}^2")
    except subprocess.CalledProcessError:
        return 0
    if first_parent != args.upstream_sha:
        return 0
    try:
        index = commits.index(second_parent)
    except ValueError:
        return 0
    return index + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print the plan without mutating branches")
    mode.add_argument("--apply", action="store_true", help="Create local stack and merge commits")
    mode.add_argument(
        "--check-buildbuddy-setup",
        action="store_true",
        help="Verify the current fork/main invariant and preflight BuildBuddy without rewriting branches",
    )
    parser.add_argument("--push", action="store_true", help="Push fork/main prefixes and fork/stack")
    parser.add_argument("--wait-buildbuddy", action="store_true", help="Trigger and poll BuildBuddy after each push")
    parser.add_argument(
        "--leave-failed-main",
        action="store_true",
        help=(
            "When a polled BuildBuddy workflow fails after pushing a prefix merge, "
            "leave fork/main on the failing prefix instead of restoring the previous head."
        ),
    )
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--upstream-remote", default="origin")
    parser.add_argument("--upstream-branch", default="main")
    parser.add_argument("--fork-remote", default="fork")
    parser.add_argument("--stack-branch", default="stack")
    parser.add_argument("--merge-branch", default="main")
    parser.add_argument("--bootstrap-from", default="")
    parser.add_argument("--source-ref", default="", help="Use this ref instead of fork/stack")
    parser.add_argument("--work-stack-branch", default=f"stack-work-{os.getpid()}")
    parser.add_argument("--work-merge-branch", default=f"merge-work-{os.getpid()}")
    parser.add_argument("--repo-url", default="https://github.com/sluongng/buck2")
    parser.add_argument("--action-name", default="Buck2 Stack Test")
    parser.add_argument(
        "--attempt-buildbuddy-link",
        action="store_true",
        help=(
            "When preflight reports that the BuildBuddy workflow repo is not linked, "
            "run buildbuddy_link_repo_browser.py once and retry the preflight."
        ),
    )
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--workflow-harness-ref",
        default="",
        help="Ref to copy BuildBuddy workflow harness files from. Defaults to the rebased stack tip.",
    )
    parser.add_argument(
        "--workflow-harness-path",
        action="append",
        default=[],
        help="Workflow harness path to copy onto each prefix merge. Repeat to override the default path list.",
    )
    parser.add_argument(
        "--no-workflow-harness-overlay",
        action="store_true",
        help="Do not amend prefix merge commits with workflow harness files from the stack tip.",
    )
    args = parser.parse_args()
    args.repo = Path(args.repo).resolve()
    args.upstream_ref = local_ref(args.upstream_remote, args.upstream_branch)
    args.stack_ref = local_ref(args.fork_remote, args.stack_branch)
    args.merge_ref = local_ref(args.fork_remote, args.merge_branch)
    if args.no_workflow_harness_overlay:
        args.workflow_harness_paths = []
    elif not args.workflow_harness_path:
        args.workflow_harness_paths = list(DEFAULT_WORKFLOW_HARNESS_PATHS)
    else:
        args.workflow_harness_paths = args.workflow_harness_path
    return args


def main() -> int:
    args = parse_args()
    git = Git(args.repo, dry_run=args.dry_run)
    if args.apply:
        require_tracked_clean(git)

    if not args.skip_fetch:
        fetch_ref(git, args.upstream_remote, args.upstream_branch)
        fetch_ref(git, args.fork_remote, args.merge_branch)
        try:
            fetch_ref(git, args.fork_remote, args.stack_branch)
        except subprocess.CalledProcessError:
            if not args.bootstrap_from:
                raise SystemExit(f"{args.fork_remote}/{args.stack_branch} is missing; pass --bootstrap-from once")
            print(f"{args.fork_remote}/{args.stack_branch} is missing; using {args.bootstrap_from}")

    source_ref = args.source_ref or args.stack_ref
    if git.maybe_ref(source_ref) is None:
        if not args.bootstrap_from:
            raise SystemExit(f"Missing {source_ref}; pass --bootstrap-from once")
        source_ref = args.bootstrap_from

    args.upstream_sha = git.ref(args.upstream_ref)
    expected_main = git.ref(args.merge_ref)

    print(f"Upstream: {args.upstream_ref} {args.upstream_sha}")
    print(f"Stack source: {source_ref}")
    print(f"Merge branch: {args.fork_remote}/{args.merge_branch} currently {expected_main}")

    if args.check_buildbuddy_setup:
        verify_current_merge(git, args)
        preflight_buildbuddy(args, expected_main)
        print("BuildBuddy setup check passed.")
        return 0

    if args.dry_run:
        print()
        print("Dry-run command sequence:")
        print(f"+ git checkout -B {shlex.quote(args.work_stack_branch)} {shlex.quote(source_ref)}")
        print(f"+ git rebase --rebase-merges {shlex.quote(args.upstream_ref)}")
        commits = commits_between(git, args.upstream_ref, source_ref, args.limit)
        if not args.workflow_harness_ref:
            args.workflow_harness_ref = source_ref
    else:
        try:
            checkout_stack(git, args, source_ref)
        except subprocess.CalledProcessError as e:
            if len(e.cmd) >= 2 and e.cmd[1] == "rebase":
                raise SystemExit(rebase_conflict_message(git, e)) from None
            raise
        commits = commits_between(git, args.upstream_ref, args.work_stack_branch, args.limit)
        if not args.workflow_harness_ref:
            args.workflow_harness_ref = args.work_stack_branch
    print(f"Stack prefixes to validate: {len(commits)}")
    if args.workflow_harness_paths:
        print(
            "Workflow harness overlay: "
            f"{args.workflow_harness_ref} -- {', '.join(args.workflow_harness_paths)}"
        )
    if not commits:
        return 0

    validated_prefixes = 0 if args.dry_run else current_merge_validated_prefix(git, args, commits)
    if validated_prefixes:
        print(
            f"Resuming after {validated_prefixes} prefix(es) already represented by "
            f"{args.fork_remote}/{args.merge_branch}"
        )
        commits = commits[validated_prefixes:]
        if not commits:
            print("All stack prefixes are already represented by the current merge branch.")
            if args.push and not args.dry_run:
                push_stack(git, args)
            print("Done.")
            return 0

    if args.push and args.wait_buildbuddy and not args.dry_run:
        preflight_buildbuddy(args, expected_main)

    if args.push and not args.dry_run:
        backup_remote_main(git, args, expected_main)

    for index, commit in enumerate(commits, start=1):
        subject = commit_subject(git, commit)
        print(f"[{index}/{len(commits)}] {commit[:12]} {subject}")
        if args.dry_run:
            print(f"+ git checkout -B {shlex.quote(args.work_merge_branch)} {shlex.quote(args.upstream_ref)}")
            print(f"+ git merge --no-ff --no-edit {shlex.quote(commit)}")
            if args.workflow_harness_paths:
                print(
                    f"+ git checkout {shlex.quote(args.workflow_harness_ref)} -- "
                    + " ".join(shlex.quote(path) for path in args.workflow_harness_paths)
                )
                print("+ git add -- " + " ".join(shlex.quote(path) for path in args.workflow_harness_paths))
                print("+ git commit --amend --no-edit  # if the workflow harness changed this merge tree")
            if args.push:
                print(
                    "+ git push "
                    f"--force-with-lease=refs/heads/{shlex.quote(args.merge_branch)}:<expected> "
                    f"{shlex.quote(args.fork_remote)} HEAD:refs/heads/{shlex.quote(args.merge_branch)}"
                )
                if args.wait_buildbuddy:
                    print("+ trigger and poll BuildBuddy for this prefix")
                    if not args.leave_failed_main:
                        print(
                            f"+ restore {shlex.quote(args.fork_remote)}/{shlex.quote(args.merge_branch)} "
                            "to the previous head if the polled workflow fails"
                        )
            continue
        merge_sha = create_merge_for_prefix(git, args, commit)
        print(f"  merge {merge_sha[:12]} first-parent={args.upstream_sha[:12]} second-parent={commit[:12]}")
        if args.push:
            previous_main = expected_main
            expected_main = push_main(git, args, expected_main)
            if args.wait_buildbuddy:
                try:
                    run_buildbuddy(args, merge_sha, commit, poll=True)
                except BuildBuddyWorkflowError:
                    if not args.leave_failed_main:
                        print(
                            f"BuildBuddy failed for {merge_sha[:12]}; restoring "
                            f"{args.fork_remote}/{args.merge_branch} to previous head",
                            flush=True,
                        )
                        restore_main(git, args, expected_main, previous_main)
                        expected_main = previous_main
                    raise

    if args.push and not args.dry_run:
        push_stack(git, args)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
