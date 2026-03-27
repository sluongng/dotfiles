---
name: draft-commit-message
description: "Draft, rewrite, and review Git commit messages using the Git project's MyFirstContribution guidance. Use when Codex needs to turn staged changes, a diff, or a rough summary into a commit message with a `component: subject` line, imperative mood, a 50-character-or-less subject, a blank line before the body, and a body that explains the why/context at roughly 72 columns."
---

# Draft Commit Message

## Goal

Turn staged changes, diffs, or plain-English summaries into commit messages
that follow the Git project's `MyFirstContribution` guidance without
inventing missing rationale.

## Workflow

1. Gather context from the repository before drafting.

Prefer staged changes first:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

If nothing is staged, inspect the worktree diff instead:

```bash
git diff --stat
git diff
```

2. Infer the component prefix from the narrowest dominant area of change.

- Prefer repository-local terminology from paths, packages, commands, or
  existing commit subjects.
- When the prefix is unclear, inspect recent history for the touched path:

```bash
git log --format=%s -- path/to/area | head -n 20
```

- If one commit spans unrelated areas and no honest single prefix works,
  recommend splitting the change into multiple commits.

3. Draft the subject as `<component>: <imperative summary>`.

- Keep the subject at 50 characters or fewer.
- Write in imperative mood, as if instructing the codebase: `add`, `teach`,
  `fix`, `remove`, `refactor`.
- Avoid repeating low-level implementation details that fit better in the
  body.

4. Draft the body to explain why and surrounding context.

- Insert one blank line after the subject.
- Put the bulk of the context in the body.
- Explain motivation, user impact, tradeoffs, or constraints that are not
  obvious from the diff.
- Wrap prose to 72 columns where practical.
- If the repository context does not reveal the why, say that explicitly
  instead of fabricating a justification.

5. Preserve or supply trailers correctly.

- Keep existing trailers such as `Signed-off-by:` unchanged.
- If the user mentions `git commit -s`, do not remove the sign-off trailer.

6. Handle single-patch submissions as self-contained units.

- Make the commit message meaningful enough that a single-patch PR does not
  need a repeated description.
- If extra reviewer-only context is needed for emailed patches, put it below
  `---` rather than in the permanent commit message body.

## Output

- Return the final commit message in a fenced `text` block unless the user
  explicitly asks for a different format.
- When confidence is low, add one short sentence after the block describing
  the missing context.
- When reviewing an existing message, list the concrete violations first and
  then provide a corrected version.

## Quick Checks

- Subject is 50 characters or fewer.
- Subject starts with a repo-appropriate component prefix.
- Subject uses imperative mood.
- Line 2 is blank.
- Body lines stay within 72 columns where practical.
- Body adds why/context that is not obvious from the diff.
- Trailers are preserved.

## Resources

- Read [git-my-first-contribution.md](references/git-my-first-contribution.md)
  for the distilled guidance that this skill follows.
- Run `scripts/validate_commit_message.py` when the user asks to validate an
  existing commit message or when a draft is close to the line-length limits.

```bash
python3 scripts/validate_commit_message.py .git/COMMIT_EDITMSG
printf '%s\n' "$message" | python3 scripts/validate_commit_message.py -
```
