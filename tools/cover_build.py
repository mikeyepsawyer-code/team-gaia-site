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

CANVAS SPEC (Section 1, v4.1 — 0.25" bleed):
  Trim 6"x9", full canvas 6.5"x9.5" = 1950x2850px @ 300dpi
  MARGIN = 169px (5/16" visual border + 1/4" bleed = 9/16", SYMMETRIC
  top and bottom by rule), TEXT_MARGIN = 187px, TEXT_W = 1651px
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

# TITLE_TOP_Y / AUTHOR_BOTTOM_Y (added Aug 13 2026 -- closes a repeated bug
# where per-book scripts added an ad-hoc offset to the title's top position
# ("MARGIN + 40") without ever matching it on the author's bottom position,
# breaking the symmetric top/bottom margin rule above. ALWAYS use these two
# constants directly for title top_y and author bottom edge -- never add or
# subtract an extra offset to either one. If a book needs more breathing
# room, that's a MARGIN change (affecting both), not a one-sided nudge.
TITLE_TOP_Y = MARGIN
AUTHOR_BOTTOM_Y = None  # computed per-call as CANVAS_H - MARGIN - text_height

# Aug 2026 rule: by default, title/subtitle/author should each SCALE TO FILL
# this width — 0.25" bleed + 0.25" visual border per side, i.e. 0.5" total
# per side, 1.0" total off the full canvas width. This is a bigger default
# than TEXT_W above (which was a conservative safe-zone width) — the new
# rule is "fill it," not "stay comfortably inside it."
#
# Aug 14 2026 fix: this was previously enforced by NOTHING — it lived only
# as this comment. bevel_text() required target_width as a plain positional
# arg with no default, and subtitle/author had no shared helper at all, so
# every per-book build script hand-rolled render_ink+apply_gold_foil for
# them and picked its own fraction of FULL_TEXT_W (or worse, an arbitrary
# pt_size with no width target at all). That's how the rule kept silently
# dropping. Fix: bevel_text() now defaults target_width to FULL_TEXT_W, and
# scaled_gold_text() below is the one function ALL THREE of title/subtitle/
# author should go through. See scaled_gold_text() docstring.
FULL_TEXT_W = CANVAS_W - int(1.0 * 300)  # = 1650px at 1950px canvas

CARD_W, CARD_H = 650, 962
CARD_QUALITY = 74
# HERO (added Aug 14 2026): the featured/banner image for a book's web
# page. Same shape as the cover (not a landscape crop -- nothing in the
# site currently crops covers to landscape, so don't invent that shape
# here), just bigger than the small nav/list CARD above. ~2x the card's
# linear size, same aspect ratio.
HERO_W, HERO_H = 1300, 1924
HERO_QUALITY = 82


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


def common_ink_bounds(ink):
    """
    Added Aug 14 2026. For layout math that needs "where does this line
    of text visually start/end" (e.g. finding the midpoint between two
    lines), ink.height (the full tight bbox) is the WRONG measurement —
    a single low-hanging descender (a 'j', a 'g' with a true descender
    in a script/serif font) or one unusually tall capital pulls the
    bbox edge out further than where the text actually reads as
    starting/ending. Most cover layout decisions should go by the
    COMMON top/bottom line that most of the glyphs actually sit on, not
    the rare outlier.

    Method: for each column of the ink's alpha channel, find that
    column's own topmost/bottommost ink pixel, then take the MODE
    across all columns — the y-position most glyphs actually share —
    rather than the min/max across the whole run.

    Returns (common_top, common_bottom) as row indices in the ink's own
    coordinate frame (0 = ink's own top edge). Use ink.height alongside
    this when you also need the true full extent (e.g. for placement
    that must not clip an actual descender).
    """
    from collections import Counter
    arr = np.asarray(ink.split()[-1])  # alpha channel
    tops, bottoms = [], []
    for col in range(arr.shape[1]):
        rows = np.where(arr[:, col] > 0)[0]
        if len(rows) == 0:
            continue
        tops.append(int(rows[0]))
        bottoms.append(int(rows[-1]))
    if not tops:
        return 0, ink.height
    common_top = Counter(tops).most_common(1)[0][0]
    common_bottom = Counter(bottoms).most_common(1)[0][0]
    return common_top, common_bottom


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
    (0.00, (42, 27, 15)),     # dark umber shadow — reintroduced into the face (sampled from Liberty)
    (0.22, (150, 80, 30)),    # copper/orange/brown zone — compressed to a single point, not a wide band
    (0.42, (232, 172, 62)),   # warm yellow-gold
    (0.50, (252, 222, 130)),  # cream highlight, shifted toward yellow rather than pale white
    (0.58, (232, 172, 62)),   # warm yellow-gold
    (0.78, (150, 80, 30)),    # copper/orange/brown zone — compressed
    (1.00, (42, 27, 15)),     # dark umber shadow
]

