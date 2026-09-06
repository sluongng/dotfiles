# Parallel Row Generation

Read when delegating independent row jobs. Sequential generation uses the same
image prompts and QA, without requiring this handoff procedure.

## Parallel Row Generation

After the base job has been recorded and `references/canonical-base.png` exists, use subagents for independent row-strip generation when available and useful, unless the user requests sequential work. State which row jobs are delegated. When delegation is unavailable, generate rows sequentially through the same `$imagegen` and QA path; tool availability alone does not require a permission pause.

The parent agent must own the manifest and package writes.

Default flow:

1. Parent runs `prepare_pet_run.py`.
2. Parent generates and records `base`.
3. Parent runs `pet_job_status.py`.
4. Parent spawns subagents for `idle` and `running-right` first as identity and gait checks.
5. Parent records the selected `idle` and `running-right` results returned by subagents.
6. Parent decides whether `running-left` is safe to derive by mirror; if not, parent treats it as a normal grounded row job delegated to a subagent.
7. Parent spawns subagents for every remaining non-derived row image-generation job.
8. Each subagent receives the row prompt and every listed input image path, invokes `$imagegen`, and returns only the selected `$CODEX_HOME/generated_images/.../ig_*.png` source path.
9. Parent alone runs `record_imagegen_result.py`, `derive_running_left_from_running_right.py`, repair queueing, finalization, QA, and packaging.

Subagent write boundary: do not let subagents edit `imagegen-jobs.json`, copy files into `decoded/`, run `record_imagegen_result.py`, run `derive_running_left_from_running_right.py`, run `finalize_pet_run.py`, or package the pet. This avoids manifest races and keeps provenance checks centralized.

Subagent handoff contract:

- Give each subagent exactly one row job unless you are intentionally batching adjacent simple rows.
- Include the row id, the absolute prompt file path, the full prompt text or an instruction to read that exact prompt file, and every input image path with its role label from `imagegen-jobs.json`.
- Explicitly remind the subagent that the prompt's transparency and effects rules are mandatory: no detached effects, no wave marks for `waving`, no speed lines or dust for running rows, and only attached opaque sprite-like tears/smoke/stars when allowed by the state prompt.
- Tell the subagent to inspect the generated candidate for frame count, identity consistency, clean flat chroma-key background, safe spacing, and forbidden detached effects before returning it.
- Tell the subagent to return only the selected original `$CODEX_HOME/generated_images/.../ig_*.png` source path plus a one-sentence QA note. The parent decides whether to record or repair it.

Use this template for each subagent:

```text
Generate the `<row-id>` row for this hatch-pet run.

Run dir: <absolute run dir>
Prompt file: <absolute prompt file>
Input images:
- <absolute path> — <role>
- <absolute path> — <role>

Read and follow the row prompt exactly, including the Transparency and artifact rules. Use `$imagegen` only; do not use local scripts to draw, tile, edit, or synthesize sprites.

Before returning, visually check:
- exact requested frame count
- same pet identity as the canonical base
- clean flat chroma-key background
- complete, separated, unclipped poses
- no forbidden detached effects or slot-crossing artifacts

Do not edit manifests, copy into decoded, record results, mirror rows, finalize, repair, or package. Return only:
selected_source=/absolute/path/to/$CODEX_HOME/generated_images/.../ig_*.png
qa_note=<one sentence>
```

Report which rows were delegated, generated sequentially, mirrored, or repaired when that helps explain the delivered artifacts or limitations.
