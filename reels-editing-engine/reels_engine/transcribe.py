"""Word-timestamped transcript. Primary: faster-whisper (runs locally, downloads a model on first use).
Fallbacks: import an SRT/VTT/JSON you already have (e.g. from Descript, CapCut, or Instagram captions).
Never guess the words: if nothing can transcribe, say so and stop."""
import json, re
from pathlib import Path
from .util import log, write_json, read_json, ffmpeg

SENTENCE_END = re.compile(r"[.!?]$")


def extract_audio(video, out_wav):
    ffmpeg(["-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out_wav])
    return out_wav


def transcribe(video, out_json, model_size="small", language=None, device="auto", compute_type="auto", work_dir=None, engine="auto"):
    """engine: auto (faster-whisper, falling back to pocketsphinx when its model cannot be loaded), whisper, or sphinx."""
    work_dir = Path(work_dir or Path(out_json).parent)
    wav = work_dir / "audio16k.wav"
    extract_audio(video, wav)
    if engine in ("auto", "whisper"):
        try:
            return _whisper(wav, out_json, model_size, language, device, compute_type)
        except Exception as e:
            if engine == "whisper":
                raise
            log(f"faster-whisper unavailable ({str(e).splitlines()[0][:140]}); falling back to pocketsphinx (offline, less accurate: check every caption)")
    return _sphinx(wav, out_json)


def _sphinx(wav, out_json):
    try:
        from pocketsphinx import Decoder
    except ImportError:
        raise RuntimeError("no transcriber available: pip install pocketsphinx (offline) or faster-whisper, or import an SRT with reel import-transcript")
    import wave
    log("transcribing with pocketsphinx (bundled offline model)...")
    d = Decoder(logfn="/dev/null" if Path("/dev/null").exists() else None)
    with wave.open(str(wav)) as w:
        data = w.readframes(w.getnframes())
    d.start_utt(); d.process_raw(data, False, True); d.end_utt()
    words = []
    for seg in d.seg():
        tok = seg.word
        if tok.startswith(("<", "[")):
            continue
        tok = re.sub(r"\(\d+\)$", "", tok)
        words.append({"i": len(words), "w": tok, "s": round(seg.start_frame / 100, 3), "e": round(seg.end_frame / 100, 3), "p": round(float(getattr(seg, "prob", 0.5) or 0.5), 2)})
    if not words:
        raise RuntimeError("pocketsphinx heard no words; is the audio audible?")
    data = _finish(words, _segments_from_words(words), source="pocketsphinx", language="en")
    data["needs_review"] = True
    write_json(out_json, data)
    log(f"transcript: {len(words)} words (pocketsphinx). Review transcript.md and fix misheard words with: reel fix")
    return data


def _whisper(wav, out_json, model_size, language, device, compute_type):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed")
    log(f"transcribing with faster-whisper '{model_size}' (first run downloads the model)...")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(wav), word_timestamps=True, language=language, vad_filter=True,
                                      vad_parameters={"min_silence_duration_ms": 250})
    words, segs = [], []
    for seg in segments:
        seg_words = []
        for w in (seg.words or []):
            token = w.word.strip()
            if not token:
                continue
            idx = len(words)
            words.append({"i": idx, "w": token, "s": round(float(w.start), 3), "e": round(float(w.end), 3), "p": round(float(w.probability or 0), 2)})
            seg_words.append(idx)
        segs.append({"s": round(float(seg.start), 3), "e": round(float(seg.end), 3), "text": seg.text.strip(), "words": seg_words})
    data = _finish(words, segs, source="faster-whisper:" + model_size, language=getattr(info, "language", language))
    write_json(out_json, data)
    log(f"transcript: {len(words)} words, {len(segs)} segments, language {data['language']}")
    return data


def import_transcript(path, out_json, duration=None):
    """Import SRT / VTT / JSON (list of {w,s,e} or {words:[...]}) and normalise to our format."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    words = []
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
        items = raw.get("words", raw) if isinstance(raw, dict) else raw
        for it in items:
            w = it.get("w") or it.get("word") or it.get("text")
            s = it.get("s", it.get("start")); e = it.get("e", it.get("end"))
            if w is None or s is None or e is None:
                continue
            for tok in str(w).strip().split():
                words.append({"i": len(words), "w": tok, "s": float(s), "e": float(e), "p": 1.0})
    else:
        # SRT / VTT: cue-level timing; spread words evenly across each cue
        cues = re.findall(r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*\n(.*?)(?:\n\s*\n|\Z)", text, flags=re.S)
        for a, b, body in cues:
            s, e = _ts(a), _ts(b)
            toks = re.sub(r"<[^>]+>", "", body).split()
            if not toks:
                continue
            step = (e - s) / len(toks)
            for k, tok in enumerate(toks):
                words.append({"i": len(words), "w": tok, "s": round(s + k * step, 3), "e": round(s + (k + 1) * step, 3), "p": 0.9})
    if not words:
        raise RuntimeError(f"no words found in {path}")
    data = _finish(words, _segments_from_words(words), source=f"import:{path.name}", language=None)
    write_json(out_json, data)
    log(f"imported transcript: {len(words)} words from {path.name}")
    return data


def _ts(t):
    h, m, s = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _segments_from_words(words, max_gap=0.6, max_words=14):
    segs, cur = [], []
    for w in words:
        if cur and (w["s"] - words[cur[-1]]["e"] > max_gap or len(cur) >= max_words or SENTENCE_END.search(words[cur[-1]]["w"])):
            segs.append(cur); cur = []
        cur.append(w["i"])
    if cur:
        segs.append(cur)
    return [{"s": words[c[0]]["s"], "e": words[c[-1]]["e"], "text": " ".join(words[i]["w"] for i in c), "words": c} for c in segs]


def _finish(words, segs, source, language):
    # sentences: split on terminal punctuation or a gap > 0.7s
    sentences, cur = [], []
    for w in words:
        cur.append(w["i"])
        nxt = words[w["i"] + 1] if w["i"] + 1 < len(words) else None
        if SENTENCE_END.search(w["w"]) or (nxt and nxt["s"] - w["e"] > 0.7):
            sentences.append(cur); cur = []
    if cur:
        sentences.append(cur)
    return {
        "source": source, "language": language or "en",
        "duration": words[-1]["e"] if words else 0,
        "text": " ".join(w["w"] for w in words),
        "words": words, "segments": segs,
        "sentences": [{"words": s, "text": " ".join(words[i]["w"] for i in s), "s": words[s[0]]["s"], "e": words[s[-1]]["e"]} for s in sentences],
    }


def transcript_markdown(data, edit=None):
    """Numbered words so you (or Claude) can say 'cut 12-15' precisely."""
    removed = set((edit or {}).get("removed", [])) | set((edit or {}).get("auto_removed", []))
    kept = set((edit or {}).get("kept", []))
    lines = ["# Transcript (word numbers in brackets, ~~struck~~ = cut)", ""]
    for sent in data["sentences"]:
        parts = []
        for i in sent["words"]:
            w = data["words"][i]
            tok = f"{w['w']}[{i}]"
            if i in removed and i not in kept:
                tok = f"~~{tok}~~"
            parts.append(tok)
        lines.append(f"**{sent['s']:.1f}s** " + " ".join(parts))
        lines.append("")
    return "\n".join(lines)