# PASTEL GOLD (Aug 7 2026) — a lighter variant for pastel/light-background
# covers (e.g. watercolor paintings). Same structure as STATIC_GOLD_FOIL_STOPS
# but the shadow and copper zones are raised up toward midtone brightness —
# a near-black shadow reads as a heavy, wrong-weight intrusion against a
# pale watercolor; this keeps the same gold "shape" without that mismatch.
PASTEL_GOLD_FOIL_STOPS = [
    (0.00, (130, 100, 60)),
    (0.22, (195, 150, 80)),
    (0.42, (235, 180, 90)),
    (0.50, (255, 230, 160)),
    (0.58, (235, 180, 90)),
    (0.78, (195, 150, 80)),
    (1.00, (130, 100, 60)),
]


def chisel_shade(mask_bool, bevel_px, light_dir=(-0.5, -0.55, 0.7), blur_sigma=1.6,
                  normal_blur=2.5):
    """
    Per-pixel brightness multiplier approximating a flat-faceted (chiseled,
    not rounded/inflated) bevel edge, lit from upper-left ("top lighting" —
    Regal Gold's structure corrected for light direction). Uses a distance
    transform from the letter edge: within bevel_px of the edge the facet
    tilts per the local edge direction (linear ramp = flat chisel facet,
    not a rounded/domed profile); beyond that the face is flat.

    Aug 9 2026 fix #1: the raw distance-transform field is noisy at pixel
    resolution, and np.gradient amplifies that noise most where curves
    change direction fastest (G, O, S bowls) — the normals chop instead
    of flowing smoothly, reading as a choppy/banded bevel on curved
    strokes even though straight strokes look fine. A light Gaussian blur
    on the distance field BEFORE differentiating for normals (blur_sigma)
    fixes this without rounding off the facet look on straight edges.

    Aug 9 2026 fix #2: distinct from the above, letters with competing
    equidistant edges (the medial axis inside a G's bowl, the counter of
    an O) produce a genuine seam — the normal direction flips abruptly
    right where two "nearest edge" regions meet, visible as a hard shadow
    or highlight line that cuts the letter in two (worst on G at roughly
    the 12 o'clock and 9 o'clock positions). Blurring the underlying
    distance field does NOT remove this — the ridge just gets softer,
    the direction still flips at its centerline. What removes it is
    blurring the NORMAL VECTORS themselves (nx, ny) after they're
    computed: averaging two opposing directions produces a smooth
    in-between instead of a hard flip. normal_blur=2.5 is the sweet
    spot — much higher starts to round the whole bevel toward domed.
    """
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(mask_bool)
    dist = ndimage.gaussian_filter(dist, sigma=blur_sigma)
    t = np.clip(dist / max(1, bevel_px), 0, 1)
    gy, gx = np.gradient(dist.astype(float))
    gx = np.where(t < 1, gx, 0.0)
    gy = np.where(t < 1, gy, 0.0)
    nx, ny = -gx, -gy
    if normal_blur > 0:
        nx = ndimage.gaussian_filter(nx, sigma=normal_blur)
        ny = ndimage.gaussian_filter(ny, sigma=normal_blur)
    nz = 0.35 + 0.65 * t  # tilted at the edge, flattens to fully "up" toward the interior
    norm = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2) + 1e-6
    nx, ny, nz = nx / norm, ny / norm, nz / norm
    Lx, Ly, Lz = light_dir
    Lnorm = math.sqrt(Lx ** 2 + Ly ** 2 + Lz ** 2)
    Lx, Ly, Lz = Lx / Lnorm, Ly / Lnorm, Lz / Lnorm
    shade = nx * Lx + ny * Ly + nz * Lz
    return np.clip(shade, 0.0, 1.35)


