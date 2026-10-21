"""One folder per reel: raw/, transcript, cut plan, overlays, exports. project.json holds every decision."""
import datetime, shutil
from pathlib import Path
from .util import REELS_DIR, read_json, write_json, slugify, log
from .probe import probe

DEFAULT_PROJECT = {
    "name": "", "source": "", "style": "brittany", "created": "",
    "info": {},
    "edit": {
        "removed": [],            # word indices cut by hand (or by auto rules, see auto_removed)
        "auto_removed": [],       # indices removed by filler/stutter rules (kept separate so you can restore)
        "kept": [],               # indices you force-keep even if a rule would cut them
        "hook": None,             # [start_idx, end_idx] moved to the front
        "trim_dead_air": True,
        "speed": None,            # overrides style cut.speed when set
        "zooms": [],              # [{"start": s, "end": e, "scale": 1.2}] in OUTPUT seconds
        "mutes": []               # [[start, end]] output seconds where voice is silenced (optional)
    },
    "captions": {"enabled": True, "mode": None, "zone": None, "size": None, "fixes": {}},  # fixes: {"idx": "correct word"}
    "cta": {"keyword": None, "text": None, "type": None},   # type: keyword | follow | share | none
    "cover_time": None,
    "music": None,
    "music_db_under_voice": None,
    "end_card": None,            # None = per style; true/false overrides
    "notes": ""
}


class Project:
    def __init__(self, path):
        self.dir = Path(path)
        self.file = self.dir / "project.json"
        self.data = read_json(self.file)
        if self.data is None:
            raise FileNotFoundError(f"no project.json in {self.dir}. Run: reel new <video> first")
        for k, v in DEFAULT_PROJECT.items():
            self.data.setdefault(k, v if not isinstance(v, dict) else dict(v))
        for k, v in DEFAULT_PROJECT["edit"].items():
            self.data["edit"].setdefault(k, v)

    # paths
    @property
    def raw(self): return self.dir / self.data["source"]
    @property
    def transcript_file(self): return self.dir / "transcript.json"
    @property
    def work(self): p = self.dir / "work"; p.mkdir(exist_ok=True); return p
    @property
    def overlays(self): p = self.dir / "overlays"; p.mkdir(exist_ok=True); return p
    @property
    def exports(self): p = self.dir / "exports"; p.mkdir(exist_ok=True); return p

    def save(self):
        write_json(self.file, self.data)

    def transcript(self):
        return read_json(self.transcript_file)

    @staticmethod
    def create(video, name=None, style="brittany", reels_dir=None):
        video = Path(video).expanduser().resolve()
        if not video.exists():
            raise FileNotFoundError(video)
        root = Path(reels_dir) if reels_dir else REELS_DIR
        slug = slugify(name or video.stem)
        day = datetime.date.today().isoformat()
        folder = root / f"{day}-{slug}"
        n = 2
        while folder.exists():
            folder = root / f"{day}-{slug}-{n}"; n += 1
        (folder / "raw").mkdir(parents=True)
        dest = folder / "raw" / ("original" + video.suffix.lower())
        shutil.copy2(video, dest)   # always work on a copy, never the original
        info = probe(dest)
        data = dict(DEFAULT_PROJECT)
        data.update({"name": slug, "source": f"raw/{dest.name}", "style": style, "created": day, "info": info})
        data["edit"] = dict(DEFAULT_PROJECT["edit"])
        write_json(folder / "project.json", data)
        log(f"project created: {folder}  ({info['width']}x{info['height']}, {info['duration']:.1f}s, {info['size_mb']} MB)")
        return Project(folder)


def find_project(path_or_name):
    p = Path(path_or_name)
    if (p / "project.json").exists():
        return Project(p)
    if REELS_DIR.exists():
        matches = sorted(REELS_DIR.glob(f"*{path_or_name}*"))
        matches = [m for m in matches if (m / "project.json").exists()]
        if len(matches) == 1:
            return Project(matches[0])
        if len(matches) > 1:
            return Project(matches[-1])
    raise FileNotFoundError(f"no reel project matching '{path_or_name}' (looked in {REELS_DIR})")


def latest_project():
    if not REELS_DIR.exists():
        return None
    cands = sorted([p for p in REELS_DIR.iterdir() if (p / "project.json").exists()], key=lambda p: p.stat().st_mtime)
    return Project(cands[-1]) if cands else None
