#!/usr/bin/env python3
"""Reels Editing Engine CLI. Claude Code drives this from plain language; you can also run it by hand.

  reel setup                                  check ffmpeg, python deps, fonts, sound bank
  reel new <video> [--name x] [--style brittany]   copy footage into a new reel project
  reel transcribe <project> [--model small]   word timestamps with faster-whisper
  reel import-transcript <project> <file>     use an SRT/VTT/JSON transcript instead
  reel words <project>                        numbered transcript (what to cut)
  reel cut <project> 12-15 40 "um"            cut words by number, range, or exact word
  reel restore <project> 12-15 | all          undo cuts
  reel hook <project> 23-31 | suggest | clear move a line to the front
  reel zoom <project> 4.5-6.0 1.2 | clear     punch in on an output-time range
  reel fix <project> 18 "Claude"              correct a misheard word in the captions
  reel captions <project> --mode word_pop --zone upper --size 72 --off
  reel cta <project> keyword TEAM | share "Send this to..." | none
  reel style <project> playful | list | set captions.size 72 | new <name> ...
  reel music <project> path/to/track.mp3 [--db 20] | none
  reel speed <project> 1.08
  reel cover <project> 3.2
  reel render <project> [--proxy] [--out name.mp4]
  reel preview <project> [--port 8765]        live editor: click words, tap Cut, watch the reel update
  reel repurpose <project> [carousel|stories|trials|all]
  reel export-project <project>               clean cut + SRT + EDL + JSON for CapCut or any editor
  reel status <project>
"""
import argparse, json, os, re, sys, webbrowser
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reels_engine.util import log, REELS_DIR, ENGINE_DIR, have, FONTS_DIR
from reels_engine.project import Project, find_project, latest_project
from reels_engine import style as style_mod


def proj(arg):
    if arg in (None, "", "latest", "."):
        p = Project(".") if Path("project.json").exists() else latest_project()
        if p is None:
            sys.exit("no reel project yet. Run: reel new <video>")
        return p
    return find_project(arg)


def parse_indices(tokens, transcript):
    out = set()
    for t in tokens:
        m = re.fullmatch(r"(\d+)-(\d+)", t)
        if m:
            out.update(range(int(m.group(1)), int(m.group(2)) + 1)); continue
        if t.isdigit():
            out.add(int(t)); continue
        # exact word match (case-insensitive, punctuation-insensitive)
        key = re.sub(r"[^a-z0-9']", "", t.lower())
        hits = [w["i"] for w in transcript["words"] if re.sub(r"[^a-z0-9']", "", w["w"].lower()) == key]
        if not hits:
            log(f"no word matches '{t}'")
        out.update(hits)
    return sorted(out)


def cmd_setup(a):
    ok = True
    for b in ("ffmpeg", "ffprobe"):
        print(f"  {'ok ' if have(b) else 'MISSING'} {b}")
        ok &= have(b)
    for mod in ("numpy", "PIL", "faster_whisper", "pocketsphinx"):
        try:
            __import__(mod); print(f"  ok  python {mod}")
        except ImportError:
            print(f"  MISSING python {mod}  ->  pip install -r {ENGINE_DIR / 'requirements.txt'}"); ok = False
    fonts = sorted(p.name for p in FONTS_DIR.glob("*.ttf"))
    print(f"  {'ok ' if fonts else 'MISSING'} fonts: {', '.join(fonts) or 'none (captions fall back to system fonts)'}")
    from reels_engine.sfx import bank
    print(f"  ok  sound bank: {len(bank())} sounds")
    print(f"  reels folder: {REELS_DIR}")
    if a.model:
        from faster_whisper import WhisperModel
        log(f"downloading whisper model '{a.model}'..."); WhisperModel(a.model, device="auto", compute_type="auto"); log("model ready")
    print("setup complete" if ok else "setup incomplete: fix the MISSING lines above")


def cmd_new(a):
    p = Project.create(a.video, name=a.name, style=a.style, reels_dir=a.reels_dir)
    print(p.dir)
    if a.transcribe:
        a.project = str(p.dir); a.model = a.model or "small"; a.language = None; a.engine = "auto"
        cmd_transcribe(a)


def cmd_transcribe(a):
    p = proj(a.project)
    from reels_engine.transcribe import transcribe
    tr = transcribe(p.raw, p.transcript_file, model_size=a.model or "small", language=a.language, work_dir=p.work, engine=a.engine)
    _after_transcript(p, tr)


