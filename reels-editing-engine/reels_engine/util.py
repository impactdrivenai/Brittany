import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = ENGINE_DIR / "fonts"
STYLES_DIR = ENGINE_DIR / "styles"
SFX_DIR = ENGINE_DIR / "sfx"
TEMPLATES_DIR = ENGINE_DIR / "templates"
REELS_DIR = Path(os.environ.get("REELS_DIR", ENGINE_DIR.parent / "reels"))

W, H, FPS = 1080, 1920, 30


def log(msg):
    print(f"[reel] {msg}", flush=True)


def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return text[:60] or "reel"


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)


def run(cmd, quiet=True, check=True):
    """Run a command (list). Returns CompletedProcess. Raises with stderr on failure."""
    if os.environ.get("REEL_DEBUG"):
        log(" ".join(str(c) for c in cmd))
    res = subprocess.run([str(c) for c in cmd], capture_output=quiet, text=True)
    if check and res.returncode != 0:
        err = (res.stderr or "")[-4000:]
        raise RuntimeError(f"command failed ({res.returncode}): {' '.join(str(c) for c in cmd[:6])} ...\n{err}")
    return res


def ffmpeg(args, quiet=True):
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], quiet=quiet)


def have(binary):
    return shutil.which(binary) is not None


def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_ass(hex_color, alpha=0):
    """#RRGGBB -> &HAABBGGRR& (ASS colour order)."""
    r, g, b = hex_to_rgb(hex_color)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"


def fmt_ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def fmt_srt_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def font_path(family_file):
    p = FONTS_DIR / family_file
    return p if p.exists() else None
