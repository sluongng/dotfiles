#!/usr/bin/env python3
from pathlib import Path

from PIL import Image
from PIL import ImageDraw
from PIL import ImageEnhance


ROOT = Path(__file__).with_name("assets")
SIZE = 144


def canvas():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def save_icon(name, draw_fn):
    image = canvas()
    draw_fn(ImageDraw.Draw(image))
    image.resize((72, 72), Image.Resampling.LANCZOS).save(ROOT / name)


def speaker(draw, direction):
    white = (225, 245, 255, 255)
    draw.rounded_rectangle((30, 58, 56, 88), 5, fill=white)
    draw.polygon([(52, 58), (82, 36), (82, 110), (52, 88)], fill=white)
    x = 108
    draw.line((x - 16 * direction, 72, x, 72), fill=(64, 220, 200, 255), width=9)
    draw.line((x - 7 * direction, 63, x, 72, x - 7 * direction, 81), fill=(64, 220, 200, 255), width=9)


def output_mute(draw):
    speaker(draw, 1)
    draw.line((95, 52, 126, 92), fill=(255, 88, 110, 255), width=10)
    draw.line((126, 52, 95, 92), fill=(255, 88, 110, 255), width=10)


def mic(draw):
    white = (225, 245, 255, 255)
    draw.rounded_rectangle((52, 24, 92, 90), 20, fill=white)
    draw.arc((36, 52, 108, 112), 0, 180, fill=(255, 174, 66, 255), width=9)
    draw.line((72, 110, 72, 126), fill=white, width=9)
    draw.line((50, 126, 94, 126), fill=white, width=9)


def airpods(draw):
    white = (232, 247, 255, 255)
    for offset, flip in ((0, 1), (72, -1)):
        cx = 42 + offset
        draw.ellipse((cx - 22, 24, cx + 20, 66), fill=white)
        draw.rounded_rectangle((cx - 2 if flip == 1 else cx - 10, 52, cx + 10 if flip == 1 else cx + 2, 118), 6, fill=white)
        draw.ellipse((cx - 8, 32, cx + 8, 48), fill=(50, 155, 220, 255))


def codex_assets():
    source = Image.open(ROOT / "codex-complete-source.png").convert("RGB")
    source.thumbnail((72, 72), Image.Resampling.LANCZOS)
    ready = Image.new("RGB", (72, 72), "black")
    ready.paste(source, ((72 - source.width) // 2, (72 - source.height) // 2))
    ready.save(ROOT / "codex-ready.png")
    ImageEnhance.Brightness(ready).enhance(0.22).save(ROOT / "codex-dim.png")
    frames = []
    for factor in (0.55, 0.7, 0.88, 1.05, 1.2, 1.05, 0.88, 0.7):
        frames.append(ImageEnhance.Brightness(ready).enhance(factor))
    frames[0].save(
        ROOT / "codex-pulse.gif",
        save_all=True,
        append_images=frames[1:],
        duration=125,
        loop=0,
        optimize=True,
    )


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    codex_assets()
    save_icon("volume-down.png", lambda draw: speaker(draw, -1))
    save_icon("volume-up.png", lambda draw: speaker(draw, 1))
    save_icon("output-mute.png", output_mute)
    save_icon("mic-mute.png", mic)
    save_icon("airpods.png", airpods)
