"""One reel in, more content out, in the same style pack:
  carousel : 1080x1350 slides (hook, one point per slide, CTA)
  stories  : the finished reel split at sentence boundaries into <=15s story clips, plus a story cover card
  trials   : three alternate cuts at preview quality (different hook, tighter pace, other caption style)"""
import copy, json
from pathlib import Path
from .util import log, ffmpeg, write_json, read_json, W, H
from .graphics import text_card
from .captions import _hero
from .cut import hook_candidates
from .render import render, timeline_for, QUALITY, _vcodec, first_phrase
from .style import load_style


def _kept_sentences(tr, timeline):
    """Sentences in output order, only kept words, with output start/end."""
    out = []
    for s in tr["sentences"]:
        kept = [i for i in s["words"] if str(i) in timeline["word_out"] or i in timeline["word_out"]]
        if not kept:
            continue
        wo = lambda i: timeline["word_out"].get(i, timeline["word_out"].get(str(i)))
        text = " ".join(tr["words"][i]["w"] for i in kept)
        out.append({"text": text, "s": wo(kept[0])["s"], "e": wo(kept[-1])["e"], "words": kept})
    out.sort(key=lambda x: x["s"])
    return out


def carousel(project, max_slides=8):
    timeline, tr, style = timeline_for(project)
    out_dir = project.exports / "carousel"; out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("slide-*.png"): old.unlink()
    sents = _kept_sentences(tr, timeline)
    if not sents:
        return []
    hook = sents[0]["text"]
    points = [s["text"] for s in sents[1:]]
    # merge very short sentences into the previous point so slides carry one idea each
    merged = []
    for p in points:
        if merged and len(p.split()) < 5:
            merged[-1] += " " + p
        else:
            merged.append(p)
    merged = merged[:max_slides - 2]
    cta = project.data.get("cta") or {}
    files = []
    handle = style["end_card"].get("line2") or ""
    files.append(text_card(style, hook, "", out_dir / "slide-01.png", accent_word=hook.split()[_hero(hook.split())[0]].strip(".,!?"), footer=handle, number=None))
    for k, p in enumerate(merged, 2):
        words = p.split()
        files.append(text_card(style, p, "", out_dir / f"slide-{k:02d}.png", accent_word=words[_hero(words)[0]].strip(".,!?"), footer=handle, number=k - 1))
    if cta.get("type") == "keyword" and cta.get("keyword"):
        title, body = f"Comment {cta['keyword']}", "and I'll send it straight to your DMs."
    elif cta.get("text"):
        title, body = cta["text"], ""
    else:
        title, body = "Follow for the next one", "Save this so you can find it again."
    files.append(text_card(style, title, body, out_dir / f"slide-{len(files) + 1:02d}.png", bg="dark", fg="light", accent_word=cta.get("keyword"), footer=handle))
    (out_dir / "caption.md").write_text(f"# Carousel caption draft\n\n{hook}\n\n" + "\n".join(f"{k}. {p}" for k, p in enumerate(merged, 1)) + f"\n\n{title} {body}\n", encoding="utf-8")
    log(f"carousel: {len(files)} slides in {out_dir}")
    return files


