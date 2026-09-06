---
name: hatch-pet
description: "Create, repair, preview, and package Codex animated pet spritesheets from a concept or reference art using image generation and deterministic atlas assembly."
---

# Hatch Pet

## Overview

Create a Codex-compatible animated pet from a concept, one or more reference images, or both. This skill owns pet-specific prompt planning, animation rows, frame extraction, atlas geometry, QA, previews, and packaging. It delegates visual generation to `$imagegen`.

User-facing inputs are optional. If the user omits a pet name, infer one from the concept or reference filenames; if that is not possible, choose a short appropriate name. If the user omits a description, infer one from the concept or references. If the user omits reference images, generate the base pet from text first, then use that base as the canonical reference for every animation row.

## Generation Delegation

Use `$imagegen` for all normal visual generation.

Before generating base art, row strips, or repair rows, load and follow the installed image generation skill:

```text
${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/SKILL.md
```

Do not call the Image API directly for the normal path. Let `$imagegen` choose its own built-in-first path and its own CLI fallback rules. If `$imagegen` says a fallback requires confirmation, ask the user before continuing.

When invoking `$imagegen` from this skill, pass the generated pet prompt as the authoritative visual spec. Do not wrap it in the generic `$imagegen` shared prompt schema and do not add extra polish, hero-art, photo, product, or illustration-style augmentation. Pet prompts should stay terse, sprite-specific, and digital-pet oriented; only add role labels for input images and any essential user constraint.

Use this skill's scripts for deterministic work only: preparing prompts and manifests, ingesting selected `$imagegen` outputs, extracting frames, validating rows, composing the final atlas, creating QA media, and packaging.

Hard boundary: do not create, draw, tile, warp, mirror, or synthesize pet visuals with local Python/Pillow scripts, SVG, canvas, HTML/CSS, or other code-native art as a substitute for `$imagegen`. For a normal pet run, expect up to 10 visual generation jobs: 1 base pet plus 9 row-strip jobs. The only exception is `running-left`, which may be derived by mirroring `running-right` only after `running-right` has been generated, visually inspected, and explicitly approved as safe to mirror. If mirroring is not appropriate, generate `running-left` as a normal grounded `$imagegen` row. If those calls are too expensive, blocked, or unavailable, stop and explain the blocker instead of fabricating row strips locally.

Do not mark visual jobs complete by editing `imagegen-jobs.json`, copying files into `decoded/`, or writing helper scripts that populate row outputs. Use `record_imagegen_result.py` for selected built-in `$imagegen` outputs, or `generate_pet_images.py` only for the documented secondary fallback. The deterministic scripts may only process already-generated visual outputs.

Only the base job may be prompt-only. Every row-strip job generated through `$imagegen` must use the input images listed in `imagegen-jobs.json`, including the canonical base reference created after the base job is recorded. Treat any row generation without attached grounding images as invalid.

## Visual Requirements

Before generation or repair, read
[references/visual-style.md](references/visual-style.md). Keep identity, silhouette,
palette, and props consistent. Each row must have complete separated poses on
its selected flat chroma-key background, with no detached effects or guide pixels.
Default to the Codex digital-pet style unless the user specifies a different
style compatible with the atlas and extraction constraints.

## Progress

Infer missing names and descriptions from the request, as described above. Give
concise progress updates during long generation runs: base art, pose rows,
assembly, and QA. A repair run starts at the failing scope. Report completed
artifacts and actual blockers rather than requiring a fixed checklist format.

## Generation and Assembly

Read [references/generation-workflow.md](references/generation-workflow.md) for
manifest preparation, the base-first job order, grounded row prompts, original
image ingestion, safe running-left derivation, finalization, and output paths.
Read [references/animation-rows.md](references/animation-rows.md) when inspecting
frame counts or changing animation behavior.

## Parallel Rows

Delegate independent row generation when available and useful. Keep one parent
writer for manifests, ingestion, repair queues, finalization, and packaging.
Read [references/parallel-rows.md](references/parallel-rows.md) when delegating.
If delegation is unavailable, continue sequentially through the same image
and QA path unless the user has explicitly required parallel execution.

## Repair Workflow

If finalization stops because row QA failed, queue targeted repair jobs:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet"
python "$SKILL_DIR/scripts/queue_pet_repairs.py" \
  --run-dir /absolute/path/to/run
```

Then repeat the `$imagegen` generation and `record_imagegen_result.py` ingest loop for each reopened row job. Regenerate the smallest failing scope: the failed row, not the whole sheet.

For identity repairs, use the canonical base image, original references, contact sheet, and exact row failure note as grounding context. Repair only the failed row while preserving the canonical pet identity.

## Secondary Fallback

If `$imagegen` is unavailable, read
[references/imagegen-fallback.md](references/imagegen-fallback.md) for the secondary
API path and its prerequisites. Respect applicable API-spend authorization.

## Rules

- Keep `$imagegen` as the primary generation layer.
- Keep reference images attached/visible for `$imagegen` whenever the chosen path supports references.
- Attach the row's `references/layout-guides/<state>.png` image to every row-strip job as a layout-only guide, and do not accept outputs that copy guide pixels.
- Delegate independent row-strip jobs when useful and available; keep manifest and package writes with the parent in both parallel and sequential workflows.
- Generate every normal visual job with `$imagegen`: base plus all row strips that are not explicitly approved `running-left` mirror derivations.
- Treat only the base job as eligible for prompt-only generation; every row job must attach its listed grounding images.
- Generate `running-right` first, then mirror `running-left` only when visual inspection confirms a mirror preserves identity and semantics; otherwise generate `running-left` as a normal grounded `$imagegen` row.
- Never substitute locally drawn, tiled, transformed, or code-generated row strips for missing `$imagegen` outputs.
- Never manually mutate `imagegen-jobs.json` to claim a visual job completed.
- Do not rely on generated images for exact atlas geometry; use this skill's deterministic scripts.
- Use the chroma key stored in `pet_request.json`; do not force a fixed green screen.
- Keep the pet's silhouette, face, materials, palette, and props consistent across all rows.
- Enforce the linked visual-style transparency and effects constraints in every base, row, and repair prompt.
- Treat visual identity drift as a blocker even when `qa/review.json` and `final/validation.json` have no errors.
- Treat a contact sheet that shows cropped references, repeated tiles, white cell backgrounds, or non-sprite fragments as failed.
- Treat forbidden detached effects, chroma-key-adjacent artifacts, shadows, glows, smears, dust, landing marks, wave marks, speed lines, or motion trails as failed rows.
- Treat `qa/review.json` errors as blockers. Warnings require visual review.

## Acceptance Criteria

Read [references/qa-rubric.md](references/qa-rubric.md) when reviewing the atlas
and [references/codex-pet-contract.md](references/codex-pet-contract.md) when
packaging or diagnosing app loading.

- Final atlas is PNG or WebP, `1536x1872`, transparent-capable, and based on `192x208` cells.
- Used cells are non-empty and unused cells are fully transparent.
- Atlas follows the row/frame counts in `references/animation-rows.md`.
- Contact sheet and preview videos have been produced unless explicitly skipped.
- `qa/review.json` has no errors.
- Row-by-row review confirms the animation cycles are complete enough for the Codex app.
- `${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/pet.json` and `${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/spritesheet.webp` are staged together for custom pets.
