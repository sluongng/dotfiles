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
- Prefer 2-4 short, direct sentences over one dense paragraph when the first
  draft starts chaining too many clauses together.
- Start the first body paragraph with the concrete reason for the change when
  it is knowable from the task or diff, such as a user request, regression,
  missing support, broken workflow, or review feedback being addressed.
- When fixing a regression, flake, or other incident, lead with the concrete
  failure or user-visible symptom before explaining the mechanism.
- When this text is likely to be reused for a PR body, write the opening
  paragraph so it can be copied verbatim with little or no rewriting.
- If a reproducer command or short error excerpt is central to the why,
  include the real command or a brief concrete snippet. Do not leave
  placeholders such as `<probe>` or `<failure log>` in the final message.
- When citing upstream commits to explain when behavior changed, pair the hash
  with a stable release version when that gives the reader a better sense of
  time.
- Wrap prose to 72 columns where practical.
- If the repository context does not reveal the why, say that explicitly
  instead of fabricating a justification.
- Do not turn the commit body into a PR template. Avoid Markdown headings such
  as `Summary`, `Testing`, or `Checklist` in the permanent message unless the
  user explicitly asks for that format.

5. Preserve or supply trailers correctly.

- Keep existing trailers such as `Signed-off-by:` unchanged.
- If the user mentions `git commit -s`, do not remove the sign-off trailer.

6. Handle single-patch submissions as self-contained units.

- Make the commit message meaningful enough that a single-patch PR does not
  need a repeated description.
- Keep the permanent commit message readable as plain text. If the user wants
  long logs, many links, or reviewer-only reference material, prefer a short
  appendix below `---` or move that material into the PR body.
- If extra reviewer-only context is needed for emailed patches, put it below
  `---` rather than in the permanent commit message body.

## Output

- Return the final commit message in a fenced `text` block unless the user
  explicitly asks for a different format.
- If the same change will also drive PR metadata, keep the technical story in
  sync with the PR, but do not force GitHub Markdown conventions into the
  permanent commit message unless the user explicitly asks for that.
- If the commit and PR should match closely, draft the commit body first and
  treat it as the source text for the PR description rather than writing two
  separate narratives from scratch.
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
- Opening body paragraph names the regression, failure, or motivation when the
  change fixes a concrete problem.
- Body reads as plain prose, not a GitHub template.
- Body uses short direct sentences when that makes the why easier to scan.
- Any embedded commands or log excerpts are concrete and brief, not
  placeholders.
- If upstream commits are cited for timing context, release/version context is
  included when it materially helps orientation.
- If validation warns that the body lacks why/context, revise the opening body
  lines to make the problem and motivation explicit, then re-run validation.
- Trailers are preserved.

## Resources

- Read [git-my-first-contribution.md](references/git-my-first-contribution.md)
  for the distilled guidance that this skill follows.
- Run `scripts/validate_commit_message.py` when the user asks to validate an
  existing commit message, when drafting a final message for commit/squash
  workflows, or when a draft is close to the line-length limits.
- Treat validator `WARN` output as actionable review feedback, not a green
  light. If it says the body may be missing explicit why/context language, add
  a more direct motivation sentence and re-check.

```bash
python3 scripts/validate_commit_message.py .git/COMMIT_EDITMSG
printf '%s\n' "$message" | python3 scripts/validate_commit_message.py -
```
