"""Turns a cursor's layers into an RGBA image.

A cursor is a list of layers in painting order. Each layer is (kind, distance):
- "body": the island look, a fill in the variant colour with an outline in the inverse colour;
- "ink": drawn in the outline colour (glyphs, dots);
- "fill": drawn in the fill colour (holes inside a glyph);
- ("dim", a): ink mixed towards the fill colour, a = 1 is full ink (the dots behind the orbit).
A later body's outline cuts across the bodies under it, which is what separates the badge from the arrow.
"""

import numpy as np

CANVAS = 32.0
OUTLINE = 1.5
SUPERSAMPLE = 3
SHADOW_OFFSET = (0.35, 1.0)
SHADOW_SIGMA = 1.15
SHADOW_ALPHA = 0.38

VARIANTS = {
    # name: (fill, ink) in 0..1 grey
    "black": (0.0, 1.0),
    "white": (1.0, 0.0),
}


def grid(size):
    n = size * SUPERSAMPLE
    c = (np.arange(n) + 0.5) * CANVAS / n
    x, y = np.meshgrid(c, c)
    return x, y, CANVAS / n


def _coverage(d, unit):
    return np.clip(0.5 - d / unit, 0.0, 1.0)


def _blur(a, sigma_px):
    radius = max(1, int(np.ceil(sigma_px * 3)))
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma_px) ** 2)
    k /= k.sum()
    h, w = a.shape
    padded = np.pad(a, ((0, 0), (radius, radius)))
    rows = sum(kw * padded[:, i:i + w] for i, kw in enumerate(k))
    padded = np.pad(rows, ((radius, radius), (0, 0)))
    return sum(kw * padded[i:i + h] for i, kw in enumerate(k))


def _shift(a, dx_px, dy_px):
    """Moves `a` by a fractional number of pixels (bilinear), filling with zero."""
    out = np.zeros_like(a)
    ix, fx = int(np.floor(dx_px)), dx_px - np.floor(dx_px)
    iy, fy = int(np.floor(dy_px)), dy_px - np.floor(dy_px)
    h, w = a.shape
    for oy, wy in ((iy, 1 - fy), (iy + 1, fy)):
        for ox, wx in ((ix, 1 - fx), (ix + 1, fx)):
            if wx * wy == 0:
                continue
            src = a[max(0, -oy):h - max(0, oy), max(0, -ox):w - max(0, ox)]
            out[max(0, oy):max(0, oy) + src.shape[0], max(0, ox):max(0, ox) + src.shape[1]] += wx * wy * src
    return out


def render(cursor, size, variant, t=0.0):
    fill, ink = VARIANTS[variant]
    x, y, unit = grid(size)
    layers = cursor.layers(x, y, t)

    colour = np.zeros_like(x)  # premultiplied grey
    alpha = np.zeros_like(x)

    def over(grey, a):
        nonlocal colour, alpha
        colour = grey * a + colour * (1 - a)
        alpha = a + alpha * (1 - a)

    bodies = [d for kind, d in layers if kind == "body"]
    if bodies:
        silhouette = _coverage(np.minimum.reduce(bodies) - OUTLINE, unit)
        px = 1.0 / unit
        shadow = _shift(silhouette, SHADOW_OFFSET[0] * px, SHADOW_OFFSET[1] * px)
        shadow = _blur(shadow, SHADOW_SIGMA * px) * SHADOW_ALPHA
        over(0.0, shadow)

    for kind, d in layers:
        if kind == "body":
            over(ink, _coverage(d - OUTLINE, unit))
            over(fill, _coverage(d, unit))
        elif kind == "ink":
            over(ink, _coverage(d, unit))
        elif kind == "fill":
            over(fill, _coverage(d, unit))
        elif isinstance(kind, tuple) and kind[0] == "dim":
            over(fill + (ink - fill) * kind[1], _coverage(d, unit))
        else:
            raise ValueError(f"unknown layer kind {kind!r}")

    s = SUPERSAMPLE
    n = size
    colour = colour.reshape(n, s, n, s).mean(axis=(1, 3))
    alpha = alpha.reshape(n, s, n, s).mean(axis=(1, 3))
    grey = np.where(alpha > 1e-6, colour / np.maximum(alpha, 1e-6), 0.0)

    rgba = np.zeros((n, n, 4), dtype=np.uint8)
    g = np.clip(np.round(grey * 255), 0, 255).astype(np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = g
    rgba[..., 3] = np.clip(np.round(alpha * 255), 0, 255).astype(np.uint8)
    return rgba