def apply_chiseled_gold(ink, stops=STATIC_GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG,
                         bevel_frac=0.09, light_dir=(-0.5, -0.55, 0.7),
                         top_light_dir=(0.0, -1.0, 0.35), top_light_boost=1.6,
                         top_highlight_color=(255, 250, 225),
                         shadow_floor=0.45, highlight_range=0.85):
    """
    DEFAULT title/author/subtitle treatment (Aug 7 2026, fourth pass).
    Three effects layered:
    1. A SMOOTH angled color gradient across the whole glyph (the "airbrushed"
       quality from the Diana reference — soft blended color, no hard bands).
    2. A chiseled emboss brightness map (chisel_shade) from a diagonal light
       — this is what makes highlight/shadow flow across letters and words
       as a continuous sweep, not per-letter.
    3. A SECOND, more directly-overhead light pass (top_light_dir) that
       ADDS a warm highlight color into top-facing facets (not multiplies —
       multiply saturates to white almost immediately on pixels the
       diagonal light already brightened, making the boost invisible;
       adding real RGB headroom is what makes "crank it up" actually show).

    shadow_floor / highlight_range (added Aug 14 2026): control the depth
    of the bevel's dark/light swing independent of everything else — the
    brightness multiplier is shadow_floor + highlight_range * shade_flow.
    Defaults (0.45, 0.85) match the original tuning. Lower shadow_floor
    = darker shadow facets; higher highlight_range = brighter highlight
    facets. Use this to punch up contrast for a word/line that's losing
    to a busy background (e.g. call with shadow_floor=0.28,
    highlight_range=1.05 rather than reaching for a different treatment
    entirely).
    """
    w, h = ink.size
    alpha = ink.split()[3]
    mask_bool = np.asarray(alpha) > 127

    grad = angled_gradient_rgb(w, h, stops, angle_deg).convert("RGB")
    grad_arr = np.asarray(grad).astype(float)

    bevel_px = max(2, round(bevel_frac * min(w, h)))
    shade_flow = chisel_shade(mask_bool, bevel_px, light_dir)
    mult = shadow_floor + highlight_range * shade_flow
    lit_arr = grad_arr * mult[:, :, None]

    shade_top = chisel_shade(mask_bool, bevel_px, top_light_dir)
    top_amount = np.clip((shade_top - 0.55) / 0.45, 0, 1) ** 1.3  # only near-top-facing facets
    boost_color = np.array(top_highlight_color, dtype=float)
    lit_arr = lit_arr + top_amount[:, :, None] * boost_color[None, None, :] * top_light_boost * 0.35

    out_arr = np.clip(lit_arr, 0, 255).astype(np.uint8)
    out = Image.fromarray(out_arr, mode="RGB").convert("RGBA")
    out.putalpha(alpha)
    return out


def cast_shadow(canvas, ink, x, y, offset=(6, 8), blur=6, opacity=110, color=(5, 3, 1)):
    """Soft shadow cast onto the artwork behind the text, separate from the
    letter's own bevel — helps text ground/pop off busy painting backgrounds."""
    w, h = ink.size
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", (w, h), (*color, opacity))
    solid.putalpha(Image.eval(ink.split()[3], lambda a: int(a * (opacity / 255))))
    shadow_layer.paste(solid, (x + offset[0], y + offset[1]), solid)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(canvas.convert("RGBA"), shadow_layer)


