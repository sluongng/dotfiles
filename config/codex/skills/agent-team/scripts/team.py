#!/usr/bin/env python3
"""
agent-team: Planner -> Workers -> Judge using Codex MCP server.

Key properties:
- Each worker runs in a NEW referenced clone of the repo.
- Workers run with sandbox disabled + auto-accept:
    sandbox="danger-full-access"
    approval-policy="never"
- Integration happens in a separate integration clone so your main working tree stays untouched
  until the judge merges.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.mcp import MCPServerStdio  # pip install openai-agents


# -----------------------------
# Utilities
# -----------------------------

def run(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )

def git(args: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=cwd, check=check)

def require_git_clean(repo_root: Path) -> None:
    r = git(["status", "--porcelain"], cwd=repo_root)
    if r.stdout.strip():
        raise SystemExit(
            "Refusing to run: working tree has uncommitted changes.\n"
            "Commit/stash first so subagent clones have a clean base."
        )

def default_branch(repo_root: Path) -> str:
    r = git(["symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"], cwd=repo_root, check=False)
    ref = r.stdout.strip()
    if ref.startswith("origin/"):
        return ref.split("/", 1)[1]

    r = git(["branch", "--show-current"], cwd=repo_root, check=False)
    branch = r.stdout.strip()
    if branch:
        return branch

    return "main"

def sanitize_task_id(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:50] or "task"

def extract_json_object(text: str) -> Dict[str, Any]:
    """
    Pull the first JSON object from a blob of text.
    Expect planner/judge to output JSON, but this is resilient to extra prose.
    """
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in output.")
    blob = m.group(0)
    return json.loads(blob)

def calltool_text(result: Any) -> str:
    """
    Convert CallToolResult content to text.
    Works across minor SDK shape differences by duck-typing.
    """
    parts = getattr(result, "content", None)
    if not parts:
        return ""
    out: List[str] = []
    for p in parts:
        if isinstance(p, dict):
            if p.get("type") == "text":
                out.append(p.get("text", ""))
        else:
            # likely TextContent(type='text', text='...')
            t = getattr(p, "text", None)
            if isinstance(t, str):
                out.append(t)
    return "\n".join(out).strip()

def calltool_thread_id(result: Any) -> Optional[str]:
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        tid = sc.get("threadId") or sc.get("thread_id")
        if isinstance(tid, str):
            return tid
    # fallback: sometimes structuredContent may appear in meta
    meta = getattr(result, "meta", None)
    if isinstance(meta, dict):
        tid = meta.get("threadId")
        if isinstance(tid, str):
            return tid
    return None


# -----------------------------
# Data models
# -----------------------------

@dataclasses.dataclass
class Task:
    id: str
    title: str
    description: str
    scope: List[str]
    acceptance: List[str]
    test_commands: List[str]
    depends_on: List[str]

@dataclasses.dataclass
class WorkerResult:
    task_id: str
    status: str  # "done" | "blocked"
    summary: str
    commit_head: Optional[str]
    patch_path: Optional[Path]
    raw_output_path: Path


# -----------------------------
# Codex MCP calls
# -----------------------------

async def codex_call(
    server: MCPServerStdio,
    *,
    prompt: str,
    cwd: Path,
    approval_policy: str,
    sandbox: str,
    model: Optional[str] = None,
    base_instructions: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    args: Dict[str, Any] = {
        "prompt": prompt,
        "cwd": str(cwd),
        "approval-policy": approval_policy,
        "sandbox": sandbox,
        "include-plan-tool": True,
    }
    if model:
        args["model"] = model
    if base_instructions:
        args["base-instructions"] = base_instructions

    result = await server.call_tool("codex", args)
    text = calltool_text(result)
    thread_id = calltool_thread_id(result)
    return text, thread_id


# -----------------------------
# Planner / Judge prompts
# -----------------------------

def planner_prompt(user_task: str) -> str:
    return textwrap.dedent(f"""
    You are the PLANNER.

    Goal: decompose the user's request into a small set of subtasks that can be worked on mostly independently.
    Important constraints:
    - Minimize overlapping files between tasks.
    - Make tasks "worker-sized" (1-2 hours of focused work).
    - Include dependencies (depends_on) where unavoidable.
    - For each task specify a scope list (directories/files), acceptance criteria, and test commands.
    - Output MUST be valid JSON only (no markdown).

    User request:
    {user_task}

    Output schema (JSON object):
    {{
      "goal": "...",
      "tasks": [
        {{
          "id": "short-id",
          "title": "short title",
          "description": "what to do",
          "scope": ["path/or/dir", "..."],
          "acceptance": ["criterion", "..."],
          "test_commands": ["command", "..."],
          "depends_on": ["id", "..."]
        }}
      ]
    }}
    """ ).strip()

def judge_prompt(user_task: str, summary: Dict[str, Any]) -> str:
    return textwrap.dedent(f"""
    You are the JUDGE.

    Review the integrated changes and test log to decide whether the repo now satisfies the user's request.
    If the work is complete, merge the worker branches into the default branch in the main repo.

    Rules:
    - Work in the main repo at: {summary.get("repo_root")}.
    - Checkout the target branch ({summary.get("main_branch")}) before merging.
    - Use a separate remote per worker (one per task id). Remote names and paths are in the summary.
    - Merge only worker branches with status "done".
    - If a merge conflict occurs, abort the merge and report failure.
    - Leave a clean git status at the end.

    Suggested review commands:
    - git -C {summary.get("integration_dir")} log --oneline --decorate -n 20
    - git -C {summary.get("integration_dir")} diff {summary.get("main_base_sha")}..HEAD
    - cat {summary.get("tests_log")}

    Output MUST be valid JSON only.

    User request:
    {user_task}

    Evidence (JSON):
    {json.dumps(summary, indent=2)}

    Output schema:
    {{
      "done": true/false,
      "reason": "short explanation",
      "merge": {{
        "attempted": true/false,
        "status": "merged" | "skipped" | "failed",
        "target_branch": "branch name",
        "merged_tasks": ["id", "..."],
        "details": "notes"
      }},
      "followups": [
        {{
          "id": "followup-id",
          "title": "...",
          "description": "...",
          "scope": ["..."],
          "acceptance": ["..."],
          "test_commands": ["..."],
          "depends_on": ["..."]
        }}
      ]
    }}
    """).strip()


# -----------------------------
# Git clone helpers
# -----------------------------

def referenced_clone(source_repo: Path, reference_repo: Path, dest: Path) -> None:
    """
    Clone from source_repo, referencing reference_repo objects if possible.
    This matches: "Use a new referenced clone of the repo for each subagent".
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)

    # Prefer --reference-if-able, fall back gracefully.
    tried: List[List[str]] = [
        ["git", "clone", "--reference-if-able", str(reference_repo), str(source_repo), str(dest)],
        ["git", "clone", "--reference", str(reference_repo), str(source_repo), str(dest)],
        ["git", "clone", str(source_repo), str(dest)],
    ]
    last_err: Optional[str] = None
    for cmd in tried:
        p = run(cmd, check=False)
        if p.returncode == 0:
            return
        last_err = (p.stderr or p.stdout or "").strip()
    raise SystemExit(f"git clone failed for {dest}.\n{last_err}")

