---
name: github-create-pr
description: "Create GitHub pull requests from the current checkout after local commits are ready. Use when Codex needs to inspect the commit range, use `draft-commit-message` as the source of truth for the PR title and body, ask the user to review that text before opening the PR, then push the branch and create a draft or ready PR. Prefer this over generic publish workflows when PR wording review is required."
---

# GitHub Create PR

## Overview

Create a GitHub pull request from an existing local branch or commit range.
Draft the PR title and description through `$draft-commit-message` first, do
not add a `[codex]` prefix to the title, and require explicit user review of
the title and description before opening the PR. Default to commit-message-style
PR metadata rather than canned GitHub template sections.

Assume the usual workflow is co-development between the user and Codex, followed
by handoff to a second human reviewer while CI runs. Use the draft-message
guidance to optimize the PR body for reviewer understanding: explain the
problem, why the change is needed, the chosen approach, impact, tradeoffs,
rollout constraints, and any intentionally omitted work. Do not use the PR body
to prove that local validation happened unless the user or repo guidance asks
for validation in the body.

## Workflow

1. Confirm the PR scope.
   - Run `git status -sb` and inspect the commit range that will be sent.
   - If there are uncommitted or unrelated changes, stop and clarify scope.
   - If there is no coherent commit range yet, stop and ask the user to
     finish the commit workflow first.
   - Check repo-local guidance such as `AGENTS.md` before choosing branch,
     remote, or base branch behavior.

2. Draft the PR title and description before any PR creation action.
   - Inspect the commits and diff that will be included.
   - Use `$draft-commit-message` to draft the PR title and body. Treat its
     subject as the PR title and its body as the PR body unless a repo-local PR
     convention clearly requires a small adaptation.
   - Do not hand-roll a separate PR title/body using independent rules. If the
     PR text seems weak, improve the draft-message output and keep the commit
     and PR stories synchronized.
   - If the PR is effectively one finalized commit or one squashed change,
     start from that commit subject and body verbatim. Treat the commit
     message as the default PR title/body, then make only the smallest edits
     needed for reviewer context or Markdown links.
   - If the change already has a strong commit message, keep the PR title and
     body synchronized with it. Adapt only what GitHub Markdown or
     reviewer-only context requires.
   - For multi-commit PRs, synthesize from the final commit messages first.
     Prefer 1-3 short paragraphs or a short flat list over a sectioned
     template.
   - Default to plain paragraphs. Use flat bullets only when they improve
     clarity.
   - Do not default to template sections such as `Summary`, `Testing`, or
     `Checklist`. Add a labeled section only when the user explicitly asks
     for one or the material would otherwise be hard to scan.
   - If the first draft starts to look like a GitHub template, rewrite it as
     plain prose before showing it to the user.
   - For regressions, flakes, or incident fixes, put the concrete failure or
     symptom near the top so reviewers can identify the issue quickly.
   - Omit validation commands from the PR body by default. Do not add trailing
     "Validated with", "Testing", or "Tests" paragraphs unless the user
     explicitly asks for validation details in the body or approves that exact
     text during review. CI is the reviewer-visible validation surface;
     validation that Codex ran belongs in the final response, not the PR body.
   - Include exact repro commands only when they materially support the change.
     Inline them naturally in the body or in a short supporting list. Do not
     force a separate `Testing` section.
   - If a short error excerpt or command is central to the why, include the
     real text rather than a placeholder.
   - Prefer short direct sentences. If a paragraph becomes a long chain of
     clauses, split it before presenting the draft.
   - Do not add `Fixes`, `Closes`, `Related`, issue numbers, commit counts, or
     stack-breakdown prose unless the user asked for them or they are already
     clearly part of the intended message.
   - When linking upstream commits or source files, keep each link aligned to
     the exact revision being discussed.
   - Prefer direct links or descriptive links over brittle intra-body anchor
     schemes. If you must use custom anchors, plan to verify the rendered body
     after PR creation.
   - Before showing the draft, compare it against the final commit message(s).
     Remove any extra framing that does not add reviewer value.
   - If the body does not yet explain why the change should merge, rerun the
     `$draft-commit-message` reasoning with more context before showing it.
   - Show the proposed title and description to the user for review.
   - Treat explicit approval in the current thread as required before
     continuing. If approval is missing, stop here.

