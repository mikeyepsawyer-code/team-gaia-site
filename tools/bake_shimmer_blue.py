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

FONT_PATH = '/home/claude/cinzel-700.ttf'

# ---- Blue palette (sampled from the Ameris Gin reference video) ----
SHADOW_1 = (10, 14, 40)        # deepest shadow, near-black navy
SHADOW_2 = (20, 28, 70)
SHADOW_3 = (30, 45, 110)
BASE_BLUE = (42, 90, 220)      # mid-tone body blue
CERULEAN = (60, 160, 220)      # high-midtone, sampled from the reference video (hue ~200)
RIM_1 = (70, 130, 245)
RIM_2 = (100, 195, 245)        # shifted more cyan, less pale
RIM_3 = (110, 220, 245)        # was near-white, now bright cerulean
HOTSPOT = (150, 235, 255)      # was pure white, now cyan-tinted highlight


def build_letter(text, font_size, letter_spacing=0):
    """Render the text mask + layered bevel copies once. Returns a dict
    of precomputed data reused by render_frame() for every frame, so the
    expensive text rasterization only happens once per bake."""
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

    return {'mask': mask, 'size': (canvas_w, canvas_h)}


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
    mask = pre['mask']
    w, h = pre['size']
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    bevel_offsets = [
        (4, 4, SHADOW_1, 0.9), (3, 3, SHADOW_2, 0.75), (2, 2, SHADOW_3, 0.55),
        (-1, -1, RIM_1, 0.5), (-2, -2, RIM_2, 0.7), (-3, -3, RIM_3, 0.85),
    ]
    for dx, dy, color, op in bevel_offsets:
        layer = Image.new('RGBA', (w, h), color + (0,))
        a = mask.point(lambda v: int(v * op))
        layer.putalpha(a)
        out.alpha_composite(layer, (dx, dy))

    # base face
    face = Image.new('RGBA', (w, h), BASE_BLUE + (0,))
    face.putalpha(mask)
    out.alpha_composite(face)

    # cerulean high-midtone -- a soft inner layer between the base body
    # color and the rim highlights, sampled from the reference video
    cerulean_layer = Image.new('RGBA', (w, h), CERULEAN + (0,))
    cerulean_a = mask.point(lambda v: int(v * 0.55))
    cerulean_layer.putalpha(cerulean_a)
    out.alpha_composite(cerulean_layer, (-1, -1))

    # animated highlight sweep, masked to the letterforms, screen-blended
    sweep_l = _diagonal_sweep((w, h), phase)
    sweep_rgba = Image.new('RGBA', (w, h), HOTSPOT + (0,))
    sweep_alpha = Image.composite(sweep_l, Image.new('L', (w, h), 0), mask)
    sweep_rgba.putalpha(sweep_alpha)
    out.alpha_composite(sweep_rgba)

    # soft glow pass
    glow = out.filter(ImageFilter.GaussianBlur(3))
    combined = Image.alpha_composite(glow, out)
    return combined


if __name__ == '__main__':
    pre = build_letter('TEST', 120)
    f = render_frame(pre, 0.5)
    f.save('/home/claude/shimmer_test_frame.png')
    print('rendered', f.size)
