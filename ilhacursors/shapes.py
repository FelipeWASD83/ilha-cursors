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
    frames: int = 0           # frames of the loop; 0 = the cursor is still once it has arrived
    jiffies: int = 2          # loop frame time in 1/60 s
    intro: Callable = None    # (x, y, u) -> layers, u from 0 to 1: played once each time Windows switches to it
    intro_frames: int = 0
    notes: str = field(default="")

    def layers(self, x, y, t):
        return self.build(x, y, t)

    @property
    def animated(self):
        return self.frames > 0

    @property
    def is_ani(self):
        return self.animated or self.intro is not None


# --- shared parts -----------------------------------------------------------------------------------

# The polygon sits inside the final outline: it is inflated by ARROW_ROUND, which rounds every corner by that much.
ARROW_TIP = (5.2, 5.2)
ARROW_PTS = [ARROW_TIP, (5.2, 21.0), (9.5, 17.3), (15.9, 16.8)]
ARROW_ROUND = 1.95
ARROW_NOTCH = 0.9  # fillet of the inner corner between the bottom and the right edge


def _arrow_hotspot():
    tx, ty = ARROW_TIP
    out = np.zeros(2)
    for px, py in (ARROW_PTS[1], ARROW_PTS[-1]):
        v = np.array([px - tx, py - ty])
        out -= v / np.linalg.norm(v)
    out /= np.linalg.norm(out)
    return (tx + out[0] * ARROW_ROUND, ty + out[1] * ARROW_ROUND)


def arrow(x, y):
    tip, left, notch, right = ARROW_PTS
    # two triangles meeting at the notch: the smooth union fillets the concave corner there
    halves = sdf.smooth_union(sdf.polygon(x, y, [tip, left, notch]), sdf.polygon(x, y, [tip, notch, right]), ARROW_NOTCH)
    return halves - ARROW_ROUND


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


# --- intros: the arrow turning into each cursor with the island's spring ---------------------------------

INTRO_FRAMES = 16  # 267 ms at 60 fps


def ease(u, damping=4.0, omega=1.5 * math.pi):
    """0 -> 1 with the island's spring: first reaches 1 at u = 1/3, ~7% overshoot, exactly 1 at u = 1."""
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    return 1 - math.exp(-damping * u) * math.cos(omega * u)


def _arrow_extent():
    """How far the drawn arrow (outline included) reaches from its hotspot: left, up, right, down."""
    c = np.linspace(0, 32, 641)
    x, y = np.meshgrid(c, c)
    inside = arrow(x, y) < 1.9 + 0.4
    hx, hy = _arrow_hotspot()
    xs, ys = x[inside], y[inside]
    return hx - xs.min(), hy - ys.min(), xs.max() - hx, ys.max() - hy


ARROW_EXTENT = _arrow_extent()


def arrow_at(x, y, hx, hy, margin=0.7):
    """The arrow with its tip on (hx, hy), shrunk only as much as it takes to stay on the canvas."""
    left, up, right, down = ARROW_EXTENT
    room = [(hx - margin) / left, (hy - margin) / up, (32 - margin - hx) / right, (32 - margin - hy) / down]
    k = min(1.0, *room)
    ax, ay = _arrow_hotspot()
    return arrow(ax + (x - hx) / k, ay + (y - hy) / k) * k


def scaled(build, x, y, cx, cy, k, t=0.0):
    """`build`'s layers scaled by k around (cx, cy)."""
    k = max(k, 0.02)
    return [(kind, d * k) for kind, d in build(cx + (x - cx) / k, cy + (y - cy) / k, t)]


def renormalise(d, x):
    """A blend of two distance fields is no longer a distance: where it changes slowly the outline
    would swell into patches. Dividing by the gradient length brings it back to one near the edge."""
    step = x[0, 1] - x[0, 0]
    gy, gx = np.gradient(d, step)
    return d / np.maximum(np.hypot(gx, gy), 0.25)


def morph_intro(build, hotspot):
    """The arrow flowing into the cursor's shape: each body is a blend of the two distance fields,
    so the outline stays one closed line all the way; details grow in at the end."""
    hx, hy = hotspot

    def intro(x, y, u):
        e = ease(u)
        a = arrow_at(x, y, hx, hy)
        out = []
        for kind, d in build(x, y, 0.0):
            if kind == "body":
                out.append(("morph", renormalise(a + (d - a) * e, x)))
            else:
                out.append((kind, d + (1 - min(e, 1.0)) * 6.0))
        return out
    return intro


def pop_intro(build, cx, cy, keep=0):
    """The first `keep` layers stay as they are; the rest grow out of (cx, cy) with the spring."""
    def intro(x, y, u):
        e = ease(u)
        return build(x, y, 0.0)[:keep] + scaled(build, x, y, cx, cy, e)[keep:]
    return intro


