"""Rebuild the static caption fonts from the variable Google Fonts files in fonts/variable/.
Run once after dropping new variable fonts in:  python3 reels-editing-engine/tools/prepare_fonts.py
- instances Manrope (400/600/800) and Fraunces (600/800, upright + italic) at 72pt optical size
- gives each file a clean family name libass can match (e.g. "Fraunces SemiBold" + Italic flag)
- makes lining numerals the default when a font ships an 'lnum' feature (Google's Fraunces build does not; number
  hero words therefore render in the bold sans caption font, see captions.py)"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = Path(__file__).resolve().parent.parent / "fonts"
VAR = FONTS / "variable"
JOBS = [
    ("Manrope[wght].ttf", {"wght": 400}, "Manrope-Regular.ttf", "Manrope", "Regular"),
    ("Manrope[wght].ttf", {"wght": 600}, "Manrope-SemiBold.ttf", "Manrope SemiBold", "Regular"),
    ("Manrope[wght].ttf", {"wght": 800}, "Manrope-ExtraBold.ttf", "Manrope ExtraBold", "Regular"),
    ("Fraunces[SOFT,WONK,opsz,wght].ttf", {"wght": 600, "opsz": 72, "SOFT": 0, "WONK": 0}, "Fraunces-SemiBold.ttf", "Fraunces SemiBold", "Regular"),
    ("Fraunces[SOFT,WONK,opsz,wght].ttf", {"wght": 800, "opsz": 72, "SOFT": 0, "WONK": 0}, "Fraunces-Bold.ttf", "Fraunces Bold", "Regular"),
    ("Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", {"wght": 600, "opsz": 72, "SOFT": 0, "WONK": 0}, "Fraunces-SemiBoldItalic.ttf", "Fraunces SemiBold", "Italic"),
    ("Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", {"wght": 800, "opsz": 72, "SOFT": 0, "WONK": 0}, "Fraunces-BoldItalic.ttf", "Fraunces Bold", "Italic"),
]


def set_names(font, family, sub):
    n = font["name"]
    for nid in (1, 2, 3, 4, 6, 16, 17):
        n.removeNames(nameID=nid)
    full = family + ("" if sub == "Regular" else " " + sub)
    n.setName(family, 1, 3, 1, 0x409); n.setName(sub, 2, 3, 1, 0x409); n.setName(full + ";reels", 3, 3, 1, 0x409)
    n.setName(full, 4, 3, 1, 0x409); n.setName(full.replace(" ", "-"), 6, 3, 1, 0x409)
    if sub == "Italic":
        font["OS/2"].fsSelection |= 1; font["head"].macStyle |= 2
    else:
        font["OS/2"].fsSelection &= ~1; font["head"].macStyle &= ~2


def lining_numerals_default(font):
    """Point the digit code points at the 'lnum' alternates so captions get full-height numbers."""
    gsub = font.get("GSUB")
    if not gsub:
        return 0
    lookups = set()
    for fr in gsub.table.FeatureList.FeatureRecord:
        if fr.FeatureTag == "lnum":
            lookups.update(fr.Feature.LookupListIndex)
    mapping = {}
    for li in lookups:
        for st in gsub.table.LookupList.Lookup[li].SubTable:
            if getattr(st, "mapping", None):
                mapping.update(st.mapping)
    if not mapping:
        return 0
    changed = 0
    for table in font["cmap"].tables:
        for cp, g in list(table.cmap.items()):
            if g in mapping and 0x30 <= cp <= 0x39:
                table.cmap[cp] = mapping[g]; changed += 1
    return changed


def main():
    for src, axes, dst, family, sub in JOBS:
        path = VAR / src
        if not path.exists():
            print("missing", path); continue
        f = TTFont(path)
        inst = instancer.instantiateVariableFont(f, axes, updateFontNames=False)
        set_names(inst, family, sub)
        n = lining_numerals_default(inst) if family.startswith("Fraunces") else 0
        inst.save(FONTS / dst)
        print(f"{dst:32s} {family} / {sub}{'  (lining numerals)' if n else ''}")


if __name__ == "__main__":
    main()
