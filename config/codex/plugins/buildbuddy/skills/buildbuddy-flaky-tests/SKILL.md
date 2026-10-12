---
name: buildbuddy-flaky-tests
description: Find and rank recent BuildBuddy flaky tests, inspect sample failures, and reproduce or fix a selected flake.
---

# BuildBuddy Flaky Tests

## Overview

Use BuildBuddyService target-stat RPCs to fetch the same data behind the Test
Analytics flakes page, then use the top entries to drive focused PR search,
reproduction, and fixes.

The helper script calls:

- `GetTargetStats` for the flaky target list.
- `GetDailyTargetStats` for recent daily aggregate counts.
- `GetTargetFlakeSamples` for sample flaky invocations for selected labels.
- `GetUser` or `GetGroup` only to resolve the group ID when needed.

Load `references/requests.md` when you need raw HTTP JSON request templates or
field mapping details.

## Quick Start

From a BuildBuddy repo with `bb login` already done:

```bash
FLAKY_SKILL_DIR="${BUILDBUDDY_FLAKY_TESTS_SKILL_DIR:-<path-to-this-skill>}"
python3 "$FLAKY_SKILL_DIR/scripts/fetch_flaky_tests.py" \
  --org-slug buildbuddy \
  --repo auto \
  --branch master \
  --days 7 \
  --limit 10 \
  --samples-for-top 1
```

Use `--format json --out <file>` when the next step needs structured data.
Use `--sort flake-percent` to mirror the default table sort in
`enterprise/app/tap/flakes.tsx`; use the default `--sort total-flakes` for
automation because it prioritizes the highest-volume flakes.

## Preconditions

- Check API key presence without printing it:
  `git config --local buildbuddy.api-key | wc -c`.
- The script also accepts `BUILDBUDDY_API_KEY`, `BUILD_BUDDY_API_KEY`,
  `BUILDBUDDY_GROUP_ID`, `BUILD_BUDDY_GROUP_ID`, `BUILDBUDDY_ORG_SLUG`, and
  `BUILD_BUDDY_ORG_SLUG`.
- If group resolution fails, rerun with `--group-id GR...` or
  `--org-slug <url-identifier>`.
- For the public BuildBuddy repo, use `--org-slug buildbuddy`; the selected
  group inferred from `GetUser` may not be the group that owns the repo data.
- Keep windows small by default. The proto default is 7 days; the flakes UI
  can also pass explicit start/end filters.

## Triage Workflow

1. Fetch a recent ranked list with `fetch_flaky_tests.py`.
2. Pick the top entry using the requested sort. For daily automation, prefer
   total flaky plus likely-flaky runs over pure percentage.
3. For that label, inspect sample invocation IDs from the script output. If
   deeper logs are needed, use `buildbuddy-invocation-troubleshoot` on a sample
   invocation and target label.
4. Before reproduction or editing, check whether a credible PR already
   addresses the same failure signature, across open, draft, closed, and merged
   PRs. Search for the exact label, package path, test suite/class name, and
   distinctive error text; inspect the relevant diff or discussion rather than
   treating PR status or a title match as proof.
   For platform-specific timeouts, also search the affected platform and CI
   workflow for scheduling, resource-contention, or build/test-phase changes;
   related PR titles and descriptions may not name the slow test. Record
   whether each candidate is active, merged (and whether the failing revision
   contains it), or closed without merging. An abandoned experiment
   is related evidence, not proof of a fix; explain its different mechanism
   and follow any explicit job skip rule rather than silently treating it as
   resolved or claiming no related PR exists.
   For a ranked automation run, record and skip PR-handled or unchanged
   previously handled signatures according to the job's memory and receipt
   rules, then continue to the next ranked candidate. If only the skipped
   target had samples, fetch samples for the new label before diagnosing it.
   If no new actionable signature remains, report a useful no-op instead of
   duplicating a fix or reproduction.
5. If a fix is requested and no PR is clearly addressing it, reproduce narrowly.
   Choose the repeat count for the observed flake rate and runtime; for example:

```bash
bazel test <label> --config=remote-minimal --nocache_test_results --runs_per_test=30 --test_output=errors
```

Use the sample invocation's branch, commit, flags, and environment if local
reproduction does not fail.

6. Fix the demonstrated cause, then validate with the target test. Choose a
   repeat count based on the observed failure rate and runtime; increase it
   only when more runs would materially strengthen the result.
7. Report the flaky target label, ranking evidence, sample invocation links,
   PR-search result, reproduction result, and validation commands.

## Resources

- `scripts/fetch_flaky_tests.py`: fetch, rank, and summarize flaky target stats.
- `references/requests.md`: RPC field mapping and raw request templates.