def cmd_import_transcript(a):
    p = proj(a.project)
    from reels_engine.transcribe import import_transcript
    tr = import_transcript(a.file, p.transcript_file)
    _after_transcript(p, tr)


def _after_transcript(p, tr):
    from reels_engine.cut import auto_removals, hook_candidates
    st = style_mod.load_style(p.data["style"])
    p.data["edit"]["auto_removed"] = auto_removals(tr["words"], st["cut"])
    p.save()
    _write_words_md(p, tr)
    print(f"\nauto-cut {len(p.data['edit']['auto_removed'])} filler/stutter words. Hook candidates:")
    for h in hook_candidates(tr):
        print(f"  words {h['range'][0]}-{h['range'][1]}  (score {h['score']}): {h['text']}")
    print(f"\nnumbered transcript: {p.dir / 'transcript.md'}")


def _write_words_md(p, tr=None):
    from reels_engine.transcribe import transcript_markdown
    tr = tr or p.transcript()
    (p.dir / "transcript.md").write_text(transcript_markdown(tr, p.data["edit"]), encoding="utf-8")


def cmd_words(a):
    p = proj(a.project); tr = p.transcript()
    if tr is None:
        sys.exit("no transcript yet: run reel transcribe")
    _write_words_md(p, tr)
    print((p.dir / "transcript.md").read_text(encoding="utf-8"))


def cmd_cut(a):
    p = proj(a.project); tr = p.transcript()
    idx = parse_indices(a.words, tr)
    ed = p.data["edit"]
    ed["removed"] = sorted(set(ed["removed"]) | set(idx))
    ed["kept"] = [k for k in ed["kept"] if k not in idx]
    p.save(); _write_words_md(p, tr)
    print(f"cut {len(idx)} words: " + " ".join(tr['words'][i]['w'] for i in idx))


def cmd_restore(a):
    p = proj(a.project); tr = p.transcript(); ed = p.data["edit"]
    if a.words == ["all"]:
        ed["removed"], ed["auto_removed"], ed["kept"] = [], [], []
        print("restored every word")
    else:
        idx = set(parse_indices(a.words, tr))
        ed["removed"] = [i for i in ed["removed"] if i not in idx]
        ed["kept"] = sorted(set(ed["kept"]) | (idx & set(ed["auto_removed"])))
        print(f"restored {len(idx)} words")
    p.save(); _write_words_md(p, tr)


def cmd_hook(a):
    p = proj(a.project); tr = p.transcript()
    from reels_engine.cut import hook_candidates
    if a.range == "suggest":
        for h in hook_candidates(tr):
            print(f"  words {h['range'][0]}-{h['range'][1]}  (score {h['score']}): {h['text']}")
        return
    if a.range == "clear":
        p.data["edit"]["hook"] = None; p.save(); print("hook cleared"); return
    m = re.fullmatch(r"(\d+)-(\d+)", a.range)
    if not m:
        sys.exit("hook needs a word range like 23-31, or 'suggest' / 'clear'")
    p.data["edit"]["hook"] = [int(m.group(1)), int(m.group(2))]
    p.save()
    print("hook: " + " ".join(tr["words"][i]["w"] for i in range(int(m.group(1)), int(m.group(2)) + 1)))


def cmd_zoom(a):
    p = proj(a.project)
    if a.range == "clear":
        p.data["edit"]["zooms"] = []; p.save(); print("zooms cleared"); return
    s, e = a.range.split("-")
    p.data["edit"]["zooms"].append({"start": float(s), "end": float(e), "scale": float(a.scale)})
    p.save(); print(f"zoom {a.scale}x from {s}s to {e}s (output time)")


def cmd_fix(a):
    p = proj(a.project); tr = p.transcript()
    p.data["captions"].setdefault("fixes", {})[str(a.index)] = a.text
    p.save(); print(f"caption fix: word {a.index} '{tr['words'][a.index]['w']}' -> '{a.text}'")


def cmd_captions(a):
    p = proj(a.project); c = p.data["captions"]
    if a.off: c["enabled"] = False
    if a.on: c["enabled"] = True
    if a.mode: c["mode"] = a.mode
    if a.zone: c["zone"] = int(a.zone) if a.zone.isdigit() else a.zone
    if a.size: c["size"] = int(a.size)
    p.save(); print(json.dumps(c))


