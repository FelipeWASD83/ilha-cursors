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
VERSION = "1.0.2"

STATIC_SIZES = [32, 48, 64, 96, 128, 256]
# Windows refuses an .ani whose frames hold more than four sizes (measured on 26300: four load, five do not).
ANIMATED_SIZES = [32, 48, 64, 128]

SCHEME_NAMES = {"black": "Ilha preto", "white": "Ilha branco"}


def hotspot_px(cursor, size):
    hx, hy = cursor.hotspot
    clamp = lambda v: max(0, min(size - 1, int(v * size / CANVAS)))
    return clamp(hx), clamp(hy)


def images_for(cursor, variant, sizes, t=0.0):
    return [(render(cursor, s, variant, t), *hotspot_px(cursor, s)) for s in sizes]


def build_variant(variant, png_dir=None):
    out = BUILD / variant
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for cursor in CURSORS:
        if cursor.animated:
            frames = []
            for i in range(cursor.frames):
                imgs = images_for(cursor, variant, ANIMATED_SIZES, i / cursor.frames)
                frames.append(cur_bytes(imgs))
                if png_dir and i % (cursor.frames // 8) == 0:
                    Image.fromarray(imgs[-1][0]).save(png_dir / f"{variant}-{cursor.file}-{i:02d}.png")
            data = ani_bytes(frames, cursor.jiffies, title=f"{SCHEME_NAMES[variant]}: {cursor.label}", artist="Felipe")
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
