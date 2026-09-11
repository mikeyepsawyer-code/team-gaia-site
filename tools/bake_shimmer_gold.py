import sys
sys.path.insert(0, '/home/claude/repo_tools')
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage
import math

FONT = "/home/claude/fonts/parisienne-400.ttf"

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

# gold stops actually used for the site's animated shimmer (ported gold, not the STFD-specific palette)
GOLD_FOIL_STOPS = [
    (0.00, (74, 36, 24)), (0.06, (122, 74, 30)), (0.18, (230, 182, 76)),
    (0.24, (255, 242, 192)), (0.28, (242, 161, 60)), (0.36, (201, 148, 53)),
    (0.42, (122, 74, 30)), (0.48, (230, 182, 76)), (0.52, (255, 242, 192)),
    (0.56, (242, 161, 60)), (0.62, (201, 148, 53)), (0.68, (110, 66, 24)),
    (0.76, (201, 148, 53)), (0.80, (255, 242, 192)), (0.84, (242, 161, 60)),
    (0.94, (110, 66, 24)), (1.00, (74, 36, 24)),
]

def map_shade_to_color(shade, stops):
    v = np.clip(shade / 1.35, 0, 1)
    out = np.zeros(v.shape + (3,), dtype=np.float32)
    for i in range(len(stops)-1):
        t0, c0 = stops[i]
        t1, c1 = stops[i+1]
        mask = (v >= t0) & (v <= t1)
        local_t = np.clip((v - t0) / max(1e-6, (t1-t0)), 0, 1)
        for ch in range(3):
            out[..., ch] = np.where(mask, c0[ch] + (c1[ch]-c0[ch])*local_t, out[..., ch])
    return out

def render_frame(mask_img, nx, ny, nz, angle_deg, stops):
    rad = math.radians(angle_deg)
    light_dir = (math.cos(rad)*0.75, math.sin(rad)*0.75, 0.65)
    shade = shade_from_light(nx, ny, nz, light_dir)
    color = map_shade_to_color(shade, stops)
    alpha = np.asarray(mask_img).astype(np.uint8)
    out = np.zeros((mask_img.height, mask_img.width, 4), dtype=np.uint8)
    out[..., :3] = np.clip(color, 0, 255).astype(np.uint8)
    out[..., 3] = alpha
    return Image.fromarray(out, "RGBA")

mask_img = render_letter_mask("Gaia", 500)
mask_bool = np.asarray(mask_img) > 127
bevel_px = max(2, round(0.09 * min(mask_img.size)))
nx, ny, nz = precompute_normals(mask_bool, bevel_px)

frames = []
N = 24
for i in range(N):
    angle = 180 + 90 * math.sin(2*math.pi*i/N)
    frame = render_frame(mask_img, nx, ny, nz, angle, GOLD_FOIL_STOPS)
    bg = Image.new("RGB", frame.size, (10, 12, 18))
    bg.paste(frame, (0,0), frame)
    frames.append(bg)

frames[0].save('/home/claude/shimmer_proto/gaia_shimmer.gif', save_all=True,
               append_images=frames[1:], duration=90, loop=0)
frames[N//4].save('/home/claude/shimmer_proto/gaia_still.png')
print("done", len(frames), "frames, size", mask_img.size)
