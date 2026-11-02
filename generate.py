"""Builds the Ilha cursor schemes into build/<variant>/.

    python generate.py            # both variants
    python generate.py --png      # also writes the raw 128 px renders to build/png/ (for checking the drawing)
"""

import argparse
import json
import time
from pathlib import Path

from PIL import Image

from ilhacursors.fileformats import ani_bytes, cur_bytes
from ilhacursors.render import CANVAS, VARIANTS, render
from ilhacursors.shapes import CURSORS, SCHEME_ORDER

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
VERSION = "1.1.0"

STATIC_SIZES = [32, 48, 64, 96, 128, 256]
# Windows refuses an .ani whose frames hold more than four sizes (measured on 26300: four load, five do not).
ANIMATED_SIZES = [32, 48, 64, 128]

SCHEME_NAMES = {"black": "Ilha preto", "white": "Ilha branco"}

# After the intro the last frame is held for a day (in 1/60 s), so the entrance plays once per switch.
HOLD = 60 * 60 * 60 * 24
# Windows refuses an .ani with 65,536 steps or more (65,524 loads); loops repeat until just under this.
MAX_STEPS = 60000


class _Layers:
    """Gives render() a .layers for any (x, y, param) function."""

    def __init__(self, fn):
        self.layers = fn


def hotspot_px(cursor, size):
    hx, hy = cursor.hotspot
    clamp = lambda v: max(0, min(size - 1, int(v * size / CANVAS)))
    return clamp(hx), clamp(hy)


def images_for(cursor, variant, sizes, t=0.0, source=None):
    source = source or cursor
    return [(render(source, s, variant, t), *hotspot_px(cursor, s)) for s in sizes]


def ani_plan(cursor):
    """The frames to draw, as (source, param), and the step list that plays them.

    Static cursor with an intro: intro frames, then the final frame held.
    Looping cursor: intro (if any), then the loop repeated up to MAX_STEPS."""
    frames, sequence, rates = [], [], []
    if cursor.intro:
        intro = _Layers(cursor.intro)
        n = cursor.intro_frames
        frames += [(intro, i / n) for i in range(n)]
        sequence += list(range(n))
        rates += [1] * n
    first = len(frames)
    if cursor.animated:
        frames += [(cursor, i / cursor.frames) for i in range(cursor.frames)]
        repeats = max(1, (MAX_STEPS - len(sequence)) // cursor.frames)
        sequence += [first + k for k in range(cursor.frames)] * repeats
        rates += [cursor.jiffies] * (cursor.frames * repeats)
    else:
        frames.append((cursor, 0.0))
        sequence.append(first)
        rates.append(HOLD)
    return frames, sequence, rates


def build_variant(variant, png_dir=None):
    out = BUILD / variant
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.cur")) + list(out.glob("*.ani")):
        old.unlink()
    files = {}
    for cursor in CURSORS:
        if cursor.is_ani:
            plan, sequence, rates = ani_plan(cursor)
            frames = []
            for i, (source, param) in enumerate(plan):
                imgs = images_for(cursor, variant, ANIMATED_SIZES, param, source)
                frames.append(cur_bytes(imgs))
                if png_dir and i % 6 == 0:
                    Image.fromarray(imgs[-1][0]).save(png_dir / f"{variant}-{cursor.file}-{i:03d}.png")
            data = ani_bytes(frames, 1, title=f"{SCHEME_NAMES[variant]}: {cursor.label}", artist="Felipe",
                             sequence=sequence, rates=rates)
            name = f"{cursor.file}.ani"
        else:
            imgs = images_for(cursor, variant, STATIC_SIZES)
            data = cur_bytes(imgs)
            name = f"{cursor.file}.cur"
            if png_dir:
                Image.fromarray(imgs[-2][0]).save(png_dir / f"{variant}-{cursor.file}.png")
        (out / name).write_bytes(data)
        files[cursor.role] = name
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--variant", choices=list(VARIANTS))
    args = ap.parse_args()

    png_dir = None
    if args.png:
        png_dir = BUILD / "png"
        png_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"version": VERSION, "order": SCHEME_ORDER, "schemes": {}}
    for variant in [args.variant] if args.variant else VARIANTS:
        start = time.perf_counter()
        files = build_variant(variant, png_dir)
        manifest["schemes"][variant] = {"name": SCHEME_NAMES[variant], "files": files}
        print(f"{variant}: {len(files)} cursors in {time.perf_counter() - start:.1f} s")

    manifest_path = BUILD / "manifest.json"
    if args.variant and manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        old["schemes"].update(manifest["schemes"])
        manifest["schemes"] = old["schemes"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
