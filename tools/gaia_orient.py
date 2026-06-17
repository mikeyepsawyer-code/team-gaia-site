#!/usr/bin/env python3
"""
GAIA ORIENT  —  Step 1 of all Gaia photo work.
=================================================
PHILOSOPHY (this is not a technical step, it is a way of seeing):
  See her as a FIGURE, not a landscape. She is Gaia more than she is rock.
  Step 1 of making anything Gaia is to stand her up.

THE RULE (the rotation falls out of the seeing):
  - The LONG dimension is almost always the VERTICAL axis. Never trim. Only rotate.
  - Captured LANDSCAPE  -> rotate 90 (whichever direction) so GAIA is on the LEFT,
    sky on the RIGHT. She stands, she does not lie down.
  - Captured PORTRAIT (you framed it tall on purpose) -> stays UPRIGHT,
    sky/sun ABOVE, land below. You already saw her as a figure.

Detection: brightness + blue-ness locates the sky. We test the allowed
rotations for each case and pick the one that places sky correctly.

USAGE:
  python3 gaia_orient.py INPUT_DIR OUTPUT_DIR
  (or import orient_gaia(pil_image) -> pil_image)
"""
from PIL import Image, ImageOps
import numpy as np, os, sys, glob

def _sky_map(im):
    a = np.asarray(im.convert('RGB'), dtype=float)
    brightness = a.mean(axis=2)
    blueness   = a[:, :, 2] - a[:, :, 0]*0.5 - a[:, :, 1]*0.5
    return brightness + blueness*1.5

def _region(s, where):
    H, W = s.shape
    return {
        'top':    s[:H//2, :].mean(),
        'bottom': s[H//2:, :].mean(),
        'left':   s[:, :W//2].mean(),
        'right':  s[:, W//2:].mean(),
    }[where]

def orient_gaia(im):
    """Stand Gaia up. Returns a portrait PIL image, sky placed by the rule."""
    im = ImageOps.exif_transpose(im)          # bake EXIF -> pixels as captured
    w, h = im.size
    captured_landscape = w >= h

    if captured_landscape:
        # She must stand: rotate 90 whichever way puts SKY on the RIGHT.
        cands = [im.rotate(90, expand=True), im.rotate(-90, expand=True)]
        best = max(cands, key=lambda c: _region(_sky_map(c), 'right')
                                       - _region(_sky_map(c), 'left'))
        return best, 'landscape -> stood up, sky-right'
    else:
        # Framed tall on purpose: stay upright, SKY on TOP (allow 180 flip only).
        cands = [im, im.rotate(180, expand=True)]
        best = max(cands, key=lambda c: _region(_sky_map(c), 'top')
                                       - _region(_sky_map(c), 'bottom'))
        return best, 'portrait -> upright, sky-top'

def main(indir, outdir):
    os.makedirs(outdir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(indir, '*.jpg')) +
                   glob.glob(os.path.join(indir, '*.jpeg')) +
                   glob.glob(os.path.join(indir, '*.png')))
    for f in files:
        o, rule = orient_gaia(Image.open(f))
        name = os.path.basename(f)
        o.convert('RGB').save(os.path.join(outdir, name), 'JPEG', quality=92)
        print(f'{name:24s} {o.size}  {rule}')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: python3 gaia_orient.py INPUT_DIR OUTPUT_DIR'); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
