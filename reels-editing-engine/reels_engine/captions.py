"""Captions as ASS subtitles rendered by ffmpeg/libass. Three modes:
  editorial_split : small connecting words + one big hero word (serif italic), phrases replace each other on the beat
  word_pop        : one word at a time, big bold, snapping in
  sentence        : one full sentence at a time, quiet serif, below the picture
Captions are exact: fixes from project.json replace misheard words. Never over the face zone you set, never in the
bottom 20 percent where Instagram's UI sits."""
import re
from .util import hex_to_ass, fmt_ass_time, W, H

STOP = set("""a an the and or but so to of in on at for with from by as is are was were be been it its this that these those
i you he she we they me him her us them my your his our their am do does did have has had not no yes if then than just
very really like about into over under up down out off here there what when where who why how can could would should will
all any some more most much many few own same too also""".split())
NUM = re.compile(r"\d")
SENT_END = re.compile(r"[.!?]$")

ZONES = {"top": 300, "upper": 440, "center": 930, "chest": 1230, "lower": 1400}   # y centre of the caption block (1080x1920 space)


def _case(text, mode):
    return text.upper() if mode == "upper" else text


def _phrases(words_out, transcript, max_words, gap=0.45, style_mode="editorial_split"):
    """words_out: list of (idx, s, e) in output order."""
    phrases, cur = [], []
    for k, (i, s, e) in enumerate(words_out):
        if cur:
            pi, ps, pe = cur[-1]
            w_prev = transcript["words"][pi]["w"]
            if len(cur) >= max_words or SENT_END.search(w_prev) or s - pe > gap or (style_mode != "sentence" and w_prev.endswith(",") and len(cur) >= 2):
                phrases.append(cur); cur = []
        cur.append((i, s, e))
    if cur:
        phrases.append(cur)
    return phrases


def _hero(tokens):
    """Pick the hero word: numbers first, then the longest non-stop word, else the last word."""
    clean = [(k, re.sub(r"[^A-Za-z0-9$%']", "", t)) for k, t in enumerate(tokens)]
    nums = [k for k, t in clean if NUM.search(t)]
    if nums:
        return nums[0], True
    cands = [(len(t), k) for k, t in clean if t and t.lower() not in STOP]
    if cands:
        return max(cands)[1], False
    return len(tokens) - 1, False


def _tag_block(style, font, size, color_hex, italic=False, pop=True, shadow=True):
    ink = style["colors"]["ink"]
    tags = f"\\fn{font}\\fs{int(size)}\\c{hex_to_ass(color_hex)}\\b0"
    tags += "\\i1" if italic else "\\i0"
    if shadow:
        tags += f"\\bord3\\3c{hex_to_ass(ink, 0x70)}\\shad4\\4c{hex_to_ass(ink, 0x90)}\\blur5"
    else:
        tags += "\\bord0\\shad0"
    return tags


