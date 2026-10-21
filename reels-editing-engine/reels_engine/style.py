"""Style packs: fonts, colors, caption mode, cut pace, grade, sound. Your look lives here."""
import copy, json
from pathlib import Path
from .util import STYLES_DIR, FONTS_DIR, read_json, write_json, log


def list_styles():
    out = []
    for p in sorted(STYLES_DIR.glob("*.json")):
        d = read_json(p)
        out.append((d.get("name", p.stem), d.get("label", "")))
    return out


def load_style(name_or_path, overrides=None):
    p = Path(name_or_path)
    if not p.exists():
        p = STYLES_DIR / f"{name_or_path}.json"
    if not p.exists():
        raise FileNotFoundError(f"style pack not found: {name_or_path}. Available: {', '.join(n for n, _ in list_styles())}")
    style = read_json(p)
    base = read_json(STYLES_DIR / "butter.json")
    style = _merge(base, style)  # butter carries every default key
    for key, val in (overrides or {}).items():
        set_path(style, key, val)
    _check_fonts(style)
    return style


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def set_path(d, dotted, value):
    """set_path(style, 'captions.size', 72) — values parse as JSON when they look like it."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            pass
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _check_fonts(style):
    fallback = {"caption_file": "DejaVuSans-Bold.ttf", "hero_file": "DejaVuSerif-BoldItalic.ttf", "title_file": "DejaVuSerif-Bold.ttf"}
    for key in ("caption_file", "caption_bold_file", "hero_file", "title_file", "annotation_file"):
        fn = style["fonts"].get(key)
        if fn and not (FONTS_DIR / fn).exists():
            log(f"warning: font file {fn} missing in {FONTS_DIR}; captions fall back to a system font")
            style["fonts"][key.replace("_file", "")] = "DejaVu Sans"


def color(style, key_or_hex):
    """Resolve 'accent' -> '#E8187A' (pass-through for raw hex)."""
    if key_or_hex.startswith("#"):
        return key_or_hex
    return style["colors"][key_or_hex]


def save_custom_style(name, style):
    p = STYLES_DIR / f"{name}.json"
    style["name"] = name
    write_json(p, style)
    return p


def new_style_from_answers(name, label, accent, win, dark, light, caption_font_file, hero_font_file, mode, sfx, all_caps):
    """Build-your-own look: a few answers in, a style pack out."""
    s = load_style("butter")
    s.update({"name": name, "label": label})
    s["colors"].update({"accent": accent, "win": win or accent, "dark": dark, "ink": dark, "light": light, "light_dim": light})
    files = {"Manrope-SemiBold.ttf": "Manrope SemiBold", "Manrope-ExtraBold.ttf": "Manrope ExtraBold", "Manrope-Regular.ttf": "Manrope",
             "Fraunces-SemiBoldItalic.ttf": "Fraunces SemiBold", "Fraunces-BoldItalic.ttf": "Fraunces Bold", "Fraunces-Bold.ttf": "Fraunces Bold", "Fraunces-SemiBold.ttf": "Fraunces SemiBold"}
    s["fonts"]["caption_file"] = caption_font_file; s["fonts"]["caption"] = files.get(caption_font_file, Path(caption_font_file).stem)
    s["fonts"]["hero_file"] = hero_font_file; s["fonts"]["hero"] = files.get(hero_font_file, Path(hero_font_file).stem)
    s["fonts"]["hero_italic"] = "Italic" in hero_font_file
    s["captions"]["mode"] = mode
    s["captions"]["zone"] = "upper" if mode == "editorial_split" else "center"
    s["captions"]["size"] = 58 if mode == "editorial_split" else 92
    s["captions"]["max_words"] = 4 if mode == "editorial_split" else (1 if mode == "word_pop" else 8)
    s["captions"]["case"] = "upper" if all_caps else "normal"
    s["sound"]["sfx"] = sfx
    s["sound"]["sfx_every"] = {"none": [0, 0], "light": [8, 10], "lively": [5, 6]}[sfx]
    s["rules"]["all_caps"] = all_caps
    return s