3. Prepare the branch for review.
   - If the current branch does not match repo-local PR branch conventions,
     create or rename it only when needed and only after understanding the
     repository's expectations.
   - Push the branch to the appropriate remote after the user has approved
     the PR title and description.
   - Prefer repo-local remote conventions over generic defaults.
   - Record the exact remote head ref used for the PR, especially for fork
     workflows where the pushed branch name may differ from the local upstream.

4. Open the PR.
   - Default to a draft PR unless the user explicitly asks for a ready PR.
   - Prefer the GitHub connector or app for PR creation after the branch is
     pushed.
   - Use `gh` for auth checks, repo metadata, or cross-repo `head` cases
     where the connector path is awkward.
   - Use the user-approved title and description verbatim aside from trivial
     formatting cleanup.
   - When using `gh`, pass multiline PR bodies through stdin or a file, not
     through `--body` with a shell-escaped or JSON-escaped string. Prefer
     `gh pr create --body-file - <<'EOF'` and
     `gh pr edit --body-file - <<'EOF'` for multiline text. Do not use a
     command shape that can preserve literal `\\n` or `\\r\\n` sequences
     in the GitHub body.
   - Derive the base branch from the user request or the remote default
     branch when unspecified.
   - If commits were amended or squashed after the draft was first written,
     refresh the PR title/body through `$draft-commit-message` before opening
     or editing the PR.
   - After creation, verify the PR head ref matches the branch that was pushed.
     If the local branch upstream points somewhere else, fix it with
     `git branch --set-upstream-to=<remote>/<branch>` so later `gh pr view`,
     `gh pr status`, and follow-up pushes resolve the same PR.
   - If the PR body uses custom anchors or other rendering-sensitive Markdown,
     verify the rendered body and fix broken links before considering the PR
     done.
   - After creating or editing a PR body, inspect the stored body with
     `gh pr view ... --json body --jq .body` or equivalent. If the output
     contains literal `\\n` sequences where paragraph breaks should be, fix
     the body immediately with `--body-file -`.

5. Summarize the result.
   - Return the pushed branch, remote, base and head refs, PR URL, draft
     state, and validation that was run.

## Safety Rules

- Never open a PR before the user has reviewed and approved the PR title and
  description in the current thread.
- Never add `[codex]` or similar tool prefixes to the PR title unless the
  user explicitly asks for one.
- Never force template headings, especially `Testing`, when the same context
  reads cleanly as commit-message-style prose.
- Never add validation command blocks or trailing validation paragraphs to the
  PR body unless explicitly requested or approved by the user.
- Never decorate the first PR draft with extra issue refs, stack narration, or
  headings unless the user asked for them.
- Never send multiline PR bodies through a shell/JSON-escaped `--body`
  argument; use stdin or `--body-file -` so newlines remain real newlines.
- Never stage, commit, or push unrelated user changes silently.
- If repository identity, auth, or push permissions are unclear, stop and
  explain the blocker before acting.

## PR Checklist

- title and body were derived through `$draft-commit-message`
- body helps a second human reviewer understand the problem, approach,
  tradeoffs, and rollout context
- body avoids unnecessary template sections; `Testing` appears only when
  explicitly requested or clearly warranted
- body omits validation commands unless the user explicitly requested or
  approved them in the PR body
- single-commit PRs default to the finalized commit body with only minimal
  reviewer-oriented edits
- body avoids unrequested issue-closing syntax and extra framing
- debugging/incident PRs surface the failure quickly near the top
- commands, logs, and links render correctly on GitHub
- stored GitHub body has real paragraph breaks, not literal `\\n` escapes
- base and head branches are correct
- draft versus ready state matches the user's request

## Example Triggers

- "Create a draft PR for this branch."
- "Draft the PR title and description, let me review them, then open the PR."
- "Push these commits and create a PR after I approve the body."