def build_ass(transcript, timeline, style, caption_cfg, out_path, face_zone=None):
    cap = dict(style["captions"])
    for k in ("mode", "zone", "size"):
        if caption_cfg.get(k):
            cap[k] = caption_cfg[k]
    fixes = {int(k): v for k, v in (caption_cfg.get("fixes") or {}).items()}
    mode = cap.get("mode", "editorial_split")
    size = int(cap.get("size", 58))
    y = ZONES.get(cap.get("zone", "upper"), 560) if not isinstance(cap.get("zone"), int) else int(cap["zone"])
    if face_zone and face_zone[0] <= y <= face_zone[1]:
        y = ZONES["upper"] if face_zone[0] > 400 else ZONES["lower"]
    fonts, colors = style["fonts"], style["colors"]
    text_c = colors.get(cap.get("text_color", "light"), "#FFFFFF")
    hero_c = colors.get(cap.get("hero_color", "accent"), "#FFFFFF")
    num_c = colors.get(cap.get("number_color", "win"), hero_c)
    pop = bool(cap.get("pop", True))
    shadow = bool(cap.get("shadow", True))
    case = cap.get("case", "normal")

    words_out = sorted(((i, v["s"], v["e"]) for i, v in timeline["word_out"].items()), key=lambda t: t[1])
    words_out = [(int(i), s, e) for i, s, e in words_out]
    tok = lambda i: _case(fixes.get(i, transcript["words"][i]["w"]), case)

    pop_tags = "\\fscx90\\fscy90\\t(0,70,\\fscx105\\fscy105)\\t(70,130,\\fscx100\\fscy100)" if pop else "\\fad(60,0)"
    events = []

    if mode == "word_pop":
        for k, (i, s, e) in enumerate(words_out):
            nxt = words_out[k + 1][1] if k + 1 < len(words_out) else timeline["duration"]
            end = min(max(e + 0.08, s + 0.18), nxt) if nxt > s else e
            t = tok(i)
            c = num_c if NUM.search(t) else text_c
            tags = _tag_block(style, fonts.get("caption_bold", fonts["caption"]), size, c, False, pop, shadow)
            events.append((s, end, f"{{\\an5\\pos({W//2},{y}){tags}{pop_tags}}}{_esc(t)}"))
    else:
        max_words = int(cap.get("max_words", 4 if mode == "editorial_split" else 8))
        phrases = _phrases(words_out, transcript, max_words, style_mode=mode)
        for k, ph in enumerate(phrases):
            s = max(0.0, ph[0][1] - 0.05)
            nxt = phrases[k + 1][0][1] - 0.05 if k + 1 < len(phrases) else timeline["duration"]
            end = min(max(ph[-1][2] + 0.25, s + 0.6), max(nxt, s + 0.2))
            toks = [tok(i) for i, _, _ in ph]
            if mode == "sentence":
                tags = _tag_block(style, fonts["hero"], size, text_c, fonts.get("hero_italic", True), False, shadow)
                events.append((s, end, f"{{\\an5\\pos({W//2},{y}){tags}\\fad(50,0)}}{_esc(' '.join(toks))}"))
                continue
            h, is_num = _hero(toks)
            small = _tag_block(style, fonts["caption"], size, text_c, False, pop, shadow)
            if is_num:   # numbers read as a crisp scoreboard: bold sans in the win colour (serif old-style figures sit too low)
                hero = _tag_block(style, fonts.get("caption_bold", fonts["caption"]), size * float(cap.get("hero_scale", 1.9)) * 0.9, num_c, False, pop, shadow)
            else:
                hero = _tag_block(style, fonts["hero"], size * float(cap.get("hero_scale", 1.9)), hero_c, fonts.get("hero_italic", True), pop, shadow)
            before = " ".join(toks[:h]); after = " ".join(toks[h + 1:])
            lines = []
            if before: lines.append(f"{{{small}}}{_esc(before)}")
            lines.append(f"{{{hero}}}{_esc(toks[h])}")
            if after: lines.append(f"{{{small}}}{_esc(after)}")
            events.append((s, end, f"{{\\an5\\pos({W//2},{y}){pop_tags}}}" + "\\N".join(lines)))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{fonts['caption']},{size},{hex_to_ass(text_c)},&H000000FF&,{hex_to_ass(colors['ink'], 0x70)},{hex_to_ass(colors['ink'], 0x90)},0,0,0,0,100,100,0,0,1,3,4,5,90,90,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "\n".join(f"Dialogue: 0,{fmt_ass_time(s)},{fmt_ass_time(e)},Default,,0,0,0,,{t}" for s, e, t in events)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + body + "\n")
    return out_path, len(events)


def build_srt(transcript, timeline, caption_cfg, out_path, max_words=6):
    fixes = {int(k): v for k, v in (caption_cfg.get("fixes") or {}).items()}
    words_out = sorted(((int(i), v["s"], v["e"]) for i, v in timeline["word_out"].items()), key=lambda t: t[1])
    phrases = _phrases(words_out, transcript, max_words, style_mode="sentence")
    from .util import fmt_srt_time
    lines = []
    for n, ph in enumerate(phrases, 1):
        text = " ".join(fixes.get(i, transcript["words"][i]["w"]) for i, _, _ in ph)
        lines += [str(n), f"{fmt_srt_time(ph[0][1])} --> {fmt_srt_time(ph[-1][2] + 0.2)}", text, ""]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def _esc(t):
    return t.replace("{", "(").replace("}", ")")