def current_head(repo: Path) -> str:
    return git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()

def checkout_new_branch(repo: Path, branch_name: str, base_sha: str) -> None:
    git(["checkout", "-B", branch_name, base_sha], cwd=repo)

def export_patch(repo: Path, base_sha: str, patch_path: Path) -> Optional[Path]:
    """
    Export changes from base_sha..HEAD as a single patch file.
    Prefer format-patch (applies via git am); fall back to git diff if needed.
    """
    head = current_head(repo)
    if head == base_sha:
        # maybe uncommitted changes
        diff = git(["diff"], cwd=repo).stdout
        if not diff.strip():
            return None
        patch_path.write_text(diff, encoding="utf-8")
        return patch_path

    # format-patch --stdout can include multiple commits into one file
    patch = git(["format-patch", "--stdout", f"{base_sha}..{head}"], cwd=repo).stdout
    patch_path.write_text(patch, encoding="utf-8")
    return patch_path

def apply_patch(integration_repo: Path, patch_path: Path, fallback_commit_msg: str) -> None:
    """
    Try git am -3 first, fall back to git apply + commit.
    """
    p = git(["am", "-3", str(patch_path)], cwd=integration_repo, check=False)
    if p.returncode == 0:
        return

    # abort any in-progress am
    git(["am", "--abort"], cwd=integration_repo, check=False)

    # fallback apply
    p2 = git(["apply", "--3way", str(patch_path)], cwd=integration_repo, check=False)
    if p2.returncode != 0:
        raise SystemExit(
            f"Failed applying patch {patch_path}.\n"
            f"git am error:\n{p.stderr}\n\n"
            f"git apply error:\n{p2.stderr}"
        )
    git(["add", "-A"], cwd=integration_repo)
    git(["commit", "-m", fallback_commit_msg], cwd=integration_repo)


# -----------------------------
# Worker runner
# -----------------------------