def cmd_cta(a):
    p = proj(a.project)
    kind = a.kind
    if kind == "none":
        p.data["cta"] = {"keyword": None, "text": None, "type": None}
    elif kind == "keyword":
        if not a.value: sys.exit("usage: reel cta <project> keyword TEAM")
        p.data["cta"] = {"keyword": a.value.upper(), "text": a.text, "type": "keyword"}
    else:
        p.data["cta"] = {"keyword": None, "text": a.value or {"share": "Send this to the woman who gets it", "follow": "Follow for part 2", "save": "Save this for Monday"}[kind], "type": kind}
    p.save(); print(json.dumps(p.data["cta"]))


def cmd_style(a):
    if a.action == "list":
        for n, label in style_mod.list_styles():
            print(f"  {n:12s} {label}")
        return
    if a.action == "new":
        kw = dict(x.split("=", 1) for x in a.args)
        s = style_mod.new_style_from_answers(
            a.target, kw.get("label", a.target), kw.get("accent", "#E8187A"), kw.get("win"), kw.get("dark", "#111111"), kw.get("light", "#FFFAFA"),
            kw.get("caption_font", "Manrope-SemiBold.ttf"), kw.get("hero_font", "Fraunces-SemiBoldItalic.ttf"),
            kw.get("mode", "editorial_split"), kw.get("sfx", "light"), kw.get("caps", "no").lower() in ("yes", "true", "1"))
        if "line1" in kw:
            s["end_card"].update({"enabled": True, "line1": kw["line1"], "line2": kw.get("line2", "")})
        path = style_mod.save_custom_style(a.target, s)
        print(f"style pack written: {path}")
        return
    p = proj(a.project)
    if a.action == "set":
        # per-project override is stored by writing a project-local style pack copy
        st = style_mod.load_style(p.data["style"])
        style_mod.set_path(st, a.target, " ".join(a.args))
        local = p.dir / "style.json"
        style_mod.write_json(local, st)
        p.data["style"] = str(local); p.save()
        print(f"{a.target} = {' '.join(a.args)}  (project-local style at {local})")
        return
    # action is a style name
    style_mod.load_style(a.action)
    p.data["style"] = a.action; p.save()
    print(f"style pack: {a.action}")


def cmd_music(a):
    p = proj(a.project)
    p.data["music"] = None if a.path == "none" else str(Path(a.path).expanduser().resolve())
    if a.db: p.data["music_db_under_voice"] = float(a.db)
    p.save(); print(f"music: {p.data['music']}")


def cmd_speed(a):
    p = proj(a.project); p.data["edit"]["speed"] = float(a.value); p.save(); print(f"speed {a.value}")


def cmd_cover(a):
    p = proj(a.project); p.data["cover_time"] = float(a.time); p.save(); print(f"cover frame at {a.time}s")


def cmd_endcard(a):
    p = proj(a.project); p.data["end_card"] = (a.value == "on"); p.save(); print(f"end card {a.value}")


def cmd_render(a):
    p = proj(a.project)
    from reels_engine.render import render
    out = render(p, quality="proxy" if a.proxy else "final", out_name=a.out)
    print(out)


def cmd_preview(a):
    p = proj(a.project)
    from reels_engine.preview import serve
    serve(p, port=a.port, open_browser=not a.no_open)


def cmd_repurpose(a):
    p = proj(a.project)
    from reels_engine.repurpose import repurpose
    for path in repurpose(p, a.what):
        print(path)


def cmd_export_project(a):
    p = proj(a.project)
    from reels_engine.export_project import export_project
    print(export_project(p))


