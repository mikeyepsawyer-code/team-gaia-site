"""
Shimmer video baker -- bakes an animated metallic-shimmer text treatment
into an MP4 loop, frame by frame, instead of relying on live CSS.

Built for the Team Gaia site after live CSS shimmer produced a GPU
texture-wrap seam on Samsung Internet that could not be fixed from CSS.
Baking to video sidesteps that entirely -- it's just a <video autoplay
loop muted playsinline> tag on the front end.

Spec (recovered from the gold-shimmer session, adapted to a cool blue
palette per the Ameris Gin reference video):
  - Dimensional bevel: multiple offset copies behind the face --
    shadow-toned copies (dark navy) offset down-right, highlight-toned
    copies (bright blue) offset up-left, mimicking a beveled metal edge.
  - Three narrow highlight bands sweep across the text at a 25-degree
    angle.
  - Motion is back-and-forth (cosine-eased), not one-directional --
    one-directional seamless looping is what caused the GPU seam.
  - ~6 second loop period.

FONT_PATH is a module-level variable so a calling script can monkey-patch
it before calling build_letter(), same convention as bake_shimmer4.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import numpy as np

FONT_PATH = '/home/claude/cinzel-700.ttf'

# ---- Three variants, mirroring the gold shimmer/cover system ----
# LIGHT: for dark backgrounds -- lighter overall, highlight-forward.
# DARK:  for light backgrounds -- deep navy-forward, less white presence.
# HIGH_CONTRAST: for midtone backgrounds -- manufactures its own strong
#   separation regardless of what's behind it (pushed shadow/highlight
#   further apart), same purpose as HIGH_CONTRAST_SHADOW_FLOOR in the
#   gold cover tool.
# All three keep DISTINCT dapple patches (near-white vs. saturated
# sky-blue) rather than a smooth blend between them -- low blur radius
# + a steep contrast curve on the noise field, not the wide gaussian
# blur used before, which was smearing the two colors into a
# desaturated intermediate that read as neither.
VARIANTS = {
    'light': {
        'SHADOW_1': (25, 40, 110), 'SHADOW_2': (35, 55, 145), 'SHADOW_3': (48, 75, 180),
        'BASE_BLUE': (70, 115, 235), 'RIM_1': (90, 140, 245),
        'DAPPLE_WHITE': (245, 246, 244), 'DAPPLE_SKY': (90, 190, 255),
        'blur_frac': 0.028, 'contrast_pow': 3.5, 'sky_bias': 1.0,
    },
    'dark': {
        'SHADOW_1': (4, 8, 30), 'SHADOW_2': (7, 13, 48), 'SHADOW_3': (11, 20, 72),
        'BASE_BLUE': (24, 42, 150), 'RIM_1': (34, 58, 175),
        'DAPPLE_WHITE': (210, 215, 220), 'DAPPLE_SKY': (40, 110, 210),
        'blur_frac': 0.028, 'contrast_pow': 3.5, 'sky_bias': 1.35,
    },
    'high_contrast': {
        'SHADOW_1': (2, 4, 18), 'SHADOW_2': (5, 9, 35), 'SHADOW_3': (10, 18, 65),
        'BASE_BLUE': (35, 60, 210), 'RIM_1': (55, 95, 240),
        'DAPPLE_WHITE': (255, 255, 253), 'DAPPLE_SKY': (50, 165, 255),
        'blur_frac': 0.016, 'contrast_pow': 5.0, 'sky_bias': 1.0,
    },
}


def build_letter(text, font_size, letter_spacing=0, variant='light'):
    """Render the text mask + layered bevel copies once. Returns a dict
    of precomputed data reused by render_frame() for every frame, so the
    expensive text rasterization only happens once per bake."""
    cfg = VARIANTS[variant]
    font = ImageFont.truetype(FONT_PATH, font_size)

    # measure text with letter-spacing
    if letter_spacing:
        widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
        total_w = sum(widths) + letter_spacing * (len(text) - 1)
    else:
        bbox = font.getbbox(text)
        total_w = bbox[2] - bbox[0]

    bbox_full = font.getbbox(text)
    asc_desc = bbox_full[3] - bbox_full[1]
    pad = font_size // 2  # room for bevel offsets + blur
    canvas_w = int(total_w) + pad * 2
    canvas_h = int(asc_desc) + pad * 2

    mask = Image.new('L', (canvas_w, canvas_h), 0)
    md = ImageDraw.Draw(mask)
    if letter_spacing:
        x = pad
        for ch, w_ in zip(text, widths):
            md.text((x, pad - bbox_full[1]), ch, font=font, fill=255)
            x += w_ + letter_spacing
    else:
        md.text((pad, pad - bbox_full[1]), text, font=font, fill=255)

    # Precompute a static dappled texture -- DISTINCT patches, not a
    # smooth blend: small blur radius (just enough to avoid raw single-
    # pixel noise) then a steep contrast curve pushes each patch toward
    # one pole or the other, so sky-blue and white read as separate
    # facets catching light differently, matching the reference's
    # faceted-foil look rather than a gradient.
    rng = np.random.default_rng(42)
    noise = rng.random((canvas_h, canvas_w)).astype(np.float32)
    noise_img = Image.fromarray((noise * 255).astype(np.uint8), 'L')
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(font_size * cfg['blur_frac']))
    arr = np.array(noise_img, dtype=np.float32) / 255.0
    arr = np.clip((arr - arr.min()) / max(1e-5, (arr.max() - arr.min())), 0, 1)
    # steep S-curve around 0.5 to push values toward the extremes (distinct
    # patches) instead of lingering in a blended middle
    arr = 0.5 + 0.5 * np.sign(arr - 0.5) * np.abs(2 * arr - 1) ** (1 / cfg['contrast_pow'])
    dapple_mix = np.clip(arr ** cfg['sky_bias'], 0, 1)

    return {'mask': mask, 'size': (canvas_w, canvas_h), 'dapple_mix': dapple_mix, 'variant': variant}


def _diagonal_sweep(size, phase, angle_deg=25, band_count=3):
    """Build the moving highlight-band gradient layer for one frame.
    phase in [0,1], cosine-eased back-and-forth handled by caller."""
    w, h = size
    diag = int(math.hypot(w, h)) + 40
    grad = Image.new('L', (diag, diag), 0)
    gd = ImageDraw.Draw(grad)

    band_w = diag // 7
    spacing = diag // band_count
    offset = int(phase * diag * 1.6) - diag // 3

    for i in range(-1, band_count + 2):
        center = i * spacing + offset
        for dx in range(-band_w, band_w):
            dist = abs(dx)
            if dist > band_w:
                continue
            alpha = int(255 * max(0, 1 - (dist / band_w) ** 1.6))
            x = center + dx
            if 0 <= x < diag:
                gd.line([(x, 0), (x, diag)], fill=alpha)

    grad = grad.rotate(angle_deg, resample=Image.BICUBIC, expand=False)
    left = (grad.width - w) // 2
    top = (grad.height - h) // 2
    return grad.crop((left, top, left + w, top + h))


def render_frame(pre, phase):
    """Render one animation frame. phase in [0,1] (already cosine-eased
    by the caller for back-and-forth motion)."""
    cfg = VARIANTS[pre['variant']]
    mask = pre['mask']
    w, h = pre['size']
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    bevel_offsets = [
        (4, 4, cfg['SHADOW_1'], 0.9), (3, 3, cfg['SHADOW_2'], 0.75), (2, 2, cfg['SHADOW_3'], 0.55),
        (-1, -1, cfg['RIM_1'], 0.55),
    ]
    for dx, dy, color, op in bevel_offsets:
        layer = Image.new('RGBA', (w, h), color + (0,))
        a = mask.point(lambda v: int(v * op))
        layer.putalpha(a)
        out.alpha_composite(layer, (dx, dy))

    # base face -- the dominant midtone royal blue, kept as the bulk of
    # the letterform's own color (this stays a "midtone blue" overall)
    face = Image.new('RGBA', (w, h), cfg['BASE_BLUE'] + (0,))
    face.putalpha(mask)
    out.alpha_composite(face)

    # dappled highlight: build an RGB image by mixing DAPPLE_WHITE and
    # DAPPLE_SKY per-pixel using the precomputed static noise texture,
    # then reveal it only within the moving sweep band -- so the sparkle
    # positions are fixed (like real foil grain) but only shimmer as the
    # light passes over them, same as the reference video.
    mix = pre['dapple_mix']
    dapple_rgb = np.empty((h, w, 3), dtype=np.uint8)
    dw, dsky = cfg['DAPPLE_WHITE'], cfg['DAPPLE_SKY']
    for c in range(3):
        dapple_rgb[:, :, c] = (dsky[c] + (dw[c] - dsky[c]) * mix).astype(np.uint8)
    dapple_img = Image.fromarray(dapple_rgb, 'RGB')

    sweep_l = _diagonal_sweep((w, h), phase)
    sweep_alpha = Image.composite(sweep_l, Image.new('L', (w, h), 0), mask)
    dapple_rgba = dapple_img.convert('RGBA')
    dapple_rgba.putalpha(sweep_alpha)
    out.alpha_composite(dapple_rgba)

    # soft glow pass -- premultiply alpha before blurring, otherwise PIL
    # blends in the arbitrary RGB sitting under semi-transparent/fully
    # transparent pixels, which desaturates edges toward a muddy grey
    # (this was the source of the "dusty mauve" cast in highlight areas)
    arr = np.array(out).astype(np.float32)
    a = arr[:, :, 3:4] / 255.0
    premult = arr.copy()
    premult[:, :, :3] *= a
    premult_img = Image.fromarray(premult.astype(np.uint8), 'RGBA')
    blurred = premult_img.filter(ImageFilter.GaussianBlur(3))
    barr = np.array(blurred).astype(np.float32)
    ba = barr[:, :, 3:4]
    ba_safe = np.where(ba < 1, 1, ba)
    barr[:, :, :3] = barr[:, :, :3] * 255.0 / ba_safe
    glow = Image.fromarray(np.clip(barr, 0, 255).astype(np.uint8), 'RGBA')

    combined = Image.alpha_composite(glow, out)
    return combined


if __name__ == '__main__':
    pre = build_letter('TEST', 120)
    f = render_frame(pre, 0.5)
    f.save('/home/claude/shimmer_test_frame.png')
    print('rendered', f.size)
