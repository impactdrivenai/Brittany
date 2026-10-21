"""Render: graded, cut segments -> concat -> captions + CTA + sound -> end card -> export. Proxy renders (540x960,
fast) power the live preview; final renders are 1080x1920 H.264 at a high bitrate, under Instagram's limits."""
import hashlib, json, shutil
from pathlib import Path
from .util import ffmpeg, run, log, read_json, write_json, W, H, FPS, FONTS_DIR
from .style import load_style
from .cut import build_timeline, auto_removals, describe
from .grade import make_lut, grade_filter, esc
from .captions import build_ass, build_srt
from .graphics import end_card, cta_button, cover
from .sound import plan_sfx, audio_graph

QUALITY = {
    "final": {"w": W, "h": H, "crf": "18", "preset": "medium", "abr": "192k", "maxrate": "16M"},
    "proxy": {"w": 540, "h": 960, "crf": "27", "preset": "veryfast", "abr": "96k", "maxrate": "3M"},
}


def _vcodec(q):
    return ["-c:v", "libx264", "-preset", q["preset"], "-crf", q["crf"], "-maxrate", q["maxrate"], "-bufsize", "32M",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-r", str(FPS), "-g", str(FPS * 2),
            "-c:a", "aac", "-b:a", q["abr"], "-ar", "48000", "-ac", "2", "-movflags", "+faststart"]


def resolve_style(project):
    return load_style(project.data.get("style", "butter"), {})


def timeline_for(project, style=None):
    style = style or resolve_style(project)
    tr = project.transcript()
    if tr is None:
        raise RuntimeError("no transcript yet. Run: reel transcribe <project>  (or reel import-transcript)")
    edit = project.data["edit"]
    if edit.get("auto_removed") is None:
        edit["auto_removed"] = auto_removals(tr["words"], style["cut"])
    return build_timeline(tr, edit, style["cut"], project.data["info"]["duration"]), tr, style


def _seg_key(seg, speed, q, gfilter, src):
    raw = json.dumps([seg["src_start"], seg["src_end"], seg["zoom"], speed, q["w"], q["h"], q["crf"], gfilter, str(src)], sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def render_segments(project, timeline, style, quality, work):
    q = QUALITY[quality]
    info = project.data["info"]
    lut = make_lut(style["grade"].get("look", "clean"), work / f"look-{style['grade'].get('look','clean')}.cube")
    gstyle = style
    if quality == "proxy":   # preview renders skip the slow texture passes (denoise, grain); LUT and vignette stay
        gstyle = dict(style); gstyle["grade"] = dict(style["grade"], denoise=False, grain=0)
    gfilter = grade_filter(gstyle, lut)
    speed = timeline["speed"]
    segdir = work / f"segments-{quality}"; segdir.mkdir(exist_ok=True)
    paths, jobs = [], []
    for n, seg in enumerate(timeline["edl"]):
        key = _seg_key(seg, speed, q, gfilter, project.raw.name)
        out = segdir / f"seg-{key}.mp4"
        paths.append(out)
        if out.exists():
            continue
        jobs.append((n, seg, out))
    # prune stale segments so the work folder does not grow forever
    keep = {p.name for p in paths}
    for old in segdir.glob("seg-*.mp4"):
        if old.name not in keep:
            old.unlink(missing_ok=True)

    def encode(job):
        n, seg, out = job
        vf = [f"scale={q['w']}:{q['h']}:force_original_aspect_ratio=increase", f"crop={q['w']}:{q['h']}"]
        z = float(seg.get("zoom", 1.0))
        if z > 1.001:
            vf.append(f"crop=iw/{z:.4f}:ih/{z:.4f}")
            vf.append(f"scale={q['w']}:{q['h']}")
        if gfilter:
            vf.append(gfilter)
        if abs(speed - 1.0) > 1e-3:
            vf.append(f"setpts=PTS/{speed:.4f}")
        vf += [f"fps={FPS}", "format=yuv420p"]
        af = []
        if abs(speed - 1.0) > 1e-3:
            af.append(f"atempo={speed:.4f}")
        af += ["aresample=48000", "aformat=channel_layouts=stereo"]
        args = ["-ss", f"{seg['src_start']:.3f}", "-to", f"{seg['src_end']:.3f}", "-i", project.raw]
        if not info.get("has_audio", True):
            args += ["-f", "lavfi", "-t", f"{seg['src_end'] - seg['src_start']:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        tmp = out.with_name(out.stem + ".part.mp4")
        args += ["-vf", ",".join(vf), "-af", ",".join(af), "-shortest", *_vcodec(q), tmp]
        ffmpeg(args)
        tmp.rename(out)
        log(f"segment {n + 1}/{len(timeline['edl'])} rendered")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2 if quality == "final" else 3) as ex:
        list(ex.map(encode, jobs))
    return paths


def concat(paths, out, work=None):
    lst = (work or out.parent) / (out.stem + "-list.txt")
    with open(lst, "w") as f:
        for p in paths:
            f.write(f"file '{Path(p).resolve().as_posix()}'\n")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out])
    return out


