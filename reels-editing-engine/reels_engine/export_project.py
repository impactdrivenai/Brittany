"""Editable hand-off: a clean graded cut (no captions burned in), the captions as SRT and ASS, an EDL of every cut
back to the original footage, the overlays as PNG, and the style tokens. Open it in CapCut, Premiere, DaVinci or
Final Cut and keep tweaking; nothing is locked inside this tool."""
import json, shutil
from pathlib import Path
from .util import log, write_json, FPS
from .render import timeline_for, render_segments, concat
from .captions import build_srt, build_ass
from .graphics import cta_button, end_card


def _tc(seconds):
    f = int(round(seconds * FPS))
    return f"{f // (3600*FPS):02d}:{(f // (60*FPS)) % 60:02d}:{(f // FPS) % 60:02d}:{f % FPS:02d}"


def export_project(project):
    timeline, tr, style = timeline_for(project)
    out = project.exports / "editable"; out.mkdir(parents=True, exist_ok=True)
    segs = render_segments(project, timeline, style, "final", project.work)
    concat(segs, out / "clean-cut.mp4", project.work)
    build_srt(tr, timeline, project.data.get("captions", {}), out / "captions.srt")
    build_ass(tr, timeline, style, project.data.get("captions", {}), out / "captions.ass")
    shutil.copy2(project.raw, out / project.raw.name) if False else None  # original stays in raw/; EDL points at it
    lines = [f"TITLE: {project.data['name']}", "FCM: NON-DROP FRAME", ""]
    for n, seg in enumerate(timeline["edl"], 1):
        lines.append(f"{n:03d}  AX       V     C        {_tc(seg['src_start'])} {_tc(seg['src_end'])} {_tc(seg['out_start'])} {_tc(seg['out_end'])}")
        lines.append(f"* FROM CLIP NAME: {project.raw.name}")
        if seg.get("zoom", 1.0) > 1.001:
            lines.append(f"* ZOOM: {seg['zoom']:.2f}")
        lines.append("")
    (out / "cuts.edl").write_text("\n".join(lines), encoding="utf-8")
    write_json(out / "timeline.json", timeline)
    write_json(out / "style-tokens.json", {"colors": style["colors"], "fonts": style["fonts"], "captions": style["captions"], "end_card": style["end_card"], "cta": style["cta"]})
    cta = project.data.get("cta") or {}
    if cta.get("type") == "keyword" and cta.get("keyword"):
        cta_button(style, cta.get("text") or style["cta"]["template"].format(keyword=cta["keyword"]), cta["keyword"], out / "cta-overlay.png")
    if style["end_card"].get("line1"):
        end_card(style, out / "end-card.png")
    (out / "README.md").write_text(f"""# Editable hand-off: {project.data['name']}

- `clean-cut.mp4` — the cut, graded, 1080x1920, no captions or overlays burned in. Drop this on your timeline.
- `captions.srt` — captions with the final timing. CapCut: Text > Captions > Import (or use Auto captions and paste from here). Premiere / DaVinci / Final Cut import SRT directly.
- `captions.ass` — the styled captions (fonts, colours, animation) for players and tools that read ASS.
- `cuts.edl` — every cut mapped back to `raw/{project.raw.name}` (CMX3600, 30 fps) so an editor can reconform from the original.
- `cta-overlay.png`, `end-card.png` — the overlays as transparent / flat PNGs, drop them on a track above the video.
- `style-tokens.json` — colours and fonts of the look, so anything you add matches.
- `timeline.json` — the full edit decision list with word timings, for any tool that wants it.

Fonts live in `{Path(__file__).resolve().parent.parent / 'fonts'}` — install them on your machine so CapCut and others can use the same type.
""", encoding="utf-8")
    log(f"editable hand-off in {out}")
    return out
