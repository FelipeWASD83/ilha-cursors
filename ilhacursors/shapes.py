"""The seventeen Windows pointer roles, drawn in the island's language: pills, soft corners, a bubble
next to the pointer (like the island's split state) and the orbiting dots of its loading animations.

Coordinates are design units on a 32 x 32 canvas (see sdf.py)."""

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from . import sdf


@dataclass
class Cursor:
    file: str                 # file name without extension
    role: str                 # value name under HKCU\Control Panel\Cursors
    label: str                # role name as Windows shows it (pt-BR)
    hotspot: tuple            # design units
    build: Callable           # (x, y, t) -> list of layers
    frames: int = 0           # 0 = static .cur, otherwise .ani
    jiffies: int = 2          # frame time in 1/60 s
    notes: str = field(default="")

    def layers(self, x, y, t):
        return self.build(x, y, t)

    @property
    def animated(self):
        return self.frames > 0


# --- shared parts -----------------------------------------------------------------------------------

ARROW_TIP = (4.4, 3.6)
ARROW_PTS = [ARROW_TIP, (4.4, 21.6), (8.9, 17.5), (16.2, 17.1)]
ARROW_ROUND = 1.25


def _arrow_hotspot():
    tx, ty = ARROW_TIP
    out = np.zeros(2)
    for px, py in (ARROW_PTS[1], ARROW_PTS[-1]):
        v = np.array([px - tx, py - ty])
        out -= v / np.linalg.norm(v)
    out /= np.linalg.norm(out)
    return (tx + out[0] * ARROW_ROUND, ty + out[1] * ARROW_ROUND)


def arrow(x, y):
    return sdf.polygon(x, y, ARROW_PTS) - ARROW_ROUND


BUBBLE = (23.4, 23.4, 6.1)


def bubble(x, y):
    cx, cy, r = BUBBLE
    return sdf.circle(x, y, cx, cy, r)


def orbit_comet(x, y, t, cx, cy, rx, ry, r, trail=5, spacing=0.46):
    """The island's comet on its 3D orbit seen from above: a head with a fading tail; whatever is
    behind the centre is smaller and dimmer and is drawn first."""
    dots = []
    for k in range(trail):
        a = 2 * math.pi * t - k * spacing
        depth = math.sin(a)  # +1 = nearest (lower on screen)
        px, py = cx + rx * math.cos(a), cy + ry * depth
        radius = r * (1 - 0.13 * k) * (0.8 + 0.2 * (depth + 1) / 2)
        shade = (1 - 0.16 * k) * (0.66 + 0.34 * (depth + 1) / 2)
        dots.append((depth, sdf.circle(x, y, px, py, radius), shade))
    dots.sort(key=lambda d: d[0])
    return [(("dim", shade), d) for _, d, shade in dots]


def spring(t, damping=6.0, omega=2.5 * math.pi):
    """A periodic 0 -> 1 -> 0 swell that settles like the island's springs (~9% overshoot), t in [0, 1)."""
    if t < 0.5:
        u = t / 0.5
        return 1 - math.exp(-damping * u) * math.cos(omega * u)
    u = (t - 0.5) / 0.5
    return math.exp(-damping * u) * math.cos(omega * u)


def double_arrow(u, v, half=12.0, head_len=5.2, head_half=4.5, shaft=1.2):
    """A two-headed arrow along u, centred on the origin."""
    base = half - head_len
    head_a = sdf.polygon(u, v, [(half, 0), (base, head_half), (base, -head_half)])
    head_b = sdf.polygon(u, v, [(-half, 0), (-base, -head_half), (-base, head_half)])
    heads = sdf.union(head_a, head_b) - 0.85
    body = sdf.capsule(u, v, -base, 0, base, 0, shaft)
    return sdf.smooth_union(heads, body, 0.8)


# --- the roles --------------------------------------------------------------------------------------

def build_arrow(x, y, t):
    return [("body", arrow(x, y))]


def build_help(x, y, t):
    cx, cy, r = BUBBLE
    s = r / 6.1
    hook = []
    for i in range(15):
        a = math.radians(178 + (402 - 178) * i / 14)
        hook.append((cx + s * 2.15 * math.cos(a), cy + s * (-1.55 + 2.15 * math.sin(a))))
    hook += [(cx + s * 0.05, cy + s * 1.05), (cx, cy + s * 1.35)]
    glyph = sdf.union(sdf.polyline(x, y, hook, s * 0.92), sdf.circle(x, y, cx, cy + s * 3.55, s * 1.0))
    return [("body", arrow(x, y)), ("body", bubble(x, y)), ("ink", glyph)]