def extract_frame(video, t, out):
    ffmpeg(["-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1", "-q:v", "2", out])
    return out


def still_clip(png, duration, out, quality, sfx=None):
    q = QUALITY[quality]
    args = ["-loop", "1", "-t", f"{duration:.2f}", "-i", png]
    if sfx:
        args += ["-i", sfx]
        fc = f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.25,apad[a];[0:v]scale={q['w']}:{q['h']},fps={FPS},format=yuv420p[v]"
    else:
        args += ["-f", "lavfi", "-t", f"{duration:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        fc = f"[1:a]anull[a];[0:v]scale={q['w']}:{q['h']},fps={FPS},format=yuv420p[v]"
    ffmpeg([*args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{duration:.2f}", *_vcodec(q), out])
    return out


def render(project, quality="final", out_name=None):
    q = QUALITY[quality]
    work = project.work
    timeline, tr, style = timeline_for(project)
    project.save()
    log(f"timeline: {describe(timeline, tr)}")
    write_json(work / "timeline.json", timeline)

    segs = render_segments(project, timeline, style, quality, work)
    cut_mp4 = concat(segs, work / f"cut-{quality}.mp4")

    # captions
    cap_cfg = project.data.get("captions", {})
    ass_path, n_caps = build_ass(tr, timeline, style, cap_cfg, work / "captions.ass")
    build_srt(tr, timeline, cap_cfg, project.exports / "captions.srt")

    # CTA overlay
    cta = project.data.get("cta", {}) or {}
    cta_png = None
    dur = timeline["duration"]
    cta_s = float(style["cta"].get("seconds", 2.5))
    if cta.get("type") == "keyword" and cta.get("keyword"):
        text = cta.get("text") or style["cta"]["template"].format(keyword=cta["keyword"])
        cta_png = cta_button(style, text, cta["keyword"], project.overlays / "cta.png")
    elif cta.get("type") in ("share", "follow", "save") and cta.get("text"):
        cta_png = cta_button(style, cta["text"], "", project.overlays / "cta.png")

    # sound
    sfx_plan = plan_sfx(timeline, tr, style)
    music = project.data.get("music")
    music_path = Path(music).expanduser() if music else None
    if music_path and not music_path.is_absolute():
        music_path = project.dir / music_path
    if music_path and not music_path.exists():
        log(f"warning: music file not found: {music_path}; rendering without music")
        music_path = None

    inputs = ["-i", cut_mp4]
    n_in = 1
    cta_idx = None
    if cta_png:
        inputs += ["-loop", "1", "-i", cta_png]; cta_idx = n_in; n_in += 1
    sfx_off = n_in
    for s in sfx_plan:
        inputs += ["-i", s["file"]]; n_in += 1
    music_idx = None
    if music_path:
        inputs += ["-stream_loop", "-1", "-i", music_path]; music_idx = n_in; n_in += 1

    vparts = []
    v = "0:v"
    if cap_cfg.get("enabled", True) and n_caps:
        vparts.append(f"[{v}]ass=filename='{esc(ass_path)}':fontsdir='{esc(FONTS_DIR)}'[vcap]"); v = "vcap"
    if cta_idx is not None:
        vparts.append(f"[{cta_idx}:v]scale={q['w']}:{q['h']},format=rgba[ctapng]")
        vparts.append(f"[{v}][ctapng]overlay=0:0:enable='between(t,{max(0, dur - cta_s):.2f},{dur + 1:.2f})':shortest=1[vcta]"); v = "vcta"
    if not vparts:
        vparts.append(f"[{v}]null[vout]"); v = "vout"
    agraph, aout = audio_graph(style, "0:a", sfx_plan, sfx_off, music_idx, dur, project.data.get("music_db_under_voice"))
    fc = ";".join(vparts + [agraph])
    main_mp4 = work / f"main-{quality}.mp4"
    ffmpeg([*inputs, "-filter_complex", fc, "-map", f"[{v}]", "-map", f"[{aout}]", "-t", f"{dur:.3f}", *_vcodec(q), main_mp4])
    log("captions, CTA and sound mixed")

    # end card
    ec_on = project.data.get("end_card")
    if ec_on is None:
        ec_on = style["end_card"].get("enabled", False)
    final_parts = [main_mp4]
    if ec_on and style["end_card"].get("line1"):
        png = end_card(style, project.overlays / "end-card.png")
        from .sfx import bank
        pop = next((f for f in bank(banned=style["sound"].get("banned", [])) if f.stem.startswith(style["end_card"].get("sfx", "pop-soft"))), None)
        ec_mp4 = still_clip(png, float(style["end_card"].get("duration", 1.5)), work / f"endcard-{quality}.mp4", quality, pop)
        final_parts.append(ec_mp4)

    name = out_name or (f"{project.data['name']}.mp4" if quality == "final" else "preview.mp4")
    final = project.exports / name
    if len(final_parts) > 1:
        concat(final_parts, final, work)
    else:
        shutil.copy2(main_mp4, final)

    # cover + notes
    hook_t = project.data.get("cover_time")
    if hook_t is None:
        first = min(timeline["word_out"].values(), key=lambda v: v["s"]) if timeline["word_out"] else {"s": 0.3}
        hook_t = first["s"] + 0.35
    frame = extract_frame(cut_mp4, hook_t, work / "cover-frame.jpg")
    cover(frame, first_phrase(tr, timeline), style, project.exports / "cover.jpg")
    _write_notes(project, timeline, tr, style, sfx_plan, final, quality)
    size_mb = final.stat().st_size / 1e6
    log(f"exported {final} ({size_mb:.1f} MB, {dur + (1.5 if len(final_parts) > 1 else 0):.1f}s)")
    return final


def first_phrase(tr, timeline, n=10):
    """The opening line of the cut (first kept sentence, capped at n words) for covers and notes."""
    ws = sorted(((int(i), v["s"]) for i, v in timeline["word_out"].items()), key=lambda t: t[1])
    if not ws:
        return ""
    first = ws[0][0]
    sent = next((s for s in tr["sentences"] if first in s["words"]), None)
    kept = [i for i in (sent["words"] if sent else [i for i, _ in ws]) if i in timeline["word_out"] or str(i) in timeline["word_out"]]
    return " ".join(tr["words"][i]["w"] for i in kept[:n])


def _write_notes(project, timeline, tr, style, sfx_plan, final, quality):
    removed = timeline["removed"]
    lines = [f"# Cut notes: {project.data['name']}", "",
             f"- Style pack: **{style['name']}** ({style.get('label','')})",
             f"- Output: `{final.name}` ({quality}), {timeline['duration']:.1f}s, {len(timeline['edl'])} segments, speed {timeline['speed']:.2f}",
             f"- Words kept: {timeline['kept_count']}  |  words cut: {len(removed)}",
             f"- Hook: {first_phrase(tr, timeline, 10)}",
             f"- CTA: {json.dumps(project.data.get('cta'))}",
             f"- Grade look: {style['grade'].get('look')}  |  captions: {project.data.get('captions',{}).get('mode') or style['captions']['mode']}",
             "", "## Sound effects used", ""]
    lines += [f"- {s['t']:.1f}s  {s['file'].name}  ({s['event']})" for s in sfx_plan] or ["- none"]
    lines += ["", "## Words cut", "", " ".join(f"~~{tr['words'][i]['w']}~~[{i}]" for i in removed) or "none"]
    (project.exports / "cut-notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
