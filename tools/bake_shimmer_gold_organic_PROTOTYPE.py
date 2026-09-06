import sys
sys.path.insert(0, '/home/claude/repo/tools')
from cover_build import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage
import math

FONT = "/home/claude/fonts/cinzel-700.ttf"

def render_letter_mask(text, pt, pad_frac=0.5):
    font = ImageFont.truetype(FONT, pt)
    tmp = Image.new("L", (10,10), 0); d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0,0), text, font=font)
    pad = round(pt*pad_frac)
    w = (bbox[2]-bbox[0]) + pad*2
    h = (bbox[3]-bbox[1]) + pad*2
    canvas = Image.new("L", (w,h), 0)
    dc = ImageDraw.Draw(canvas)
    dc.text((pad-bbox[0], pad-bbox[1]), text, font=font, fill=255)
    return canvas

def precompute_normals(mask_bool, bevel_px, blur_sigma=1.6, normal_blur=2.5):
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
    nz = 0.35 + 0.65 * t
    norm = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-6
    return nx/norm, ny/norm, nz/norm

def shade_from_light(nx, ny, nz, light_dir):
    Lx, Ly, Lz = light_dir
    Ln = math.sqrt(Lx**2+Ly**2+Lz**2)
    Lx, Ly, Lz = Lx/Ln, Ly/Ln, Lz/Ln
    shade = nx*Lx + ny*Ly + nz*Lz
    return np.clip(shade, 0.0, 1.35)

# ---- 3-tier gradient stops (shade value -> color), low to high ----
BAND_STOPS = [
    (0.00, (60, 38, 24)),     # chocolate (band 3 lowlight, deepest shadow)
    (0.28, (140, 74, 46)),    # burnt sienna (band 3 highlight / band 2 lowlight, shared bridge)
    (0.55, (230, 160, 90)),   # soft orange (band 2 highlight)
    (0.80, (210, 225, 175)),  # light green (band 1 lowlight, STFD water)
    (1.00, (255, 225, 140)),  # butter yellow (band 1 highlight, brightest)
]

def map_shade_to_color(shade):
    # shade in [0, 1.35] -> normalize to [0,1] for the gradient lookup
    v = np.clip(shade / 1.35, 0, 1)
    out = np.zeros(v.shape + (3,), dtype=np.float32)
    for i in range(len(BAND_STOPS)-1):
        t0, c0 = BAND_STOPS[i]
        t1, c1 = BAND_STOPS[i+1]
        mask = (v >= t0) & (v <= t1)
        local_t = np.clip((v - t0) / max(1e-6, (t1-t0)), 0, 1)
        for ch in range(3):
            out[..., ch] = np.where(mask, c0[ch] + (c1[ch]-c0[ch])*local_t, out[..., ch])
    return out

def render_frame(mask_img, nx, ny, nz, angle_deg):
    rad = math.radians(angle_deg)
    light_dir = (math.cos(rad)*0.75, math.sin(rad)*0.75, 0.65)
    shade = shade_from_light(nx, ny, nz, light_dir)
    color = map_shade_to_color(shade)
    alpha = np.asarray(mask_img).astype(np.uint8)
    out = np.zeros((mask_img.height, mask_img.width, 4), dtype=np.uint8)
    out[..., :3] = np.clip(color, 0, 255).astype(np.uint8)
    out[..., 3] = alpha
    return Image.fromarray(out, "RGBA")

# ---- Build test letters "We" ----
mask_img = render_letter_mask("We", 500)
mask_bool = np.asarray(mask_img) > 127
bevel_px = max(2, round(0.09 * min(mask_img.size)))
nx, ny, nz = precompute_normals(mask_bool, bevel_px)

frames = []
N = 16
for i in range(N):
    angle = 180 + 90 * math.sin(2*math.pi*i/N)  # sweep back and forth
    frame = render_frame(mask_img, nx, ny, nz, angle)
    bg = Image.new("RGB", frame.size, (25, 35, 55))
    bg.paste(frame, (0,0), frame)
    frames.append(bg)

frames[0].save('/home/claude/shimmer_proto/preview.gif', save_all=True, append_images=frames[1:],
               duration=120, loop=0)
frames[N//4].save('/home/claude/shimmer_proto/still1.png')
frames[N//2].save('/home/claude/shimmer_proto/still2.png')
print("done", len(frames), "frames")
