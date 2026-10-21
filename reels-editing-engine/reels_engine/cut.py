"""Word-level cutting. The transcript is the timeline: strike words, the video follows.

Builds an EDL (list of source ranges in output order) from:
  * auto rules: filler words, stutters, dead air between words, leading/trailing silence
  * your word cuts (removed indices) and force-keeps
  * a hook range moved to the front
  * jump-cut punch-ins (alternate 1.0 / punch_scale at every cut so jumps read as intentional)
  * manual zooms in output time
Also maps every kept word to its OUTPUT time so captions land exactly on the voice."""
import re
from .util import log

WORD_RE = re.compile(r"[^a-z0-9']+")


def norm(w):
    return WORD_RE.sub("", w.lower())


def auto_removals(words, style_cut):
    """Indices removed by rules. Fillers always; stutters (same word twice in a row within 0.6s) when enabled."""
    fillers = set(style_cut.get("fillers", []))
    out = set()
    prev = None
    for w in words:
        n = norm(w["w"])
        if n in fillers:
            out.add(w["i"])
        elif style_cut.get("cut_stutters", True) and prev is not None and n and n == norm(prev["w"]) and w["s"] - prev["e"] < 0.6:
            out.add(prev["i"])  # drop the first of the pair, keep the clean second take
        prev = w
    return sorted(out)


def build_timeline(transcript, edit, style_cut, source_duration):
    words = transcript["words"]
    removed = (set(edit.get("removed", [])) | set(edit.get("auto_removed", []))) - set(edit.get("kept", []))
    kept = [w for w in words if w["i"] not in removed]
    if not kept:
        raise RuntimeError("every word is cut; restore something")

    max_pause = float(style_cut.get("max_pause", 0.35))
    keep_pause = float(style_cut.get("keep_pause", 0.12))
    pad_in, pad_out = 0.06, 0.10
    trim_dead = edit.get("trim_dead_air", True)

    # 1) group kept words into contiguous runs in SOURCE order; a run breaks when a removed word sits between
    #    two kept words or when the gap is long enough to count as dead air.
    runs, cur = [], [kept[0]]
    for prev, w in zip(kept, kept[1:]):
        gap = w["s"] - prev["e"]
        word_cut_between = w["i"] != prev["i"] + 1
        if word_cut_between or (trim_dead and gap > max_pause):
            runs.append(cur); cur = [w]
        else:
            cur.append(w)
    runs.append(cur)

    # 2) each run -> source range with small pads; trim long pauses inside to keep_pause
    def run_range(run):
        s = max(0.0, run[0]["s"] - pad_in)
        e = min(source_duration, run[-1]["e"] + pad_out)
        return s, e

    # 3) hook: the run(s) covering hook word indices go first
    hook = edit.get("hook")
    hook_set = set(range(hook[0], hook[1] + 1)) if hook else set()
    hook_runs, other_runs = [], []
    for run in runs:
        idxs = {w["i"] for w in run}
        if hook_set and idxs & hook_set:
            inside = [w for w in run if w["i"] in hook_set]
            outside = [w for w in run if w["i"] not in hook_set]
            if inside:
                hook_runs.append(inside)
            if outside:
                # keep the pieces before/after the hook in their place (split at hook)
                before = [w for w in outside if w["i"] < min(hook_set)]
                after = [w for w in outside if w["i"] > max(hook_set)]
                if before: other_runs.append(before)
                if after: other_runs.append(after)
        else:
            other_runs.append(run)
    ordered = hook_runs + other_runs

    # 4) EDL with output times, speed, punch-ins, and sub-run gap trimming
    speed = float(edit.get("speed") or style_cut.get("speed") or 1.0)
    punch = bool(style_cut.get("jump_cut_punch", True))
    punch_scale = float(style_cut.get("punch_scale", 1.12))
    min_seg = float(style_cut.get("min_segment", 0.25))
    edl, word_out = [], {}
    t_out = 0.0
    toggle = False
    for run in ordered:
        # split a run further where an internal pause exceeds keep_pause*2 (tighten pauses inside sentences)
        pieces, cur = [], [run[0]]
        for prev, w in zip(run, run[1:]):
            if trim_dead and (w["s"] - prev["e"]) > max(keep_pause * 2.5, 0.3):
                pieces.append(cur); cur = [w]
            else:
                cur.append(w)
        pieces.append(cur)
        for k, piece in enumerate(pieces):
            s, e = run_range(piece)
            if k > 0:
                s = max(0.0, piece[0]["s"] - keep_pause)   # re-enter with a short breath
            if e - s < min_seg:
                e = min(source_duration, s + min_seg)
            dur = (e - s) / speed
            seg = {"src_start": round(s, 3), "src_end": round(e, 3), "out_start": round(t_out, 3), "out_end": round(t_out + dur, 3),
                   "zoom": punch_scale if (punch and toggle) else 1.0, "words": [w["i"] for w in piece]}
            toggle = not toggle
            for w in piece:
                word_out[w["i"]] = {"s": round(t_out + (w["s"] - s) / speed, 3), "e": round(t_out + (w["e"] - s) / speed, 3)}
            edl.append(seg)
            t_out += dur

    # 5) manual zooms override punch zoom on the segments they cover (split segments at zoom edges)
    for z in edit.get("zooms", []) or []:
        edl = _apply_zoom(edl, float(z["start"]), float(z["end"]), float(z.get("scale", 1.2)), speed)

    return {"edl": edl, "duration": round(t_out, 3), "word_out": word_out, "speed": speed,
            "removed": sorted(removed), "kept_count": len(kept)}