def busy_intro(x, y, u):
    """Arrow into the island's pill, then the comet comes out of the middle."""
    e1 = ease(u / 0.62)
    e2 = ease((u - 0.38) / 0.62)
    a = arrow_at(x, y, 16.0, 16.0)
    pill = build_busy(x, y, 0.0)[0][1]
    out = [("morph", renormalise(a + (pill - a) * e1, x))]
    if e2 > 0:
        out += scaled(build_busy, x, y, 16.0, 16.0, e2)[1:]
    return out


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


def spinning_dots(x, y, t, cx, cy, radius, dot, count=4, spacing=0.92):
    """Dots chasing each other around a circle, the head biggest; each one is a body with its own outline,
    tail first so the head lands on top."""
    layers = []
    for k in reversed(range(count)):
        a = 2 * math.pi * t - k * spacing - math.pi / 2
        layers.append(("body", sdf.circle(x, y, cx + radius * math.cos(a), cy + radius * math.sin(a),
                                          dot * (1 - 0.17 * k))))
    return layers


def build_working(x, y, t):
    return [("body", arrow(x, y))] + spinning_dots(x, y, t, 23.4, 23.6, 4.4, 1.9)


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


POCKET = 7.9


def build_move(x, y, t):
    u, v = sdf.rotate(x, y, 16.0, 16.0, 0)
    kw = dict(half=12.6, head_len=4.6, head_half=3.9, shaft=1.15)
    cross = sdf.smooth_union(double_arrow(u, v, **kw), double_arrow(v, u, **kw), 1.2)
    body = sdf.smooth_union(cross, sdf.circle(x, y, 16, 16, 2.3), 0.8)
    # the pockets between neighbouring heads are narrower than the outline; paint them in the outline
    # colour first so they read as outline instead of tiny holes
    pockets = (np.abs(u) + np.abs(v)) / math.sqrt(2) - POCKET
    return [("ink", pockets), ("body", body)]


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
    return [("body", hand)]


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


AH = _arrow_hotspot()
BX, BY, _ = BUBBLE


def _morph(file, role, label, hotspot, build, **kw):
    return Cursor(file, role, label, hotspot, build, intro=morph_intro(build, hotspot), intro_frames=INTRO_FRAMES, **kw)


def _badge(file, role, label, build):
    return Cursor(file, role, label, AH, build, intro=pop_intro(build, BX, BY, keep=1), intro_frames=INTRO_FRAMES)


# The normal arrow stays still: it comes back all the time (leaving a link, crossing windows) and an
# entrance every time would get old fast.
CURSORS = [
    Cursor("arrow", "Arrow", "Seleção normal", AH, build_arrow),
    _badge("help", "Help", "Seleção de ajuda", build_help),
    Cursor("working", "AppStarting", "Trabalhando em segundo plano", AH, build_working, frames=96, jiffies=1,
           intro=pop_intro(build_working, 23.4, 23.6, keep=1), intro_frames=INTRO_FRAMES),
    Cursor("busy", "Wait", "Ocupado", (16.0, 16.0), build_busy, frames=96, jiffies=1,
           intro=busy_intro, intro_frames=24),
    _morph("precision", "Crosshair", "Seleção de precisão", (16.0, 16.0), build_precision),
    _morph("text", "IBeam", "Seleção de texto", (16.0, 16.0), build_text),
    Cursor("handwriting", "NWPen", "Manuscrito", (4.6, 27.4), build_handwriting,
           intro=pop_intro(build_handwriting, 4.6, 27.4), intro_frames=INTRO_FRAMES),
    _morph("unavailable", "No", "Não disponível", (16.0, 16.0), build_unavailable),
    _morph("resize-ns", "SizeNS", "Redimensionamento vertical", (16.0, 16.0), _resize(90)),
    _morph("resize-ew", "SizeWE", "Redimensionamento horizontal", (16.0, 16.0), _resize(0)),
    _morph("resize-nwse", "SizeNWSE", "Redimensionamento diagonal 1", (16.0, 16.0), _resize(45)),
    _morph("resize-nesw", "SizeNESW", "Redimensionamento diagonal 2", (16.0, 16.0), _resize(-45)),
    _morph("move", "SizeAll", "Mover", (16.0, 16.0), build_move),
    _morph("alternate", "UpArrow", "Seleção alternativa", (16.0, 3.4), build_alternate),
    _morph("link", "Hand", "Seleção de link", (12.1, 2.6), build_link),
    _badge("location", "Pin", "Seleção de local", build_location),
    _badge("person", "Person", "Seleção de pessoa", build_person),
]

# Order of the comma list in HKCU\Control Panel\Cursors\Schemes.
SCHEME_ORDER = ["Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No", "SizeNS", "SizeWE",
                "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand", "Pin", "Person"]
