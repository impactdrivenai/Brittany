import json
from .util import run


def probe(path):
    res = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    data = json.loads(res.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    info = {
        "duration": float(data["format"].get("duration", 0) or 0),
        "width": int(v["width"]) if v else 0,
        "height": int(v["height"]) if v else 0,
        "fps": _fps(v.get("r_frame_rate", "30/1")) if v else 30.0,
        "rotation": _rotation(v) if v else 0,
        "has_audio": a is not None,
        "size_mb": round(int(data["format"].get("size", 0)) / 1e6, 1),
    }
    if info["rotation"] in (90, 270, -90):
        info["width"], info["height"] = info["height"], info["width"]
    return info


def _fps(rate):
    try:
        n, d = rate.split("/")
        return round(float(n) / float(d), 3)
    except Exception:
        return 30.0


def _rotation(v):
    rot = 0
    tags = v.get("tags", {}) or {}
    if "rotate" in tags:
        try: rot = int(tags["rotate"])
        except Exception: rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            try: rot = int(round(float(sd["rotation"])))
            except Exception: pass
    return rot % 360
