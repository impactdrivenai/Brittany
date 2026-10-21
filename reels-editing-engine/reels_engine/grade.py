"""Cinematic colour grade: a generated 3D LUT (.cube) per look, applied with ffmpeg lut3d, then fine grain and a
soft vignette on footage only (overlays, captions and screenshots are composited after, so they stay true colour)."""
import math
import numpy as np
from pathlib import Path

LOOKS = {
    # contrast, lift (shadow offset), gain, warm_hi, cool_sh, desat, halation-ish softness unused
    "cinematic":  {"contrast": 1.16, "lift": -0.035, "gain": 1.00, "warm_hi": 0.060, "cool_sh": 0.050, "desat": 0.10},
    "warm_moody": {"contrast": 1.09, "lift": -0.018, "gain": 1.00, "warm_hi": 0.050, "cool_sh": 0.030, "desat": 0.07},
    "clean":      {"contrast": 1.04, "lift":  0.000, "gain": 1.01, "warm_hi": 0.020, "cool_sh": 0.010, "desat": 0.03},
    "faded":      {"contrast": 0.94, "lift":  0.060, "gain": 0.98, "warm_hi": 0.050, "cool_sh": 0.000, "desat": 0.15},
    "bright":     {"contrast": 1.05, "lift":  0.015, "gain": 1.03, "warm_hi": 0.010, "cool_sh": 0.000, "desat": -0.05},
    "none":       None,
}


def _s_curve(x, contrast):
    # smooth S around mid grey; contrast 1.0 = identity
    k = (contrast - 1.0) * 3.0
    if abs(k) < 1e-6:
        return x
    y = x - 0.5
    return np.clip(0.5 + y * (1 + k) / (1 + k * np.abs(y) * 2), 0, 1)


def make_lut(look, out_path, size=33):
    p = LOOKS.get(look)
    out_path = Path(out_path)
    if p is None:
        return None
    g = np.linspace(0, 1, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # cube order: R fastest
    rgb = np.stack([r, gg, b], axis=-1).reshape(-1, 3)
    # lift / gain
    rgb = np.clip(rgb * p["gain"] + p["lift"] * (1 - rgb), 0, 1)
    # contrast S-curve on each channel
    rgb = _s_curve(rgb, p["contrast"])
    # luma
    luma = (0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2])[:, None]
    # warm highlights (push red/yellow where it is bright), cool shadows (push blue/teal where dark)
    hi = np.clip((luma - 0.45) / 0.55, 0, 1)
    sh = np.clip((0.45 - luma) / 0.45, 0, 1)
    rgb = rgb + hi * p["warm_hi"] * np.array([1.0, 0.35, -0.9]) + sh * p["cool_sh"] * np.array([-0.6, 0.25, 1.0])
    # highlight roll-off: compress the top 10 percent so nothing clips hard
    rgb = np.where(rgb > 0.9, 0.9 + (rgb - 0.9) * 0.6, rgb)
    rgb = np.clip(rgb, 0, 1)
    # desaturate with skin protection (skin hue is warm, mid luma): protect pixels where r > g > b and mid luma
    luma = (0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2])[:, None]
    skin = ((rgb[:, 0] > rgb[:, 1]) & (rgb[:, 1] > rgb[:, 2]) & (luma[:, 0] > 0.25) & (luma[:, 0] < 0.85)).astype(float)[:, None]
    amount = p["desat"] * (1 - 0.7 * skin)
    rgb = np.clip(luma + (rgb - luma) * (1 - amount), 0, 1)
    with open(out_path, "w") as f:
        f.write(f"TITLE \"reels engine {look}\"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n")
        np.savetxt(f, rgb, fmt="%.6f")
    return out_path


def esc(path):
    """Escape a path for use inside an ffmpeg filter graph option."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def grade_filter(style, lut_path):
    g = style.get("grade", {})
    parts = []
    if g.get("denoise", True):
        parts.append("hqdn3d=1.5:1.5:4:4")
    if lut_path:
        parts.append(f"lut3d=file='{esc(lut_path)}':interp=tetrahedral")
    grain = float(g.get("grain", 0) or 0)
    if grain > 0:
        parts.append(f"noise=alls={int(grain)}:allf=t+u")
    vig = float(g.get("vignette", 0) or 0)
    if vig > 0:
        angle = min(math.pi / 2, vig * math.pi / 2.2)
        parts.append(f"vignette=angle={angle:.4f}:mode=backward" if False else f"vignette=angle={angle:.4f}")
    return ",".join(parts)
