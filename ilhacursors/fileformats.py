"""Writers for Windows .cur (one file, several sizes) and .ani (RIFF ACON of .cur frames)."""

import struct

import numpy as np


def _dib(rgba):
    """32-bit BGRA bitmap with the AND mask, the way an icon directory entry stores it."""
    h, w, _ = rgba.shape
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    bgra = rgba[::-1, :, [2, 1, 0, 3]].tobytes()  # bottom-up
    row_bytes = ((w + 31) // 32) * 4
    mask = bytearray()
    transparent = rgba[::-1, :, 3] == 0
    for row in transparent:
        bits = np.packbits(row.astype(np.uint8))
        mask += bits.tobytes().ljust(row_bytes, b"\0")
    return header + bgra + bytes(mask)


def cur_bytes(images):
    """images: list of (rgba ndarray, hotspot_x, hotspot_y) in pixels."""
    count = len(images)
    out = struct.pack("<HHH", 0, 2, count)
    blobs = [_dib(img) for img, _, _ in images]
    offset = 6 + 16 * count
    for (img, hx, hy), blob in zip(images, blobs):
        h, w, _ = img.shape
        out += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, hx, hy, len(blob), offset)
        offset += len(blob)
    return out + b"".join(blobs)


def _chunk(tag, data):
    pad = b"\0" if len(data) % 2 else b""
    return tag + struct.pack("<I", len(data)) + data + pad


def ani_bytes(frames, jiffies, title="", artist=""):
    """frames: list of cur_bytes() results, all shown for `jiffies` sixtieths of a second."""
    anih = struct.pack("<9I", 36, len(frames), len(frames), 0, 0, 0, 0, jiffies, 1)  # 1 = AF_ICON
    body = b"ACON" + _chunk(b"anih", anih)
    info = b""
    if title:
        info += _chunk(b"INAM", title.encode("cp1252") + b"\0")
    if artist:
        info += _chunk(b"IART", artist.encode("cp1252") + b"\0")
    if info:
        body += _chunk(b"LIST", b"INFO" + info)
    body += _chunk(b"LIST", b"fram" + b"".join(_chunk(b"icon", f) for f in frames))
    return b"RIFF" + struct.pack("<I", len(body)) + body