def worker_prompt(task: Task) -> str:
    scope_txt = "\n".join([f"- {s}" for s in task.scope]) or "- (not specified)"
    acc_txt = "\n".join([f"- {a}" for a in task.acceptance]) or "- (not specified)"
    tests_txt = "\n".join([f"- {t}" for t in task.test_commands]) or "- (none specified)"
    return textwrap.dedent(f"""
    You are a WORKER agent. You have ONE task and you must finish it end-to-end.

    Task ID: {task.id}
    Title: {task.title}

    Description:
    {task.description}

    Allowed scope (do not modify files outside this list without stopping and explaining):
    {scope_txt}

    Acceptance criteria:
    {acc_txt}

    Tests to run (run what makes sense; at minimum run the ones listed if possible):
    {tests_txt}

    Requirements:
    - Make focused, minimal changes.
    - Run tests and fix failures you introduced.
    - Commit your changes (git add -A && git commit ...) so HEAD contains the completed work.
    - End with a clean git status.
    - Output MUST be valid JSON only, matching this schema:

    {{
      "task_id": "{task.id}",
      "status": "done" | "blocked",
      "summary": "what you changed",
      "files_changed": ["..."],
      "tests_ran": ["..."],
      "test_results": "pass/fail + notes",
      "notes": "any risks or follow-ups",
      "commit_head": "<sha or null>"
    }}
    """).strip()


# -----------------------------
# Main orchestration
# -----------------------------

