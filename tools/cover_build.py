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
# Aug 7 2026 rule: top/bottom edge spacing = 5/16" visual border + 1/4"
# bleed = 9/16" total = 169px at 300dpi. Slightly more breathing room than
# the old 112px (3/8" flat). This is specifically the TOP/BOTTOM default —
# left/right text width still uses FULL_TEXT_W below.
MARGIN = 169
TEXT_MARGIN = 187
TEXT_W = 1651

# Aug 2026 rule: by default, title/subtitle/author should each SCALE TO FILL
# this width — 0.25" bleed + 0.25" visual border per side, i.e. 0.5" total
# per side, 1.0" total off the full canvas width. This is a bigger default
# than TEXT_W above (which was a conservative safe-zone width) — the new
# rule is "fill it," not "stay comfortably inside it."
FULL_TEXT_W = CANVAS_W - int(1.0 * 300)  # = 1650px at 1950px canvas

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


def _stops_at(stops, t):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            local_t = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return lerp_color(c0, c1, local_t)
    return stops[-1][1] if t > stops[-1][0] else stops[0][1]


# APPROVED GOLD FOIL STOPS (Aug 2026) — ported directly from
# assets/effects/gold-shimmer-snippet.html's .shimmer-final linear-gradient
# (25deg, same stops used for the animated web version). Using the identical
# stops here means the static "foil still" cover treatment and the animated
# "foil shimmer" web treatment are visually the same gold, not two
# different golds that happen to both be called gold.
GOLD_FOIL_STOPS = [
    (0.00, (74, 36, 24)), (0.06, (122, 74, 30)), (0.18, (230, 182, 76)),
    (0.24, (255, 242, 192)), (0.28, (242, 161, 60)), (0.36, (201, 148, 53)),
    (0.42, (122, 74, 30)), (0.48, (230, 182, 76)), (0.52, (255, 242, 192)),
    (0.56, (242, 161, 60)), (0.62, (201, 148, 53)), (0.68, (110, 66, 24)),
    (0.76, (201, 148, 53)), (0.80, (255, 242, 192)), (0.84, (242, 161, 60)),
    (0.94, (110, 66, 24)), (1.00, (74, 36, 24)),
]
FOIL_SEED = 42
FOIL_ANGLE_DEG = 25

# STATIC GOLD FOIL (Aug 7 2026) — for the still JPEG cover only. The
# GOLD_FOIL_STOPS above (ported from the animated web shimmer) have 3
# highlight bands + 4 shadow bands, which reads fine as a moving sweep
# (only one band is "hot" at a time) but is too busy frozen as a single
# still frame. This is a calmer, single-highlight-band alternative:
# one small off-white/cream peak, warm yellow/orange midtones on both
# sides of it, and shadow ends biased slightly green (top) and slightly
# purple (bottom) rather than flat neutral brown. THIS is now the DEFAULT
# for title/author on static covers — GOLD_FOIL_STOPS remains for web use.
STATIC_GOLD_FOIL_STOPS = [
    (0.00, (54, 58, 40)),    # shadow, green-copper bias
    (0.20, (150, 100, 45)),  # warm copper-orange midtone
    (0.40, (222, 168, 70)),  # warm yellow-gold midtone
    (0.48, (250, 238, 210)), # small bright highlight, off-white/cream
    (0.52, (250, 238, 210)), # keep the peak narrow (4% of the band)
    (0.62, (222, 168, 70)),  # warm yellow-gold midtone
    (0.82, (150, 100, 55)),  # warm copper midtone
    (1.00, (50, 34, 46)),    # shadow, purple-brown bias
]


