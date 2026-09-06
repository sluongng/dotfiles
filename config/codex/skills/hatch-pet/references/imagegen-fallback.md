# Secondary Image Generation Fallback

Read only when the installed imagegen skill is unavailable or cannot be invoked.

## Secondary Image Generation Fallback

`scripts/generate_pet_images.py` is a secondary fallback for this skill.

Use it only when the installed `$imagegen` system skill is unavailable or cannot be invoked in the current environment. Normal pet creation should delegate visual generation to `$imagegen`, because `$imagegen` owns the built-in-first image generation policy and its own CLI fallback behavior.

Run the secondary fallback only after explaining why `$imagegen` cannot be used:

```bash
python "$SKILL_DIR/scripts/generate_pet_images.py" \
  --run-dir /absolute/path/to/run \
  --model gpt-image-2 \
  --states all
```

The secondary fallback requires `OPENAI_API_KEY`.
