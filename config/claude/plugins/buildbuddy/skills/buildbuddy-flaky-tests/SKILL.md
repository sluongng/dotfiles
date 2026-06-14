---
name: buildbuddy-flaky-tests
description: Fetch and triage recent BuildBuddy flaky-test data with BuildBuddyService RPCs. Use when Claude needs to list the latest flaky targets, match the Test Analytics flakes UI, get sample flaky invocations/log pointers, rank recent flakes, check whether a PR is already addressing a flaky target, or start reproducing and fixing the top flaky test.
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
4. Check whether an open PR already addresses it before editing:
   search GitHub PRs for the exact label, package path, test suite/class name,
   and distinctive error text from logs.
5. If no PR is clearly addressing it, reproduce narrowly. Start with the target:

```bash
bazel test <label> --config=remote-minimal --nocache_test_results --runs_per_test=30 --test_output=errors
```

Use the sample invocation's branch, commit, flags, and environment if local
reproduction does not fail.

6. Make the smallest plausible fix, then validate with the target test using a
   higher repeat count when the failure was reproduced.
7. Report the flaky target label, ranking evidence, sample invocation links,
   PR-search result, reproduction result, and validation commands.

## Resources

- `scripts/fetch_flaky_tests.py`: fetch, rank, and summarize flaky target stats.
- `references/requests.md`: RPC field mapping and raw request templates.

### references/
Documentation and reference material intended to be loaded into context to inform Claude's process and thinking.

**Examples from other skills:**
- Product management: `communication.md`, `context_building.md` - detailed workflow guides
- BigQuery: API reference documentation and query examples
- Finance: Schema documentation, company policies

**Appropriate for:** In-depth documentation, API references, database schemas, comprehensive guides, or any detailed information that Claude should reference while working.

### assets/
Files not intended to be loaded into context, but rather used within the output Claude produces.

**Examples from other skills:**
- Brand styling: PowerPoint template files (.pptx), logo files
- Frontend builder: HTML/React boilerplate project directories
- Typography: Font files (.ttf, .woff2)

**Appropriate for:** Templates, boilerplate code, document templates, images, icons, fonts, or any files meant to be copied or used in the final output.

---

**Not every skill requires all three types of resources.**