def bevel_text(canvas, text, font_path, pt_size, center_x, top_y,
                target_width, foil_stops=STATIC_GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG,
                seed=FOIL_SEED):
    """
    DEFAULT title/author treatment (Aug 7 2026): heavier weight font +
    a simple static bevel (dark shadow offset + light rim offset behind
    the gold face), echoing the web shimmer-final's 7-layer dimensional
    effect without needing animation. Returns the composited canvas.
    Use a BOLD font_path — the bevel reads as mush on a thin weight.
    """
    ink, w, h = render_ink(text, font_path, pt_size)
    ink = scale_ink_to_width(ink, target_width)
    scale = ink.width / w
    off = max(2, round(3 * scale * (pt_size / 280)))  # offset scales with size

    alpha = ink.split()[3]
    shadow = Image.new("RGBA", ink.size, (18, 10, 8, 0))
    shadow.putalpha(Image.eval(alpha, lambda a: int(a * 0.55)))
    rim = Image.new("RGBA", ink.size, (255, 235, 190, 0))
    rim.putalpha(Image.eval(alpha, lambda a: int(a * 0.5)))

    face = apply_gold_foil(ink, stops=foil_stops, angle_deg=angle_deg, seed=seed, grain_strength=8)

    x = round(center_x - ink.width / 2)
    canvas.paste(shadow, (x + off, top_y + off), shadow)
    canvas.paste(rim, (x - round(off * 0.6), top_y - round(off * 0.6)), rim)
    canvas.paste(face, (x, top_y), face)
    return canvas, ink.height


def angled_gradient_rgb(w, h, stops=GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG):
    """
    Build a w x h RGB image with a gradient running at angle_deg (matches
    the web foil shimmer's 25deg linear-gradient), NOT top-to-bottom.
    A plain vertical gradient reads as horizontal color banding across
    text — this is the effect Michael asked to retire. Angled gradients
    read as light catching a metallic surface instead.
    """
    diag = int(math.hypot(w, h)) + 4
    row = Image.new("RGB", (diag, 1))
    px = row.load()
    for x in range(diag):
        px[x, 0] = _stops_at(stops, x / (diag - 1))
    strip = row.resize((diag, diag))
    rotated = strip.rotate(angle_deg, resample=Image.BICUBIC, expand=False)
    left = (diag - w) // 2
    top = (diag - h) // 2
    return rotated.crop((left, top, left + w, top + h))


def foil_grain(w, h, seed=FOIL_SEED, strength=14):
    """Gaussian crinkle grain — subtle noise, blurred, for a foil-not-flat feel."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, strength, (h, w))
    noise_img = Image.fromarray(np.clip(noise + 128, 0, 255).astype(np.uint8), mode="L")
    return noise_img.filter(ImageFilter.GaussianBlur(radius=1.1))


def apply_gold_foil(ink, stops=GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG, seed=FOIL_SEED, grain_strength=10):
    """
    DEFAULT treatment for title + author text (Aug 2026 rule). Angled
    metallic gradient + subtle grain, alpha-masked to the ink shape.
    """
    w, h = ink.size
    alpha = ink.split()[3]
    grad = angled_gradient_rgb(w, h, stops, angle_deg).convert("RGB")
    grain = foil_grain(w, h, seed, grain_strength)
    grad_arr = np.asarray(grad).astype(int)
    grain_arr = (np.asarray(grain).astype(int) - 128)[:, :, None]
    out_arr = np.clip(grad_arr + grain_arr, 0, 255).astype(np.uint8)
    out = Image.fromarray(out_arr, mode="RGB").convert("RGBA")
    out.putalpha(alpha)
    return out


def sample_palette(image, n=5, seed=FOIL_SEED):
    """
    Extract n dominant colors from a source photo/painting via PIL's
    median-cut quantization. Used to build a subtitle treatment that
    harmonizes with that specific cover instead of a fixed hardcoded
    color — default behavior per Aug 2026 rule.
    """
    small = image.convert("RGB").resize((150, 150))
    quant = small.quantize(colors=n, method=Image.MEDIANCUT)
    palette = quant.getpalette()[: n * 3]
    colors = [tuple(palette[i:i + 3]) for i in range(0, len(palette), 3)]
    return colors


def harmonized_subtitle_stops(source_image, n=5):
    """
    Build gradient stops from a source image's sampled palette, ordered
    dark->light->dark so it still reads as a coherent gradient rather
    than a jumble. This is the default subtitle treatment — colors that
    belong to THIS cover rather than a fixed copper/gold every time.
    """
    colors = sample_palette(source_image, n=n)
    colors.sort(key=lambda c: sum(c))
    if len(colors) < 3:
        colors = colors * 3
    mid = colors[len(colors) // 2]
    dark = colors[0]
    light = colors[-1]
    # brighten the lightest stop so it still functions as a highlight
    light = tuple(min(255, int(c * 1.15) + 30) for c in light)
    dark = tuple(int(c * 0.6) for c in dark)
    n_stops = 5
    seq = [dark, mid, light, mid, dark]
    return [(i / (n_stops - 1), seq[i]) for i in range(n_stops)]


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
