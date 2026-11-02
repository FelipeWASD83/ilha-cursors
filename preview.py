"""Loads every built cursor through the Windows API (the same path the system uses), checks the hotspot
and the frame count, and draws a sheet with what Windows itself renders, over light, dark and busy
backgrounds. Nothing on the system changes.

    python preview.py               # build/preview-<variant>.png and build/preview-anim-<variant>.png
"""

import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from generate import ANIMATED_SIZES, BUILD, STATIC_SIZES, hotspot_px
from ilhacursors.shapes import CURSORS

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

IMAGE_CURSOR, LR_LOADFROMFILE, DI_NORMAL = 2, 0x10, 3
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                              wintypes.UINT]
user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HANDLE, ctypes.c_int, ctypes.c_int,
                              wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
user32.DestroyCursor.argtypes = [wintypes.HANDLE]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
                                   wintypes.HANDLE, wintypes.DWORD]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD), ("yHotspot", wintypes.DWORD),
                ("hbmMask", wintypes.HBITMAP), ("hbmColor", wintypes.HBITMAP)]


user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]


def load(path, size):
    h = user32.LoadImageW(None, str(path), IMAGE_CURSOR, size, size, LR_LOADFROMFILE)
    if not h:
        raise RuntimeError(f"Windows refused {path.name} at {size} px (error {ctypes.get_last_error()})")
    return h


def hotspot_of(h):
    info = ICONINFO()
    if not user32.GetIconInfo(h, ctypes.byref(info)):
        return None
    for bm in (info.hbmMask, info.hbmColor):
        if bm:
            gdi32.DeleteObject(bm)
    return info.xHotspot, info.yHotspot


def draw(h, size, background, step=0):
    """What Windows paints for cursor `h` over `background` (an RGB array size x size)."""
    hdc = gdi32.CreateCompatibleDC(None)
    bmi = (ctypes.c_byte * 44)()
    ctypes.memmove(bmi, ctypes.c_char_p(np.array([40, size, -size], dtype="<i4").tobytes() +
                                        np.array([1, 32], dtype="<u2").tobytes()), 16)
    bits = ctypes.c_void_p()
    dib = gdi32.CreateDIBSection(hdc, bmi, 0, ctypes.byref(bits), None, 0)
    old = gdi32.SelectObject(hdc, dib)
    buf = (ctypes.c_uint8 * (size * size * 4)).from_address(bits.value)
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(size, size, 4)
    arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3] = background[..., 2], background[..., 1], background[..., 0], 0
    ok = user32.DrawIconEx(hdc, 0, 0, h, size, size, step, None, DI_NORMAL)
    out = arr[..., [2, 1, 0]].copy()
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(dib)
    gdi32.DeleteDC(hdc)
    if not ok:
        raise RuntimeError(f"DrawIconEx failed (error {ctypes.get_last_error()})")
    return out


def backgrounds(size):
    yy, xx = np.mgrid[0:size, 0:size] / max(1, size - 1)
    light = np.full((size, size, 3), 236, np.uint8)
    dark = np.full((size, size, 3), 24, np.uint8)
    busy = np.stack([60 + 160 * xx, 90 + 120 * yy, 200 - 140 * xx * yy], -1)
    stripes = ((np.mgrid[0:size, 0:size].sum(0) // max(2, size // 8)) % 2).astype(bool)
    busy[stripes] *= 0.55
    return {"light": light, "dark": dark, "busy": busy.astype(np.uint8)}


def font(px):
    try:
        return ImageFont.truetype("segoeui.ttf", px)
    except OSError:
        return ImageFont.load_default()


def check_and_sheet(variant, files):
    folder = BUILD / variant
    problems = []
    show = [32, 48, 96]
    cell = 104
    label_h = 22
    cols = len(CURSORS)
    rows = [(bg, s) for bg in ("light", "dark", "busy") for s in show]
    sheet = Image.new("RGB", (120 + cols * cell, 60 + len(rows) * cell), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), f"Ilha ({variant}) desenhado pelo Windows", fill=(20, 20, 20), font=font(18))
    for c, cursor in enumerate(CURSORS):
        path = folder / files[cursor.role]
        d.text((120 + c * cell + 4, 60 - label_h + 2), cursor.file, fill=(60, 60, 60), font=font(11))
        sizes = ANIMATED_SIZES if cursor.animated else STATIC_SIZES
        for s in sizes:
            h = load(path, s)
            hs = hotspot_of(h)
            if hs != hotspot_px(cursor, s):
                problems.append(f"{path.name} {s}px: hotspot {hs}, expected {hotspot_px(cursor, s)}")
            user32.DestroyCursor(h)
        for r, (bg, s) in enumerate(rows):
            h = load(path, s)
            img = draw(h, s, backgrounds(s)[bg])
            user32.DestroyCursor(h)
            tile = Image.fromarray(img)
            scale = max(1, (cell - 8) // s)
            tile = tile.resize((s * scale, s * scale), Image.NEAREST)
            x0 = 120 + c * cell + (cell - tile.width) // 2
            y0 = 60 + r * cell + (cell - tile.height) // 2
            sheet.paste(tile, (x0, y0))
    for r, (bg, s) in enumerate(rows):
        d.text((10, 60 + r * cell + cell // 2 - 8), f"{bg} {s}px", fill=(60, 60, 60), font=font(13))
    sheet.save(BUILD / f"preview-{variant}.png")

    # animation strip: every 4th frame of the animated cursors at 64 px, light and dark
    anim = [c for c in CURSORS if c.animated]
    s = 64
    steps = list(range(0, anim[0].frames, anim[0].frames // 12))
    strip = Image.new("RGB", (len(steps) * (s + 8) + 8, len(anim) * 2 * (s + 8) + 8), (250, 250, 250))
    for a, cursor in enumerate(anim):
        h = load(folder / files[cursor.role], s)
        for i, step in enumerate(steps):
            for k, bg in enumerate(("light", "dark")):
                img = draw(h, s, backgrounds(s)[bg], step)
                strip.paste(Image.fromarray(img), (8 + i * (s + 8), 8 + (a * 2 + k) * (s + 8)))
        user32.DestroyCursor(h)
    strip.save(BUILD / f"preview-anim-{variant}.png")
    return problems


def main():
    manifest = json.loads((BUILD / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for variant, scheme in manifest["schemes"].items():
        problems += check_and_sheet(variant, scheme["files"])
        print(f"{variant}: {len(scheme['files'])} cursors loaded by Windows at every size")
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
