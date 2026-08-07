#!/usr/bin/env python3
"""
GAIA COVER BUILD ENGINE
========================
Reusable primitives for Team Gaia book covers, extracted from
project-knowledge/COVER_PRODUCTION_STANDARD.txt v4.0. This file did not
exist before Aug 2026 — every cover build had rebuilt this logic from the
spec text from scratch each session. This is the fix: encode the frozen
rules as code once, so future sessions call functions instead of
re-deriving them.

WHAT THIS DOES NOT DO: it does not encode per-book creative choices
(palette, layout tweaks, which gradient system to use). Those live in
per-book build scripts that import this module. See Section 5 of the
standard for approved per-book specs.

CANVAS SPEC (Section 1, v4.0 — 0.25" bleed):
  Trim 6"x9", full canvas 6.5"x9.5" = 1950x2850px @ 300dpi
  MARGIN = 112px, TEXT_MARGIN = 187px, TEXT_W = 1651px
"""
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import numpy as np
import math

CANVAS_W, CANVAS_H = 1950, 2850
MARGIN = 112
TEXT_MARGIN = 187
TEXT_W = 1651

CARD_W, CARD_H = 650, 962
CARD_QUALITY = 74


def render_ink(text, font_path, pt_size, pad=80):
    """
    Render text to a tightly-cropped RGBA ink image using ACTUAL pixel
    extents (not font bbox) — required so descenders and script-font
    left-edges are never clipped.

    THE EDGE-CLIPPING GUARD (fixes the historical render_ink bug where
    script fonts lost their left-edge glyph): render onto a canvas padded
    well beyond any plausible glyph overshoot, THEN measure real ink
    extent from the alpha channel, THEN crop. Never trust font.getbbox()
    for cropping — only for sizing the working canvas.

    Returns: (ink_rgba: PIL.Image in mode RGBA, ink_w: int, ink_h: int)
    Ink is returned WHITE-filled (alpha=text shape) — apply gradient after.
    """
    font = ImageFont.truetype(font_path, pt_size)
    tmp = Image.new("L", (10, 10), 0)
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font)
    work_w = (bbox[2] - bbox[0]) + pad * 2
    work_h = (bbox[3] - bbox[1]) + pad * 2

    canvas = Image.new("L", (work_w, work_h), 0)
    dc = ImageDraw.Draw(canvas)
    dc.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=255)

    arr = np.asarray(canvas)
    cols = np.where(arr.max(axis=0) > 0)[0]
    rows = np.where(arr.max(axis=1) > 0)[0]
    if len(cols) == 0 or len(rows) == 0:
        raise ValueError(f"render_ink produced no visible pixels for text={text!r}")
    x0, x1 = cols[0], cols[-1] + 1
    y0, y1 = rows[0], rows[-1] + 1

    mask = canvas.crop((x0, y0, x1, y1))
    ink_w, ink_h = mask.size
    ink = Image.new("RGBA", (ink_w, ink_h), (255, 255, 255, 0))
    ink.putalpha(mask)
    return ink, ink_w, ink_h


def scale_ink_to_width(ink, target_w):
    """LANCZOS scale to an exact target ink width, preserving aspect."""
    w, h = ink.size
    scale = target_w / w
    new_h = max(1, round(h * scale))
    return ink.resize((target_w, new_h), Image.LANCZOS)


def lerp_color(c0, c1, t):
    return tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


def apply_vertical_gradient(ink, stops):
    """
    Apply a multi-stop vertical color gradient to a white-ink RGBA image.
    stops: list of (t, (r,g,b)) with t in [0,1], sorted ascending.
    Alpha channel (the glyph shape) is preserved untouched.
    """
    w, h = ink.size
    alpha = ink.split()[3]
    grad_row = Image.new("RGB", (1, h))
    px = grad_row.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                local_t = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                px[0, y] = lerp_color(c0, c1, local_t)
                break
        else:
            px[0, y] = stops[-1][1] if t > stops[-1][0] else stops[0][1]
    grad = grad_row.resize((w, h))
    out = Image.new("RGBA", (w, h))
    out.paste(grad, (0, 0))
    out.putalpha(alpha)
    return out