def build_working(x, y, t):
    cx, cy = 22.6, 24.4
    swell = 0.8 * spring(t)
    pill = sdf.capsule(x, y, cx - 3.0 - swell, cy, cx + 3.0 + swell, cy, 4.15)
    return [("body", arrow(x, y)), ("body", pill)] + orbit_comet(x, y, t, cx, cy, 3.3 + swell, 1.25, 1.12, trail=4)


def build_busy(x, y, t):
    cx, cy = 16.0, 16.0
    swell = 2.0 * spring(t)
    pill = sdf.capsule(x, y, cx - 5.6 - swell, cy, cx + 5.6 + swell, cy, 5.6)
    return [("body", pill)] + orbit_comet(x, y, t, cx, cy, 6.2 + swell, 2.2, 1.7)


def build_precision(x, y, t):
    c, gap, end, r = 16.0, 3.6, 12.0, 0.95
    arms = sdf.union(
        sdf.capsule(x, y, c, c - gap, c, c - end, r),
        sdf.capsule(x, y, c, c + gap, c, c + end, r),
        sdf.capsule(x, y, c - gap, c, c - end, c, r),
        sdf.capsule(x, y, c + gap, c, c + end, c, r),
    )
    return [("body", sdf.union(arms, sdf.circle(x, y, c, c, 1.25)))]


def build_text(x, y, t):
    c = 16.0
    stem = sdf.capsule(x, y, c, 7.6, c, 24.4, 1.0)
    caps = []
    for yy, bend in ((6.2, 1.0), (25.8, -1.0)):
        caps.append(sdf.polyline(x, y, [(c - 3.6, yy - 0.5 * bend), (c - 1.4, yy + 0.25 * bend), (c, yy + 0.9 * bend),
                                        (c + 1.4, yy + 0.25 * bend), (c + 3.6, yy - 0.5 * bend)], 0.95))
    return [("body", sdf.smooth_union(stem, sdf.union(*caps), 0.9))]


def build_handwriting(x, y, t):
    tip = (4.6, 27.4)
    u, v = sdf.rotate(x, y, tip[0], tip[1], -45)  # u runs from the tip up and to the right
    nib = sdf.polygon(u, v, [(0.0, 0.0), (6.2, 3.0), (6.2, -3.0)]) - 0.55
    body = sdf.rounded_box(u, v, 14.6, 0.0, 8.6, 3.0, 3.0)
    pen = sdf.smooth_union(nib, body, 0.5)
    collar = sdf.intersect(np.abs(u - 6.7) - 0.45, pen + 0.2)
    lead = sdf.circle(u, v, 1.25, 0.0, 0.85)
    return [("body", pen), ("ink", collar), ("ink", lead)]


def build_unavailable(x, y, t):
    c, R = 16.0, 9.6
    ring = np.abs(sdf.circle(x, y, c, c, R)) - 1.55
    k = R * math.cos(math.radians(45))
    slash = sdf.capsule(x, y, c - k, c - k, c + k, c + k, 1.55)
    return [("body", sdf.union(ring, slash))]


def _resize(angle):
    def build(x, y, t):
        u, v = sdf.rotate(x, y, 16.0, 16.0, angle)
        half = 12.0 if angle % 90 == 0 else 11.4
        return [("body", double_arrow(u, v, half=half))]
    return build


def build_move(x, y, t):
    u, v = sdf.rotate(x, y, 16.0, 16.0, 0)
    kw = dict(half=12.6, head_len=4.6, head_half=3.9, shaft=1.15)
    cross = sdf.smooth_union(double_arrow(u, v, **kw), double_arrow(v, u, **kw), 1.2)
    return [("body", sdf.smooth_union(cross, sdf.circle(x, y, 16, 16, 2.3), 0.8))]


def build_alternate(x, y, t):
    c = 16.0
    head = sdf.polygon(x, y, [(c, 3.4), (c + 6.6, 11.6), (c - 6.6, 11.6)]) - 1.0
    shaft = sdf.capsule(x, y, c, 10.0, c, 27.6, 1.9)
    return [("body", sdf.smooth_union(head, shaft, 0.8))]


