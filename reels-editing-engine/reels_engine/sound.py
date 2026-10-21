"""Sound: voice chain (her voice is the product), sound effects timed to visual events (felt, not heard, never the
same one twice, never the whoosh), and an optional music bed ducked under every spoken line."""
import math, random
from .sfx import bank, pick_for
from .captions import NUM


def voice_chain(style):
    lufs = style["sound"].get("voice_lufs", -14)
    return (f"highpass=f=80,afftdn=nf=-25:nr=10,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=140:makeup=2,"
            f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000")


def plan_sfx(timeline, transcript, style, seed=7):
    """Return [{'t': out_seconds, 'file': Path, 'event': str}] respecting the style's cadence."""
    snd = style["sound"]
    mode = snd.get("sfx", "light")
    lo, hi = snd.get("sfx_every", [8, 10])
    if mode == "none" or not lo:
        return []
    files = bank(banned=[b.lower() for b in snd.get("banned", [])])
    if not files:
        return []
    # visual events in output time
    events = []
    for seg in timeline["edl"][1:]:
        events.append((seg["out_start"], "cut"))
    for i, v in timeline["word_out"].items():
        w = transcript["words"][int(i)]["w"]
        if NUM.search(w):
            events.append((v["s"], "number"))
    events.sort()
    rnd = random.Random(seed)
    plan, used = [], []
    t_next = rnd.uniform(lo * 0.5, hi * 0.6)   # first hit lands early but not on frame 0
    for t, kind in events:
        if t < t_next:
            continue
        f = pick_for(kind, files, used)
        if f is None:
            used = []  # bank exhausted: allow reuse, still never back-to-back
            f = pick_for(kind, files, used)
        used.append(f)
        plan.append({"t": round(t, 3), "file": f, "event": kind})
        t_next = t + rnd.uniform(lo, hi)
    return plan


def db_to_gain(db):
    return 10 ** (-abs(db) / 20)


def audio_graph(style, voice_label, sfx_plan, sfx_input_offset, music_index=None, duration=None, music_db=None, has_voice=True):
    """Build the audio half of a filter_complex. Inputs: [0:a] voice; sfx inputs start at sfx_input_offset; music at music_index.
    Returns (filter_string, out_label)."""
    parts = []
    parts.append(f"[{voice_label}]{voice_chain(style)}[voice]")
    mix_inputs = []
    if music_index is not None:
        parts.append("[voice]asplit=2[v_main][v_sc]")
        mdb = music_db if music_db is not None else style["sound"].get("music_db_under_voice", 20)
        fade_st = max(0.0, (duration or 30) - 1.2)
        parts.append(f"[{music_index}:a]aresample=48000,atrim=0:{duration or 30},volume={db_to_gain(mdb):.3f},afade=t=out:st={fade_st:.2f}:d=1.2[m0]")
        parts.append("[m0][v_sc]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=450:makeup=1[music]")
        mix_inputs += ["[v_main]", "[music]"]
    else:
        mix_inputs.append("[voice]")
    g = db_to_gain(style["sound"].get("sfx_db_under_voice", 15))
    for k, s in enumerate(sfx_plan):
        idx = sfx_input_offset + k
        ms = int(s["t"] * 1000)
        parts.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g:.3f},adelay={ms}|{ms}[s{k}]")
        mix_inputs.append(f"[s{k}]")
    if len(mix_inputs) == 1:
        parts.append(f"{mix_inputs[0]}anull[aout]")
    else:
        parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0:dropout_transition=0[aout]")
    return ";".join(parts), "aout"
