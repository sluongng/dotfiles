---
name: buildbuddy-pr-coach
description: "Produce recurring or report-only BuildBuddy PR queue triage with ranked merge blockers and next actions. Use the plugin PR coach for local preparation."
---

# BuildBuddy PR Coach

Use this skill for recurring BuildBuddy PR triage, especially automation prompts
that ask for a daily PR coach view of `buildbuddy-io/buildbuddy`.
For preparing worktrees, rebasing candidates, or fixing PRs, use the available
BuildBuddy plugin PR coach when that work is requested. A queue report can be
completed from GitHub state without fetching or changing a local checkout.

## Workflow

1. Read automation memory defensively when the run has an automation id. Do
   not probe raw `$CODEX_HOME/automations/...` paths; always construct the
   fallback path first:
   ```bash
   AUTOMATION_BASE="${CODEX_HOME:-$HOME/.codex}/automations"
   MEMORY_PATH="$AUTOMATION_BASE/<automation_id>/memory.md"
   if [ -f "$MEMORY_PATH" ]; then
     sed -n '1,240p' "$MEMORY_PATH"
   fi
   ```
2. If the requested work includes local preparation or checkout comparison,
   inspect the relevant checkout and refresh its base as needed. Skip these
   commands for a report-only queue scan:
   ```bash
   git status --short --branch
   git fetch origin +refs/heads/master:refs/remotes/origin/master
   git branch --show-current
   git rev-parse --short HEAD
   git rev-parse --short origin/master
   git rev-list --left-right --count HEAD...origin/master
   ```
3. Fetch the open PR queue with lightweight fields first. Avoid `commits` and
   other heavy nested fields in broad `gh pr list` calls.
   ```bash
   gh pr list -R buildbuddy-io/buildbuddy --state open --limit 200 \
     --json number,title,author,reviewRequests,assignees,mergeStateStatus,statusCheckRollup,updatedAt,createdAt,isDraft,labels,headRefName,baseRefName,url
   ```
4. Use targeted follow-up calls only for likely candidates or unclear blockers:
   ```bash
   gh pr view <number> -R buildbuddy-io/buildbuddy \
     --json number,title,author,reviewDecision,mergeStateStatus,statusCheckRollup,reviews,comments,latestReviews,headRefName,baseRefName,url,isDraft,updatedAt
   ```
5. If using `gh search prs`, request only fields supported by `gh search`:
   `number,title,author,assignees,labels,createdAt,updatedAt,url,isDraft,state`.
   Do not request `reviewDecision`, `mergeStateStatus`, `reviewRequests`, or
   `statusCheckRollup` from search results.
6. Quote `gh api` URLs that contain `?`, `&`, or shell glob characters:
   ```bash
   gh api 'repos/buildbuddy-io/buildbuddy/pulls?state=open&per_page=100'
   ```

## Output Contract

Default to three buckets:

- Highest chance of merge today: 3-5 PRs with PR number, title, status signal,
  blocker, and next concrete action.
- Needs local prep: PRs where the next action is local first, such as rebase on
  latest `origin/master`, check CI, or address comments.
- Waiting or low-probability: stale, blocked, draft, or reviewer-waiting PRs
  that need a decision or can stay brief.

Bias recommendations toward local prep first and reviewer pings second. Do not
dump the full open queue unless the user explicitly asks for it.

## Common Failure Modes

- GraphQL queue queries that include commit authors or deep review connections
  can exceed GitHub limits. Start lightweight, then drill into selected PRs.
- `gh search prs --json reviewDecision` fails because `reviewDecision` is not a
  search field. Use `gh pr view` for review state.
- Raw `$CODEX_HOME/automations/...` paths can resolve to `/automations/...` when
  `CODEX_HOME` is unset. Always use `${CODEX_HOME:-$HOME/.codex}`.
- `git rev-parse --short HEAD origin/master` fails with "Needed a single
  revision"; call `git rev-parse --short` once per revision instead.
