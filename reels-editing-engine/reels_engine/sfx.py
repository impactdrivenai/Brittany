"""Sound effect bank. Ships with a synthesized starter set (felt, not heard). Drop your own WAV/MP3 files
into sfx/ with descriptive names; anything containing a banned word (whoosh, swish) is never used."""
import math, random, struct, wave
from pathlib import Path
import numpy as np
from .util import SFX_DIR, read_json, write_json, log

SR = 48000

# family -> which visual event it suits
FAMILIES = {
    "pop-soft": "graphic or caption lands", "click-soft": "cut or jump cut", "tick-typewriter": "label or list line",
    "paper-flip": "screenshot or card in", "ding-soft": "a win or a number", "thud-low": "big statement",
    "pop-bubble": "chip appears", "shutter": "polaroid or photo", "projector-click": "film gate opens",
    "chime-soft": "payoff", "coin": "money mention",
}


def _env(n, attack=0.002, decay=0.08):
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(attack, 1e-4))
    d = np.exp(-t / max(decay, 1e-4))
    return a * d


def _tone(freq, dur, decay, sweep_to=None, harmonics=(1.0,)):
    n = int(SR * dur)
    t = np.arange(n) / SR
    if sweep_to:
        f = np.linspace(freq, sweep_to, n)
        phase = 2 * np.pi * np.cumsum(f) / SR
    else:
        phase = 2 * np.pi * freq * t
    sig = sum(h * np.sin(phase * (i + 1)) for i, h in enumerate(harmonics))
    return sig * _env(n, decay=decay)


def _noise(dur, decay, lowpass=None):
    n = int(SR * dur)
    x = np.random.RandomState(7).randn(n)
    if lowpass:
        k = max(1, int(SR / lowpass / 2))
        x = np.convolve(x, np.ones(k) / k, mode="same")
    return x * _env(n, decay=decay)


def _mix(*sigs):
    n = max(len(x) for x in sigs)
    out = np.zeros(n)
    for x in sigs:
        out[:len(x)] += x
    return out


def _write(path, sig, gain=0.5):
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * gain
    pcm = (sig * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def generate_bank(force=False):
    SFX_DIR.mkdir(exist_ok=True)
    made = []
    recipes = {
        "pop-soft": lambda: _tone(620, 0.12, 0.035, sweep_to=240),
        "pop-bubble": lambda: _tone(320, 0.09, 0.03, sweep_to=980),
        "click-soft": lambda: _noise(0.03, 0.006, lowpass=4000),
        "tick-typewriter": lambda: _mix(_tone(1800, 0.05, 0.012), 0.5 * _noise(0.04, 0.008, lowpass=6000)),
        "paper-flip": lambda: _noise(0.22, 0.07, lowpass=1500),
        "ding-soft": lambda: _tone(1046, 0.6, 0.22, harmonics=(1.0, 0.35, 0.12)),
        "chime-soft": lambda: _mix(_tone(1568, 0.7, 0.25, harmonics=(1.0, 0.3)), 0.6 * _tone(2093, 0.7, 0.2)),
        "thud-low": lambda: _tone(70, 0.35, 0.12, sweep_to=40),
        "shutter": lambda: np.concatenate([_noise(0.03, 0.006, lowpass=5000), np.zeros(int(SR * 0.05)), _noise(0.04, 0.008, lowpass=3500)]),
        "projector-click": lambda: np.concatenate([_tone(900, 0.03, 0.008), np.zeros(int(SR * 0.04)), _tone(600, 0.04, 0.01)]),
        "coin": lambda: _mix(_tone(2200, 0.35, 0.09, harmonics=(1.0, 0.5)), 0.5 * _tone(3300, 0.3, 0.07)),
    }
    for name, fn in recipes.items():
        p = SFX_DIR / f"{name}.wav"
        if p.exists() and not force:
            continue
        _write(p, fn())
        made.append(p.name)
    if made:
        log(f"synthesized starter sound bank: {', '.join(made)}")
    return made


def bank(banned=()):
    """All usable sfx files, grouped by family (filename prefix before the first '.')."""
    generate_bank()
    files = []
    for p in sorted(SFX_DIR.iterdir()):
        if p.suffix.lower() not in (".wav", ".mp3", ".m4a", ".ogg", ".flac"):
            continue
        if any(b in p.stem.lower() for b in banned):
            continue
        files.append(p)
    return files


def pick_for(event, files, used):
    """Pick a sound that fits the event and was not used yet in this reel."""
    prefs = {
        "cut": ["click-soft", "tick-typewriter"], "caption": ["pop-soft", "pop-bubble", "tick-typewriter"],
        "graphic": ["pop-soft", "pop-bubble", "paper-flip"], "number": ["ding-soft", "chime-soft", "coin"],
        "statement": ["thud-low"], "endcard": ["pop-soft"], "screenshot": ["paper-flip", "shutter"],
    }.get(event, ["pop-soft"])
    for pref in prefs:
        for f in files:
            if f.stem.startswith(pref) and f not in used:
                return f
    for f in files:
        if f not in used:
            return f
    return None
