# Pet Generation and Assembly

Use for a new pet or when rerunning the pipeline. Repair-only work can start at
the relevant job and ingest step.

## Default Workflow

1. Prepare a pet run folder and imagegen job manifest:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet"
python "$SKILL_DIR/scripts/prepare_pet_run.py" \
  --pet-name "<Name>" \
  --description "<one sentence>" \
  --reference /absolute/path/to/reference.png \
  --output-dir /absolute/path/to/run \
  --pet-notes "<stable pet description>" \
  --style-notes "<style notes>" \
  --force
```

All arguments above are optional except any flags needed to express user constraints. For text-only requests, pass the concept through `--pet-notes` and omit `--reference`; `prepare_pet_run.py` will infer a name, description, chroma key, and output directory as needed.

2. Inspect the next ready `$imagegen` jobs:

```bash
python "$SKILL_DIR/scripts/pet_job_status.py" --run-dir /absolute/path/to/run
```

3. For each ready job, invoke `$imagegen` with:

- the prompt file listed in `imagegen-jobs.json`
- every input image listed for the job, with its role label
- the default built-in `image_gen` path unless `$imagegen` itself routes otherwise

The base job must complete first. If user references exist, the base job uses them. If no references exist, the base job may be prompt-only. After recording the base, `record_imagegen_result.py` writes `decoded/base.png` and `references/canonical-base.png`; all row jobs use the original references if present plus those canonical base images.

`prepare_pet_run.py` also creates 9 row-specific layout guide images under `references/layout-guides/`, one per animation state. Row jobs attach the matching guide as a layout-only input so the model can follow the correct frame count, spacing, centering, and safe padding. Treat these guides as invisible construction references: the generated row strip must not include visible boxes, borders, center marks, labels, guide colors, or the guide background.

When generating row strips, keep the identity lock in the row prompt authoritative: do not redesign the pet, and preserve the same head shape, face, markings, palette, prop, outline weight, body proportions, and silhouette. A row that looks like a related but different pet is failed even if the deterministic geometry QA passes.

Generate and record `running-right` before deciding how to complete `running-left`. Inspect `running-right` against the base and references. If the pet is visually symmetric enough that a horizontal mirror preserves identity, prop placement, handedness, markings, lighting, text-free details, and direction semantics, derive `running-left` with:

```bash
python "$SKILL_DIR/scripts/derive_running_left_from_running_right.py" \
  --run-dir /absolute/path/to/run \
  --confirm-appropriate-mirror \
  --decision-note "<why mirroring preserves this pet's identity>"
```

If there is any asymmetric side-specific marking, readable text, non-mirrored logo, handed prop, one-sided accessory, lighting cue, or direction-specific pose that would become wrong when flipped, do not mirror. Generate `running-left` with `$imagegen` using its row prompt and all listed grounding images, including `decoded/running-right.png` as a gait reference.

For the built-in path, record the selected source image from `$CODEX_HOME/generated_images/.../ig_*.png`. Do not record files from the run directory, `tmp/`, hand-made fixtures, deterministic row folders, or post-processed copies as visual job sources.

4. After selecting a generated output for a job, ingest it:

```bash
python "$SKILL_DIR/scripts/record_imagegen_result.py" \
  --run-dir /absolute/path/to/run \
  --job-id <job-id> \
  --source /absolute/path/to/generated-output.png
```

This copies the image to the exact decoded path expected by the deterministic pipeline and records source metadata in `imagegen-jobs.json`.

5. When all jobs are complete, finalize:

```bash
python "$SKILL_DIR/scripts/finalize_pet_run.py" \
  --run-dir /absolute/path/to/run
```

Expected output:

```text
run/
  pet_request.json
  imagegen-jobs.json
  prompts/
  decoded/
  frames/frames-manifest.json
  final/spritesheet.png
  final/spritesheet.webp
  final/validation.json
  qa/contact-sheet.png
  qa/review.json
  qa/run-summary.json
  qa/videos/*.mp4
```

Package output is written outside the run directory by default. If `CODEX_HOME` is set, use it; otherwise use `$HOME/.codex`.

```text
${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/
  pet.json
  spritesheet.webp
```

Review `qa/contact-sheet.png`, `qa/review.json`, `final/validation.json`, and `qa/videos/` before accepting the pet.

Deterministic validation is necessary but not sufficient. Before calling the pet done, visually inspect the contact sheet for identity consistency. Block acceptance if any row changes species/body type, face, markings, palette, prop design, prop side unexpectedly, or overall silhouette.