def build_top_aligned_ink(text, font_path, pt_size, pad=80):
    """
    DEFAULT TITLE TREATMENT (added Aug 13 2026). Renders text with every
    glyph's TOP edge aligned to the same row, letting bottoms fall where
    each glyph's natural height puts them -- tall capitals hang down
    below the shorter "faux-lowercase" forms in fonts like Cinzel that
    render lowercase as shrunk capitals. This is the INVERSE of normal
    baseline-aligned text (where bottoms share a line and capitals stand
    up taller). Use this for titles by default. Subtitles and author
    names keep normal baseline alignment via render_ink/bevel_text --
    the contrast between the two is part of the effect, not incidental.

    Returns an RGBA ink image (white-filled, alpha=glyph shape), same
    contract as render_ink, so it drops into scale_ink_to_width /
    apply_chiseled_gold / apply_gold_foil unchanged.
    """
    font = ImageFont.truetype(font_path, pt_size)
    tmp = Image.new("L", (10, 10), 0)
    d = ImageDraw.Draw(tmp)

    advances = [0.0]
    for i in range(1, len(text) + 1):
        advances.append(d.textlength(text[:i], font=font))

    char_boxes = [None if ch == ' ' else font.getbbox(ch) for ch in text]
    tops = [b[1] for b in char_boxes if b is not None]
    bottoms = [b[3] for b in char_boxes if b is not None]
    global_top, global_bottom = min(tops), max(bottoms)
    total_h = global_bottom - global_top
    total_w = advances[-1]

    work_w, work_h = int(total_w) + pad * 2, int(total_h) + pad * 2
    canvas = Image.new("L", (work_w, work_h), 0)
    dc = ImageDraw.Draw(canvas)
    for i, ch in enumerate(text):
        if char_boxes[i] is None:
            continue
        x = pad + advances[i]
        y = pad - char_boxes[i][1]  # every glyph's own top lands at `pad`
        dc.text((x, y), ch, font=font, fill=255)

    arr = np.array(canvas)
    rows, cols = np.any(arr, axis=1), np.any(arr, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    canvas = canvas.crop((cmin, rmin, cmax + 1, rmax + 1))

    white = Image.new("L", canvas.size, 255)
    ink_rgba = Image.merge("RGBA", (white, white, white, canvas))
    return ink_rgba, canvas.width, canvas.height


def bevel_text(canvas, text, font_path, pt_size, center_x, top_y,
                target_width=FULL_TEXT_W, foil_stops=STATIC_GOLD_FOIL_STOPS,
                angle_deg=FOIL_ANGLE_DEG, seed=FOIL_SEED):
    """
    DEFAULT title/author/subtitle treatment (Aug 7 2026, second pass):
    heavier weight font + chiseled emboss bevel (apply_chiseled_gold) +
    a soft cast shadow onto the artwork behind the letters for grounding.
    Use a BOLD font_path — the bevel reads as mush on a thin weight.

    target_width now DEFAULTS to FULL_TEXT_W (Aug 14 2026 fix) instead of
    requiring the caller to always supply it. Prefer scaled_gold_text()
    below for subtitle/author, which shares this same default and also
    covers the flat (non-chiseled) treatment.
    """
    ink, w, h = render_ink(text, font_path, pt_size)
    ink = scale_ink_to_width(ink, target_width)

    x = round(center_x - ink.width / 2)
    canvas = cast_shadow(canvas, ink, x, top_y)

    face = apply_chiseled_gold(ink, stops=foil_stops, angle_deg=angle_deg)
    canvas.paste(face, (x, top_y), face)
    return canvas, ink.height


# HIGH CONTRAST GOLD FINISH (added Aug 14 2026): apply_chiseled_gold's
# shadow_floor/highlight_range pushed further apart than the defaults,
# so the bevel manufactures its own light/dark separation instead of
# relying on the artwork behind it for contrast.
#
# WHEN TO USE: wherever the painting directly behind the text sits in
# the MID tonal range -- not clearly dark, not clearly light, no strong
# value swing of its own. Normal pastel/chiseled gold reads fine over
# a strong dark (navy band, shadowed painting area) or a strong light
# (bright sky, white ground) because the painting itself is already
# doing the contrast work. It's the mid-tone regions -- muted golds,
# dusty pinks, mid-value textures close to the gold's own hue and
# value -- where flat/normal-chisel gold has nothing to carve itself
# out against and starts to disappear (this is what happened to
# "feminine" sitting on the gold orb cluster in Restoring/Forgotten
# Sacred Communion -- see that build for the reference case). Reach
# for this per WORD or per PHRASE where that specific patch of art is
# mid-toned, not as a whole-cover default.
HIGH_CONTRAST_SHADOW_FLOOR = 0.26
HIGH_CONTRAST_HIGHLIGHT_RANGE = 1.10
HIGH_CONTRAST_TOP_LIGHT_BOOST = 2.3


def apply_high_contrast_gold(ink, stops=STATIC_GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG):
    """Convenience wrapper: apply_chiseled_gold tuned to the High Contrast
    Gold finish. See the constants/comment above for when to reach for
    this instead of apply_chiseled_gold's defaults."""
    return apply_chiseled_gold(
        ink, stops=stops, angle_deg=angle_deg,
        shadow_floor=HIGH_CONTRAST_SHADOW_FLOOR,
        highlight_range=HIGH_CONTRAST_HIGHLIGHT_RANGE,
        top_light_boost=HIGH_CONTRAST_TOP_LIGHT_BOOST,
    )


def scaled_gold_text(canvas, text, font_path, pt_size, center_x, top_y,
                      target_width=FULL_TEXT_W, treatment="chiseled",
                      foil_stops=STATIC_GOLD_FOIL_STOPS, angle_deg=FOIL_ANGLE_DEG,
                      cast_shadow_on=True):
    """
    UNIFIED title/subtitle/author placement (added Aug 14 2026). This is
    the one function all three text elements should go through — do not
    reach for render_ink + apply_gold_foil/apply_chiseled_gold directly
    for subtitle or author "since they're smaller/different." That
    per-element hand-rolling is exactly how the FULL_TEXT_W width rule
    kept silently dropping: target_width defaults here to FULL_TEXT_W,
    so title, subtitle, and author are the same width — background
    width minus 0.25" bleed minus 0.25" visual exclusion — unless a
    build script deliberately overrides it, which then shows up as an
    explicit, visible choice at the call site instead of a silent one.

    GOSPEL RULE (confirmed Aug 16 2026, after a same-session violation):
    every per-book build script starts ALL THREE elements — title,
    subtitle, author — at target_width=FULL_TEXT_W. This is not a
    fallback for when nothing else is specified; it is the mandatory
    starting point. A narrower width is something a book can choose to
    do deliberately afterward (e.g. a subtitle style that reads better
    shorter), but it is never the default a build script reaches for
    out of habit or to "make it look nicer" on a first pass. If a
    build script passes any target_width other than FULL_TEXT_W (or
    omits the parameter, which is the same thing), that choice needs a
    stated reason in a comment at the call site.

    treatment:
      "chiseled" (default) — bevel emboss via apply_chiseled_gold, same
      as the title. Use for author, or a subtitle that should carry the
      same weight as the title.
      "flat" — apply_gold_foil, smoother/no bevel facets. Use when a
      subtitle should read quieter than the title next to it.
      "high_contrast" (added Aug 14 2026) — apply_high_contrast_gold;
      deeper shadows + brighter highlights, self-supplied contrast
      rather than borrowed from the artwork. Use per-word/per-phrase
      where the art directly behind that text is mid-toned. See the
      HIGH_CONTRAST_SHADOW_FLOOR comment above for the full rule. NOTE:
      this function applies one treatment to the WHOLE string — if only
      part of a line needs it (the common case), render/scale/composite
      that word separately with apply_high_contrast_gold instead of
      calling this with the whole line.

    Returns (canvas, ink.height) same contract as bevel_text.
    """
    ink, w, h = render_ink(text, font_path, pt_size)
    ink = scale_ink_to_width(ink, target_width)
    x = round(center_x - ink.width / 2)

    if cast_shadow_on:
        canvas = cast_shadow(canvas, ink, x, top_y)

    if treatment == "chiseled":
        face = apply_chiseled_gold(ink, stops=foil_stops, angle_deg=angle_deg)
    elif treatment == "high_contrast":
        face = apply_high_contrast_gold(ink, stops=foil_stops, angle_deg=angle_deg)
    else:
        face = apply_gold_foil(ink, stops=foil_stops, angle_deg=angle_deg)

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


def export_hero(full_cover, out_path, quality=HERO_QUALITY):
    """
    Added Aug 14 2026. 1300x1924 web hero/banner image -- same shape as
    the cover, ~2x the CARD's linear size. For the featured image on a
    book's own page, as distinct from the small CARD used in nav/list
    contexts.
    """
    hero = full_cover.convert("RGB").resize((HERO_W, HERO_H), Image.LANCZOS)
    hero.save(out_path, "JPEG", quality=quality)
    return out_path


def export_approved_web_assets(full_cover, book_slug, out_dir="/home/claude"):
    """
    Added Aug 14 2026 -- APPROVAL-STAGE ONLY. Call this once, when Michael
    has approved a cover version, never during draft iteration (drafts go
    through save_cover_version with make_card=False, full-res only).

    Writes card + hero to FIXED, UNVERSIONED filenames --
    {book_slug}_card.jpeg and {book_slug}_hero.jpeg -- unlike the
    versioned masters in covers/[slug]/ (which intentionally keep history
    per Charter 1D), the web-facing card and hero are meant to always be
    "whatever the current approved cover is." When pushing to GitHub,
    push these to images/cover-{book_slug}-card.jpeg and
    images/cover-{book_slug}-hero.jpeg, OVERWRITING whatever was there
    (fetch a fresh SHA first, per the standard GitHub PUT pattern) --
    do not create a new versioned filename alongside the old one.

    Returns {"card_path": str, "hero_path": str}.
    """
    card_path = f"{out_dir}/{book_slug}_card.jpeg"
    hero_path = f"{out_dir}/{book_slug}_hero.jpeg"
    export_card(full_cover, card_path)
    export_hero(full_cover, hero_path)
    return {"card_path": card_path, "hero_path": hero_path}


def save_cover_version(canvas, book_slug, existing_versions, out_dir="/home/claude",
                        quality=92, make_card=False):
    """
    Section 0 DISPLAY GATE (added Aug 13 2026): every cover build saves
    through this function, never through ad-hoc filenames. It auto-
    increments the version number and returns paths in a fixed shape so
    the calling session has no excuse to skip displaying the result.

    make_card (Aug 14 2026 fix, default False): the 650x962 web card is a
    FINAL-APPROVAL-STAGE artifact, not a draft-iteration one — Michael
    reviews full covers during iteration and only needs the card once a
    version is actually approved for the site. This used to build the
    card unconditionally on every save, producing a redundant deliverable
    on every single draft round. Pass make_card=True explicitly once a
    version is approved and you're producing the final deliverable pair.

    existing_versions: list of ints already used for this book_slug (the
    caller gets these by listing the relevant GitHub covers/ folder before
    calling — this function does no network I/O itself, to keep it a pure
    PIL utility).

    Returns a dict: {"version": int, "full_path": str, "card_path": str}.
    card_path is None unless make_card=True.
    MANDATORY NEXT STEP (not automatable from inside this function, since
    a Python script cannot invoke Claude's own view tool): the calling
    session must call view() on full_path immediately after this returns,
    before doing anything else with the cover — before export_card, before
    any GitHub push, before presenting anything to Michael. See
    COVER_PRODUCTION_STANDARD.txt Section 0 for the full rule.
    """
    version = (max(existing_versions) + 1) if existing_versions else 1
    full_path = f"{out_dir}/{book_slug}_cover_v{version}_full.jpg"
    canvas.convert("RGB").save(full_path, "JPEG", quality=quality)
    card_path = None
    if make_card:
        card_path = f"{out_dir}/{book_slug}_cover_v{version}_card.jpg"
        export_card(canvas, card_path)
    return {"version": version, "full_path": full_path, "card_path": card_path}