def cmd_status(a):
    p = proj(a.project)
    tr = p.transcript()
    print(f"project: {p.dir}\nstyle: {p.data['style']}\nsource: {p.data['source']} {p.data['info'].get('width')}x{p.data['info'].get('height')} {p.data['info'].get('duration'):.1f}s")
    if tr:
        from reels_engine.render import timeline_for
        tl, _, _ = timeline_for(p)
        from reels_engine.cut import describe
        print("timeline:", describe(tl, tr))
    print("edit:", json.dumps(p.data["edit"]))
    print("captions:", json.dumps(p.data["captions"]), "\ncta:", json.dumps(p.data["cta"]))
    ex = sorted(p.exports.glob("*")) if (p.dir / "exports").exists() else []
    print("exports:", ", ".join(x.name for x in ex) or "none yet")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--model", help="also download this whisper model (tiny/base/small/medium)"); s.set_defaults(fn=cmd_setup)
    s = sub.add_parser("new"); s.add_argument("video"); s.add_argument("--name"); s.add_argument("--style", default="brittany"); s.add_argument("--reels-dir"); s.add_argument("--transcribe", action="store_true"); s.add_argument("--model"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("transcribe"); s.add_argument("project", nargs="?"); s.add_argument("--model"); s.add_argument("--language"); s.add_argument("--engine", choices=["auto", "whisper", "sphinx"], default="auto"); s.set_defaults(fn=cmd_transcribe)
    s = sub.add_parser("import-transcript"); s.add_argument("project"); s.add_argument("file"); s.set_defaults(fn=cmd_import_transcript)
    s = sub.add_parser("words"); s.add_argument("project", nargs="?"); s.set_defaults(fn=cmd_words)
    s = sub.add_parser("cut"); s.add_argument("project"); s.add_argument("words", nargs="+"); s.set_defaults(fn=cmd_cut)
    s = sub.add_parser("restore"); s.add_argument("project"); s.add_argument("words", nargs="+"); s.set_defaults(fn=cmd_restore)
    s = sub.add_parser("hook"); s.add_argument("project"); s.add_argument("range"); s.set_defaults(fn=cmd_hook)
    s = sub.add_parser("zoom"); s.add_argument("project"); s.add_argument("range"); s.add_argument("scale", nargs="?", default="1.2"); s.set_defaults(fn=cmd_zoom)
    s = sub.add_parser("fix"); s.add_argument("project"); s.add_argument("index", type=int); s.add_argument("text"); s.set_defaults(fn=cmd_fix)
    s = sub.add_parser("captions"); s.add_argument("project"); s.add_argument("--mode", choices=["editorial_split", "word_pop", "sentence"]); s.add_argument("--zone", help="top | upper | center | chest | lower | pixel y"); s.add_argument("--size"); s.add_argument("--off", action="store_true"); s.add_argument("--on", action="store_true"); s.set_defaults(fn=cmd_captions)
    s = sub.add_parser("cta"); s.add_argument("project"); s.add_argument("kind", choices=["keyword", "share", "follow", "save", "none"]); s.add_argument("value", nargs="?"); s.add_argument("--text"); s.set_defaults(fn=cmd_cta)
    s = sub.add_parser("style"); s.add_argument("project", nargs="?"); s.add_argument("action", nargs="?", default="list"); s.add_argument("target", nargs="?"); s.add_argument("args", nargs="*"); s.set_defaults(fn=cmd_style)
    s = sub.add_parser("music"); s.add_argument("project"); s.add_argument("path"); s.add_argument("--db"); s.set_defaults(fn=cmd_music)
    s = sub.add_parser("speed"); s.add_argument("project"); s.add_argument("value"); s.set_defaults(fn=cmd_speed)
    s = sub.add_parser("cover"); s.add_argument("project"); s.add_argument("time"); s.set_defaults(fn=cmd_cover)
    s = sub.add_parser("endcard"); s.add_argument("project"); s.add_argument("value", choices=["on", "off"]); s.set_defaults(fn=cmd_endcard)
    s = sub.add_parser("render"); s.add_argument("project", nargs="?"); s.add_argument("--proxy", action="store_true"); s.add_argument("--out"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("preview"); s.add_argument("project", nargs="?"); s.add_argument("--port", type=int, default=8765); s.add_argument("--no-open", action="store_true"); s.set_defaults(fn=cmd_preview)
    s = sub.add_parser("repurpose"); s.add_argument("project"); s.add_argument("what", nargs="?", default="all", choices=["carousel", "stories", "trials", "all"]); s.set_defaults(fn=cmd_repurpose)
    s = sub.add_parser("export-project"); s.add_argument("project"); s.set_defaults(fn=cmd_export_project)
    s = sub.add_parser("status"); s.add_argument("project", nargs="?"); s.set_defaults(fn=cmd_status)
    a = ap.parse_args(argv)
    # 'reel style list' / 'reel style new' have no project arg; shuffle
    if a.cmd == "style" and a.project in ("list", "new") and a.action != "new":
        if a.project == "list":
            a.action = "list"
        else:
            a.action, a.target, a.args = "new", a.action, ([a.target] if a.target else []) + list(a.args)
    try:
        a.fn(a)
    except (RuntimeError, FileNotFoundError) as e:
        sys.exit(f"[reel] error: {e}")


if __name__ == "__main__":
    main()