def build_link(x, y, t):
    index = sdf.capsule(x, y, 12.1, 4.6, 12.1, 16.0, 2.35)
    fingers = [
        sdf.capsule(x, y, 16.75, 12.2, 16.75, 17.0, 2.25),
        sdf.capsule(x, y, 21.2, 13.2, 21.2, 18.0, 2.15),
        sdf.capsule(x, y, 25.4, 14.6, 25.4, 19.0, 1.95),
    ]
    palm = sdf.rounded_box(x, y, 18.6, 21.2, 8.6, 7.0, 5.2)
    thumb = sdf.capsule(x, y, 11.6, 21.6, 6.6, 16.6, 2.25)
    hand = palm
    for part in [index, thumb] + fingers:
        hand = sdf.smooth_union(hand, part, 0.9)
    seams = []
    prev = index
    for f in fingers:
        # the line where a finger meets the one on its left, only above the palm
        seam = sdf.intersect(np.abs(f) - 0.5, prev, y - 17.2, hand + 0.9)
        seams.append(seam)
        prev = f
    return [("body", hand), ("ink", sdf.union(*seams))]


def build_location(x, y, t):
    cx, cy, r = BUBBLE
    s = r / 6.1
    head = sdf.circle(x, y, cx, cy - s * 1.1, s * 2.75)
    point = sdf.polygon(x, y, [(cx - s * 2.35, cy + s * 0.3), (cx + s * 2.35, cy + s * 0.3), (cx, cy + s * 4.1)]) - s * 0.35
    pin = sdf.smooth_union(head, point, s * 0.8)
    hole = sdf.circle(x, y, cx, cy - s * 1.1, s * 1.05)
    return [("body", arrow(x, y)), ("body", bubble(x, y)), ("ink", pin), ("fill", hole)]


def build_person(x, y, t):
    cx, cy, r = BUBBLE
    s = r / 6.1
    head = sdf.circle(x, y, cx, cy - s * 1.75, s * 1.7)
    shoulders = sdf.intersect(sdf.rounded_box(x, y, cx, cy + s * 3.0, s * 3.4, s * 2.4, s * 2.4), y - (cy + s * 3.5))
    return [("body", arrow(x, y)), ("body", bubble(x, y)), ("ink", sdf.union(head, shoulders))]


CURSORS = [
    Cursor("arrow", "Arrow", "Seleção normal", _arrow_hotspot(), build_arrow),
    Cursor("help", "Help", "Seleção de ajuda", _arrow_hotspot(), build_help),
    Cursor("working", "AppStarting", "Trabalhando em segundo plano", _arrow_hotspot(), build_working, frames=48),
    Cursor("busy", "Wait", "Ocupado", (16.0, 16.0), build_busy, frames=48),
    Cursor("precision", "Crosshair", "Seleção de precisão", (16.0, 16.0), build_precision),
    Cursor("text", "IBeam", "Seleção de texto", (16.0, 16.0), build_text),
    Cursor("handwriting", "NWPen", "Manuscrito", (4.6, 27.4), build_handwriting),
    Cursor("unavailable", "No", "Não disponível", (16.0, 16.0), build_unavailable),
    Cursor("resize-ns", "SizeNS", "Redimensionamento vertical", (16.0, 16.0), _resize(90)),
    Cursor("resize-ew", "SizeWE", "Redimensionamento horizontal", (16.0, 16.0), _resize(0)),
    Cursor("resize-nwse", "SizeNWSE", "Redimensionamento diagonal 1", (16.0, 16.0), _resize(45)),
    Cursor("resize-nesw", "SizeNESW", "Redimensionamento diagonal 2", (16.0, 16.0), _resize(-45)),
    Cursor("move", "SizeAll", "Mover", (16.0, 16.0), build_move),
    Cursor("alternate", "UpArrow", "Seleção alternativa", (16.0, 3.4), build_alternate),
    Cursor("link", "Hand", "Seleção de link", (12.1, 2.6), build_link),
    Cursor("location", "Pin", "Seleção de local", _arrow_hotspot(), build_location),
    Cursor("person", "Person", "Seleção de pessoa", _arrow_hotspot(), build_person),
]

# Order of the comma list in HKCU\Control Panel\Cursors\Schemes.
SCHEME_ORDER = ["Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No", "SizeNS", "SizeWE",
                "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand", "Pin", "Person"]