async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="The large task to delegate.")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--planner-model", default=None)
    ap.add_argument("--worker-model", default=None)
    ap.add_argument("--judge-model", default=None)
    args = ap.parse_args()

    # repo root
    repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()).resolve()
    require_git_clean(repo_root)

    main_base_sha = current_head(repo_root)
    main_branch = default_branch(repo_root)

    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    team_root = repo_root / ".codex" / "agent-team-runs" / run_id
    integration_dir = team_root / "integration"
    clones_dir = team_root / "clones"
    patches_dir = team_root / "patches"
    logs_dir = team_root / "logs"
    for d in (integration_dir, clones_dir, patches_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Make an integration clone (referencing repo_root) and work ONLY inside it.
    referenced_clone(source_repo=repo_root, reference_repo=repo_root, dest=integration_dir)

    base_sha = current_head(integration_dir)
    integration_branch = f"agent-team/integration-{run_id}"
    checkout_new_branch(integration_dir, integration_branch, base_sha)

    # Start Codex MCP server (stdio). Use "codex mcp-server" if available, else npx.
    if shutil.which("codex"):
        command = "codex"
        cmd_args = ["mcp-server"]
    else:
        command = "npx"
        cmd_args = ["-y", "codex", "mcp-server"]

    async with MCPServerStdio(
        name="Codex CLI",
        params={"command": command, "args": cmd_args},
        client_session_timeout_seconds=360000,
        cache_tools_list=True,
    ) as server:
        # ----------------- Planner -----------------
        plan_log = logs_dir / "planner.txt"
        planner_out, _ = await codex_call(
            server,
            prompt=planner_prompt(args.task),
            cwd=integration_dir,
            approval_policy="on-request",
            sandbox="read-only",
            model=args.planner_model,
        )
        plan_log.write_text(planner_out, encoding="utf-8")
        plan = extract_json_object(planner_out)

        (team_root / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

        tasks: List[Task] = []
        for t in plan.get("tasks", []):
            tid = sanitize_task_id(t.get("id", t.get("title", "task")))
            tasks.append(Task(
                id=tid,
                title=t.get("title", tid),
                description=t.get("description", ""),
                scope=list(t.get("scope", [])),
                acceptance=list(t.get("acceptance", [])),
                test_commands=list(t.get("test_commands", [])),
                depends_on=[sanitize_task_id(x) for x in t.get("depends_on", [])],
            ))

        # Build lookup for dependencies.
        by_id = {t.id: t for t in tasks}

        done: set[str] = set()
        running: set[str] = set()
        results: Dict[str, WorkerResult] = {}

        sem = asyncio.Semaphore(args.max_workers)

        async def run_one(task: Task) -> WorkerResult:
            async with sem:
                # Clone from integration dir so dependent tasks can see merged work.
                # Reference repo_root so the clone is a referenced clone.
                task_clone = clones_dir / task.id
                referenced_clone(source_repo=integration_dir, reference_repo=repo_root, dest=task_clone)

                # Ensure worker starts from latest integration HEAD at clone time.
                worker_base = current_head(integration_dir)
                checkout_new_branch(task_clone, f"agent-team/{task.id}", worker_base)

                log_path = logs_dir / f"worker-{task.id}.txt"
                out, _ = await codex_call(
                    server,
                    prompt=worker_prompt(task),
                    cwd=task_clone,
                    approval_policy="never",            # auto-accept
                    sandbox="danger-full-access",       # no sandbox
                    model=args.worker_model,
                )
                log_path.write_text(out, encoding="utf-8")

                # Parse worker JSON (best-effort)
                status = "blocked"
                summary = ""
                commit_head = None
                try:
                    wj = extract_json_object(out)
                    status = wj.get("status", status)
                    summary = wj.get("summary", summary)
                    commit_head = wj.get("commit_head", None)
                except Exception:
                    # If parsing fails, continue; patch export may still work.
                    pass

                patch_path = patches_dir / f"{task.id}.patch"
                patch = export_patch(task_clone, worker_base, patch_path)

                return WorkerResult(
                    task_id=task.id,
                    status=status,
                    summary=summary,
                    commit_head=commit_head,
                    patch_path=patch,
                    raw_output_path=log_path,
                )

        async def apply_worker_result(task: Task, wr: WorkerResult) -> None:
            if wr.patch_path is None:
                return
            apply_patch(
                integration_repo=integration_dir,
                patch_path=wr.patch_path,
                fallback_commit_msg=f"team: apply {task.id} ({task.title})"
            )

        # ----------------- Scheduler (dependency-aware) -----------------
        pending = set(t.id for t in tasks)

        async def launch_ready_tasks() -> List[asyncio.Task[WorkerResult]]:
            ready: List[Task] = []
            for tid in list(pending):
                task = by_id[tid]
                if all(dep in done for dep in task.depends_on):
                    ready.append(task)

            # Launch as many as we can, respecting max-workers via semaphore.
            launched: List[asyncio.Task[WorkerResult]] = []
            for task in ready:
                if task.id in running:
                    continue
                running.add(task.id)
                pending.remove(task.id)
                launched.append(asyncio.create_task(run_one(task)))
            return launched

        active: List[asyncio.Task[WorkerResult]] = []
        active.extend(await launch_ready_tasks())

        while active:
            finished, active = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)

            for fut in finished:
                wr = fut.result()
                task = by_id[wr.task_id]
                results[wr.task_id] = wr

                # Merge immediately so later dependent tasks clone from updated integration state.
                if wr.status == "done" and wr.patch_path:
                    await apply_worker_result(task, wr)
                    done.add(wr.task_id)

                running.discard(wr.task_id)

            # Launch next ready tasks
            active.extend(await launch_ready_tasks())

        # ----------------- Verification -----------------
        # Run a minimal "smoke" command set derived from plan.
        # (This is intentionally simple; you can expand this.)
        unique_cmds: List[str] = []
        seen = set()
        for t in tasks:
            for c in t.test_commands:
                if c and c not in seen:
                    seen.add(c)
                    unique_cmds.append(c)

        test_log = logs_dir / "tests.txt"
        test_lines: List[str] = []
        for cmd in unique_cmds:
            test_lines.append(f"$ {cmd}")
            p = run(cmd.split(), cwd=integration_dir, check=False)
            test_lines.append(p.stdout)
            test_lines.append(p.stderr)
            test_lines.append(f"[exit={p.returncode}]")
            test_lines.append("-" * 40)
        test_log.write_text("\n".join(test_lines), encoding="utf-8")

        # ----------------- Judge -----------------
        summary = {
            "repo_root": str(repo_root),
            "main_branch": main_branch,
            "main_base_sha": main_base_sha,
            "integration_dir": str(integration_dir),
            "integration_branch": integration_branch,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": results.get(t.id).status if t.id in results else "not-run",
                    "summary": results.get(t.id).summary if t.id in results else "",
                    "patch": str(results.get(t.id).patch_path) if (t.id in results and results[t.id].patch_path) else None,
                    "log": str(results.get(t.id).raw_output_path) if t.id in results else None,
                    "clone": str(clones_dir / t.id),
                    "branch": f"agent-team/{t.id}",
                    "remote": f"agent-team-worker-{t.id}",
                    "depends_on": t.depends_on,
                }
                for t in tasks
            ],
            "tests_log": str(test_log),
        }

        judge_log = logs_dir / "judge.txt"
        judge_out, _ = await codex_call(
            server,
            prompt=judge_prompt(args.task, summary),
            cwd=repo_root,
            approval_policy="never",
            sandbox="danger-full-access",
            model=args.judge_model,
        )
        judge_log.write_text(judge_out, encoding="utf-8")

        # Print final summary for the human.
        merge_status = None
        merge_target = None
        try:
            judge_json = extract_json_object(judge_out)
            merge = judge_json.get("merge", {}) if isinstance(judge_json, dict) else {}
            if isinstance(merge, dict):
                merge_status = merge.get("status")
                merge_target = merge.get("target_branch")
        except Exception:
            pass

        print("\n=== agent-team finished ===")
        print(f"Run directory: {team_root}")
        print(f"Integration clone: {integration_dir}")
        print(f"Integration branch: {integration_branch}")
        print(f"Planner output: {team_root / 'plan.json'}")
        print(f"Worker logs: {logs_dir}")
        print(f"Patches: {patches_dir}")
        print(f"Tests log: {test_log}")
        if merge_status:
            target = merge_target or main_branch
            print(f"Merge status: {merge_status} ({target})")
        print(f"Judge output: {judge_log}")

if __name__ == "__main__":
    asyncio.run(main())
