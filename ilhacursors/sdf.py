"""Signed distance primitives on numpy grids.

Every shape is a function of the sample coordinates (x, y) in design units: the canvas is always
32 x 32 units, whatever the pixel size, with y growing downwards like the screen. Negative = inside.
"""

import numpy as np


def circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def capsule(x, y, ax, ay, bx, by, r):
    pax, pay = x - ax, y - ay
    bax, bay = bx - ax, by - ay
    h = np.clip((pax * bax + pay * bay) / (bax * bax + bay * bay), 0.0, 1.0)
    return np.hypot(pax - bax * h, pay - bay * h) - r


def polyline(x, y, pts, r):
    d = None
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        s = capsule(x, y, ax, ay, bx, by, r)
        d = s if d is None else np.minimum(d, s)
    return d


def rounded_box(x, y, cx, cy, hw, hh, r):
    qx = np.abs(x - cx) - (hw - r)
    qy = np.abs(y - cy) - (hh - r)
    outside = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    return outside + inside - r


def polygon(x, y, pts):
    pts = [np.asarray(p, dtype=float) for p in pts]
    d = (x - pts[0][0]) ** 2 + (y - pts[0][1]) ** 2
    s = np.ones_like(x)
    n = len(pts)
    for i in range(n):
        vi, vj = pts[i], pts[i - 1]
        ex, ey = vj[0] - vi[0], vj[1] - vi[1]
        wx, wy = x - vi[0], y - vi[1]
        h = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0.0, 1.0)
        bx, by = wx - ex * h, wy - ey * h
        d = np.minimum(d, bx * bx + by * by)
        c1 = y >= vi[1]
        c2 = y < vj[1]
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def union(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.minimum(out, d)
    return out


def smooth_union(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def intersect(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.maximum(out, d)
    return out


def subtract(a, b):
    return np.maximum(a, -b)


def rotate(x, y, cx, cy, degrees):
    """Coordinates of (x, y) in a frame centred on (cx, cy) and turned by `degrees` (clockwise on screen)."""
    a = np.radians(degrees)
    dx, dy = x - cx, y - cy
    c, s = np.cos(a), np.sin(a)
    return dx * c + dy * s, -dx * s + dy * c
