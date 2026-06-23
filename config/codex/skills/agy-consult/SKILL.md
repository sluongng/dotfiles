---
name: agy-consult
description: Run the Antigravity CLI `agy` as a fast, advisory, read-only scout from Codex. Use when Codex should delegate bounded codebase reconnaissance, first-pass review, hypothesis generation, or evidence extraction to Gemini 3.5 Flash through `agy --print`, while keeping final judgment, edits, and validation in the main Codex thread.
---

# Agy Consult

Use this skill to get a fast second pass from Antigravity CLI without handing it
authority over the task. Treat results as advisory. Codex must verify any claim
against source, logs, tests, or live state before using it in a final answer or
patch.

## Workflow

1. Keep the task narrow.
   - Good prompts ask for file paths, likely causes, suspicious diffs, missing
     tests, or concrete evidence.
   - Avoid broad prompts like "fix the repo" or "analyze everything".

2. Run the bundled wrapper from the repo or workspace to inspect:

       python3 ~/.codex/skills/agy-consult/scripts/agy_consult.py \
         --prompt "Find the code paths that parse repo URLs and summarize risks with file refs."

   Useful options:

       --repo <path>          Workspace to expose to agy; defaults to cwd.
       --prompt-file <path>   Read the task from a file.
       --name <slug>          Add a readable label to the saved run directory.
       --timeout 5m           agy print timeout; defaults to 5m.
       --model <label>        Defaults to Gemini 3.5 Flash (High).

3. Review the saved artifacts.
   - The wrapper prints the run directory under
     `~/.cache/codex/agy-consult/<timestamp>-<slug>/`.
   - Inspect `response.md`, `prompt.txt`, `agy.log`, and `command.json`
     when merging the result into Codex work.

4. Verify before acting.
   - Re-read cited files and line references locally.
   - Re-run any commands or tests that matter.
   - Ignore unsupported conclusions, vague confidence, or findings without
     source evidence.

## Safety Model

The wrapper uses `bubblewrap` and fails closed if containment is unavailable.
It binds the host filesystem read-only, binds shared `~/.gemini` state
writable so Antigravity can authenticate and keep normal CLI history, and binds
the run artifact directory writable for logs. It does not rely on `agy
--sandbox` as the containment boundary.

This is read-only consulting only. For patches, create a separate writable
worktree and use a task-specific wrapper or explicit command after reviewing the
risk.

## Parallel Use

For multiple scouts, run independent wrapper invocations with a small fan-out,
for example:

    printf '%s\n' prompt-a.txt prompt-b.txt | \
      parallel -j2 'python3 ~/.codex/skills/agy-consult/scripts/agy_consult.py --prompt-file {}'

Start with `-j2`. Increase only after checking quota and result quality.