def _apply_zoom(edl, zs, ze, scale, speed):
    out = []
    for seg in edl:
        a, b = seg["out_start"], seg["out_end"]
        if ze <= a or zs >= b:
            out.append(seg); continue
        cuts = sorted({a, b, max(a, zs), min(b, ze)})
        for p, q in zip(cuts, cuts[1:]):
            if q - p < 0.02:
                continue
            frac_p, frac_q = (p - a) / (b - a), (q - a) / (b - a)
            sub = dict(seg)
            sub["out_start"], sub["out_end"] = round(p, 3), round(q, 3)
            sub["src_start"] = round(seg["src_start"] + frac_p * (seg["src_end"] - seg["src_start"]), 3)
            sub["src_end"] = round(seg["src_start"] + frac_q * (seg["src_end"] - seg["src_start"]), 3)
            if p >= zs - 1e-6 and q <= ze + 1e-6:
                sub["zoom"] = scale
            sub["words"] = [i for i in seg["words"]]
            out.append(sub)
    return out


def hook_candidates(transcript, top=3):
    """Rank sentences as hooks: names the viewer ('you'), a number, a question, a contrast word, short."""
    scored = []
    warmups = {"okay", "ok", "so", "hey", "hi", "um", "uh", "alright", "welcome", "guys", "everyone", "and", "like"}
    starts = {}
    for k, s in enumerate(transcript["sentences"]):
        idxs = list(s["words"])
        while len(idxs) > 2 and norm(transcript["words"][idxs[0]]["w"]) in warmups:
            idxs.pop(0)   # a hook never starts with a warm-up word
        starts[k] = idxs
        t = " ".join(transcript["words"][i]["w"] for i in idxs).lower()
        n = len(idxs)
        score = 0.0
        score += 2.0 if re.search(r"\byou\b|\byour\b", t) else 0
        score += 1.5 if re.search(r"\d", t) else 0
        score += 1.5 if "?" in t else 0
        score += 1.0 if re.search(r"\b(nobody|never|stop|secret|lie|mistake|wrong|actually|truth|hate|every)\b", t) else 0
        score += 1.0 if re.search(r"\b(2pm|monday|tuesday|wednesday|thursday|friday|morning|tonight|today)\b", t) else 0
        score -= 0.08 * max(0, n - 14)                                                     # too long to land in 1.5s
        score -= 1.0 if n < 3 else 0
        scored.append((score, k))
    scored.sort(reverse=True)
    return [{"sentence": k, "score": round(sc, 2), "text": " ".join(transcript["words"][i]["w"] for i in starts[k]),
             "range": [starts[k][0], starts[k][-1]]} for sc, k in scored[:top]]


def describe(timeline, transcript):
    n = len(timeline["edl"])
    return (f"{timeline['duration']:.1f}s, {n} segments, {timeline['kept_count']} words kept, "
            f"{len(timeline['removed'])} words cut, speed {timeline['speed']:.2f}")
