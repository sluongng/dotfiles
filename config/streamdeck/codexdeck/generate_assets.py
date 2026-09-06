#!/usr/bin/env python3
import math
from pathlib import Path

from PIL import Image
from PIL import ImageDraw
from PIL import ImageEnhance
from PIL import ImageFilter


ROOT = Path(__file__).with_name("assets")
SIZE = 144
CODEX_SIZE = 72


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


def dictation(draw):
    mic(draw)
    teal = (64, 220, 200, 255)
    draw.line((112, 28, 112, 52), fill=teal, width=7)
    draw.line((100, 40, 124, 40), fill=teal, width=7)


def new_codex(draw):
    white = (225, 245, 255, 255)
    teal = (64, 220, 200, 255)
    draw.rounded_rectangle((22, 34, 122, 112), 10, outline=white, width=8)
    draw.line((40, 58, 54, 72, 40, 86), fill=teal, width=8, joint="curve")
    draw.line((66, 88, 92, 88), fill=white, width=8)
    draw.line((108, 12, 108, 44), fill=teal, width=8)
    draw.line((92, 28, 124, 28), fill=teal, width=8)


def send_enter(draw):
    white = (225, 245, 255, 255)
    teal = (64, 220, 200, 255)
    draw.line((112, 34, 112, 78, 48, 78), fill=white, width=9, joint="curve")
    draw.line((48, 78, 70, 56), fill=teal, width=9)
    draw.line((48, 78, 70, 100), fill=teal, width=9)


def media_play_pause(draw):
    white = (225, 245, 255, 255)
    teal = (64, 220, 200, 255)
    draw.polygon([(22, 34), (22, 110), (76, 72)], fill=teal)
    draw.rounded_rectangle((90, 34, 104, 110), 4, fill=white)
    draw.rounded_rectangle((116, 34, 130, 110), 4, fill=white)


def centered_scale(image, scale):
    size = max(1, round(CODEX_SIZE * scale))
    resized = image.resize((size, size), Image.Resampling.LANCZOS)
    frame = Image.new("RGB", (CODEX_SIZE, CODEX_SIZE), "black")
    frame.paste(resized, ((CODEX_SIZE - size) // 2, (CODEX_SIZE - size) // 2))
    return frame


def orbit_frame(source, phase, brightness, scale, strength):
    frame = centered_scale(
        ImageEnhance.Brightness(source).enhance(brightness), scale
    )
    angle = phase * 360
    # Brighten only pixels already present in the source. This makes the light
    # travel through the existing ring instead of drawing a detached spinner
    # on top of the logo.
    sweep_mask = Image.new("L", frame.size, 0)
    sweep_draw = ImageDraw.Draw(sweep_mask)
    sweep_draw.arc(
        (6, 6, 66, 66),
        start=angle - 82,
        end=angle + 12,
        fill=round(205 * strength),
        width=8,
    )
    sweep_mask = sweep_mask.filter(ImageFilter.GaussianBlur(radius=2.4))
    brightened = ImageEnhance.Brightness(frame).enhance(1 + 0.58 * strength)
    frame = Image.composite(brightened, frame, sweep_mask)

    tip_mask = Image.new("L", frame.size, 0)
    tip_draw = ImageDraw.Draw(tip_mask)
    tip_draw.arc(
        (8, 8, 64, 64),
        start=angle - 20,
        end=angle + 18,
        fill=round(185 * strength),
        width=4,
    )
    tip = ImageEnhance.Brightness(frame).enhance(1 + 0.32 * strength)
    return Image.composite(tip, frame, tip_mask)


def save_gif(name, frames, duration):
    frames[0].save(
        ROOT / name,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
    )


def codex_assets():
    source = Image.open(ROOT / "codex-complete-source.png").convert("RGB")
    source.thumbnail((CODEX_SIZE, CODEX_SIZE), Image.Resampling.LANCZOS)
    ready = Image.new("RGB", (CODEX_SIZE, CODEX_SIZE), "black")
    ready.paste(
        source,
        ((CODEX_SIZE - source.width) // 2, (CODEX_SIZE - source.height) // 2),
    )
    ready.save(ROOT / "codex-ready.png")
    ImageEnhance.Brightness(ready).enhance(0.22).save(ROOT / "codex-dim.png")

    # The selected idle pane gets a restrained four-second breathing orbit.
    active_frames = []
    for index in range(16):
        phase = index / 16
        wave = (math.sin(phase * math.tau - math.pi / 2) + 1) / 2
        active_frames.append(
            orbit_frame(
                ready,
                phase=phase,
                brightness=0.82 + 0.15 * wave,
                scale=0.985 + 0.015 * wave,
                strength=0.58,
            )
        )
    save_gif("codex-active.gif", active_frames, duration=250)

    # Busy panes circulate more quickly and brightly so motion reads as work,
    # not as an alert.
    working_frames = []
    for index in range(12):
        phase = index / 12
        wave = (math.sin(phase * math.tau - math.pi / 2) + 1) / 2
        working_frames.append(
            orbit_frame(
                ready,
                phase=phase,
                brightness=0.88 + 0.12 * wave,
                scale=0.99 + 0.01 * wave,
                strength=1.0,
            )
        )
    save_gif("codex-working.gif", working_frames, duration=125)

    # Completion uses a recognizable double pulse that is more urgent than
    # either ambient animation but still settles between beats.
    done_frames = [
        ImageEnhance.Brightness(ready).enhance(factor)
        for factor in (0.58, 0.86, 1.28, 0.76, 1.16, 0.66, 0.61, 0.58)
    ]
    save_gif("codex-done.gif", done_frames, duration=125)

    # Retain the generic pulse for dictation and other non-pane activity.
    pulse_frames = []
    for factor in (0.55, 0.7, 0.88, 1.05, 1.2, 1.05, 0.88, 0.7):
        pulse_frames.append(ImageEnhance.Brightness(ready).enhance(factor))
    save_gif("codex-pulse.gif", pulse_frames, duration=125)


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    codex_assets()
    save_icon("volume-down.png", lambda draw: speaker(draw, -1))
    save_icon("volume-up.png", lambda draw: speaker(draw, 1))
    save_icon("output-mute.png", output_mute)
    save_icon("mic-mute.png", mic)
    save_icon("airpods.png", airpods)
    save_icon("dictation.png", dictation)
    save_icon("send-enter.png", send_enter)
    save_icon("new-codex.png", new_codex)
    save_icon("media-play-pause.png", media_play_pause)