def stories(project, max_len=15.0):
    timeline, tr, style = timeline_for(project)
    src = project.work / "main-final.mp4"
    if not src.exists():
        src = project.work / "main-proxy.mp4"
    if not src.exists():
        render(project, quality="proxy"); src = project.work / "main-proxy.mp4"
    quality = "final" if src.name.endswith("final.mp4") else "proxy"
    out_dir = project.exports / "stories"; out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("story-*"): old.unlink()
    sents = _kept_sentences(tr, timeline)
    chunks, cur_s, cur_e = [], None, None
    for s in sents:
        if cur_s is None:
            cur_s, cur_e = s["s"], s["e"]; continue
        if s["e"] - cur_s > max_len:
            chunks.append((cur_s, cur_e)); cur_s, cur_e = s["s"], s["e"]
        else:
            cur_e = s["e"]
    if cur_s is not None:
        chunks.append((cur_s, cur_e))
    # snap chunk edges to cover the whole reel
    fixed = []
    for k, (a, b) in enumerate(chunks):
        a = 0.0 if k == 0 else fixed[-1][1]
        b = timeline["duration"] if k == len(chunks) - 1 else min(b + 0.15, timeline["duration"])
        fixed.append((a, b))
    files = []
    q = QUALITY[quality]
    for k, (a, b) in enumerate(fixed, 1):
        out = out_dir / f"story-{k:02d}.mp4"
        ffmpeg(["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, *_vcodec(q), out])
        files.append(out)
    hook = " ".join(sents[0]["text"].split()[:12]) if sents else first_phrase(tr, timeline, 9)
    files.append(text_card(style, hook, f"Part 1 of {len(fixed)}. Tap through.", out_dir / "story-cover.png", size=(W, H), accent_word=hook.split()[_hero(hook.split())[0]].strip(".,!?"), footer=style["end_card"].get("line2") or ""))
    log(f"stories: {len(fixed)} clips + cover in {out_dir}")
    return files


class _Ghost:
    """A project view that renders with modified settings but never writes project.json."""
    def __init__(self, project, data):
        self.dir, self.data, self.file = project.dir, data, project.file
        self.raw, self.transcript_file = project.raw, project.transcript_file
        self.work, self.overlays, self.exports = project.work, project.overlays, project.exports
    def save(self): pass
    def transcript(self): return read_json(self.transcript_file)


def trials(project):
    tr = project.transcript()
    base = copy.deepcopy(project.data)
    style = load_style(base["style"])
    out_dir = project.exports / "trials"; out_dir.mkdir(parents=True, exist_ok=True)
    cands = hook_candidates(tr, top=3)
    cur_hook = base["edit"].get("hook")
    alt = next((c for c in cands if c["range"] != cur_hook), cands[-1] if cands else None)
    variants = []
    # A: a different hook line opens the reel
    a = copy.deepcopy(base)
    if alt: a["edit"]["hook"] = alt["range"]
    variants.append(("trial-a-hook", a, f"opens on: {alt['text'] if alt else 'same hook'}"))
    # B: tighter pace (faster, shorter pauses)
    b = copy.deepcopy(base)
    b["edit"]["speed"] = round((base["edit"].get("speed") or style["cut"].get("speed", 1.0)) * 1.07, 3)
    tight = copy.deepcopy(style); tight["cut"]["max_pause"] = 0.22; tight["cut"]["keep_pause"] = 0.08
    tight_path = project.work / "style-trial-tight.json"; write_json(tight_path, tight); b["style"] = str(tight_path)
    variants.append(("trial-b-tight", b, f"7% faster, pauses trimmed to 0.22s"))
    # C: the other caption style
    c = copy.deepcopy(base)
    cur_mode = base["captions"].get("mode") or style["captions"]["mode"]
    c["captions"]["mode"] = "word_pop" if cur_mode != "word_pop" else "editorial_split"
    c["captions"]["zone"] = "chest" if c["captions"]["mode"] == "word_pop" else "upper"
    c["captions"]["size"] = 110 if c["captions"]["mode"] == "word_pop" else 58
    variants.append(("trial-c-captions", c, f"captions as {c['captions']['mode']}"))
    files, notes = [], ["# Trial reels (preview quality)", ""]
    for name, data, why in variants:
        ghost = _Ghost(project, data)
        out = render(ghost, quality="proxy", out_name=f"trials/{name}.mp4")
        files.append(out); notes.append(f"- `{name}.mp4`: {why}")
    (out_dir / "README.md").write_text("\n".join(notes) + "\n\nPick the one that holds you at second 8, then apply its change to the main project (hook / speed / captions) and render final.\n", encoding="utf-8")
    # the ghost renders overwrote cover/notes/srt in exports; restore the main project's by re-rendering its proxy
    render(project, quality="proxy")
    log(f"trials: 3 cuts in {out_dir}")
    return files


def repurpose(project, what="all"):
    out = []
    if what in ("carousel", "all"): out += carousel(project)
    if what in ("stories", "all"): out += stories(project)
    if what in ("trials", "all"): out += trials(project)
    return out