def metallic_gradient_stops(base, hi, dark_mult=0.48, deep_mult=0.35):
    """
    Section 3C — 5-stop center-bright metallic gradient.
    base/hi: (r,g,b). Returns stops list for apply_vertical_gradient.
    """
    dark = tuple(int(c * dark_mult) for c in base)
    deep = tuple(int(c * deep_mult) for c in base)
    return [
        (0.00, dark), (0.18, base),
        (0.42, hi), (0.54, hi),
        (0.72, base), (1.00, deep),
    ]


def kintsugi_gold_gradient(ink, mid_gold=(180, 130, 40), highlight_gold=(255, 235, 160)):
    """
    Section 3D — Kintsugi standard gold treatment. Sine-ease highlight
    peaking at 35% of ink height, flat mid-gold from 70%-100%. No shadow
    stop. Uses ACTUAL ink pixel extent (the ink image is already tightly
    cropped by render_ink, so y_rel is just row/height here).
    """
    w, h = ink.size
    alpha = ink.split()[3]
    grad_row = Image.new("RGB", (1, h))
    px = grad_row.load()
    for y in range(h):
        y_rel = y / max(1, h - 1)
        if y_rel < 0.35:
            t = math.sin(y_rel / 0.35 * math.pi / 2)
        elif y_rel < 0.70:
            t = 1.0 - (y_rel - 0.35) / 0.35
        else:
            t = 0.0
        px[0, y] = lerp_color(mid_gold, highlight_gold, t)
    grad = grad_row.resize((w, h))
    out = Image.new("RGBA", (w, h))
    out.paste(grad, (0, 0))
    out.putalpha(alpha)
    return out


def visual_center_paste(canvas, ink, center_x, y):
    """
    Paste ink onto canvas horizontally centered on center_x, using the
    ink's OWN non-transparent pixel extent (not its bbox/canvas midpoint —
    since render_ink already tight-crops, ink.size IS the true extent).
    y = top-left y coordinate to paste at.
    """
    w, h = ink.size
    x = round(center_x - w / 2)
    canvas.paste(ink, (x, y), ink)
    return canvas


def bottom_gradient_overlay(canvas, start_frac=0.65, color=(8, 4, 1), max_alpha=180):
    """Section 4 — cubic ease-in bottom gradient, avoids banding."""
    w, h = canvas.size
    start_y = int(h * start_frac)
    row = Image.new("RGBA", (1, h), (0, 0, 0, 0))
    rpx = row.load()
    for y in range(h):
        if y < start_y:
            rpx[0, y] = (0, 0, 0, 0)
        else:
            t = (y - start_y) / max(1, h - start_y)
            a = int(max_alpha * (t ** 3))
            rpx[0, y] = (*color, a)
    grad = row.resize((w, h))
    return Image.alpha_composite(canvas.convert("RGBA"), grad)


def prep_photo_fullbleed(photo, exif_correct=True):
    """Section 4 — EXIF-correct, fill canvas via LANCZOS. No color adjustment."""
    if exif_correct:
        photo = ImageOps.exif_transpose(photo)
    photo = photo.convert("RGB")
    src_w, src_h = photo.size
    scale = max(CANVAS_W / src_w, CANVAS_H / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    photo = photo.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - CANVAS_W) // 2
    top = (new_h - CANVAS_H) // 2
    return photo.crop((left, top, left + CANVAS_W, top + CANVAS_H))


def export_card(full_cover, out_path, quality=CARD_QUALITY):
    """Section 5/6 — 650x962 web card, JPEG, target <85KB."""
    card = full_cover.convert("RGB").resize((CARD_W, CARD_H), Image.LANCZOS)
    card.save(out_path, "JPEG", quality=quality)
    return out_path
