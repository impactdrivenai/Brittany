"""Live editor: a tiny local web page. Click words, tap Cut, and the reel re-renders while you watch.
Every change lands on the preview automatically (proxy quality); hit Render final when it feels right."""
import json, threading, time, traceback, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from .util import TEMPLATES_DIR, log, read_json
from .project import Project


class State:
    def __init__(self, project):
        self.project = project
        self.lock = threading.Lock()
        self.dirty = True
        self.rendering = False
        self.last_error = None
        self.last_log = "waiting"
        self.version = 0
        self.final_requested = False

    def touch(self):
        with self.lock:
            self.dirty = True


def render_loop(state):
    from .render import render
    while True:
        time.sleep(0.4)
        with state.lock:
            if not state.dirty or state.rendering:
                continue
            state.dirty = False
            state.rendering = True
            final = state.final_requested
            state.final_requested = False
        try:
            state.last_log = "rendering final..." if final else "rendering preview..."
            # reload project from disk so CLI edits made in another terminal are picked up too
            proj = Project(state.project.dir)
            state.project = proj
            out = render(proj, quality="final" if final else "proxy")
            state.version = int(Path(out).stat().st_mtime)
            state.last_error = None
            state.last_log = f"{'final' if final else 'preview'} ready: {Path(out).name}"
        except Exception as e:
            state.last_error = str(e)[-1500:]
            state.last_log = "render failed"
            traceback.print_exc()
        finally:
            with state.lock:
                state.rendering = False


def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, data, code=200):
            body = json.dumps(data).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            p = self.project = state.project
            path = self.path.split("?")[0]
            if path == "/":
                html = (TEMPLATES_DIR / "preview.html").read_text(encoding="utf-8")
                body = html.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif path == "/api/state":
                tr = p.transcript() or {"words": [], "sentences": []}
                ed = p.data["edit"]
                removed = (set(ed["removed"]) | set(ed.get("auto_removed") or [])) - set(ed.get("kept", []))
                tl = read_json(p.work / "timeline.json", {})
                preview = p.exports / "preview.mp4"
                self._json({
                    "name": p.data["name"], "style": p.data["style"], "dir": str(p.dir),
                    "words": [{"i": w["i"], "w": w["w"], "s": w["s"], "removed": w["i"] in removed} for w in tr["words"]],
                    "sentences": [s["words"] for s in tr.get("sentences", [])],
                    "edit": ed, "captions": p.data["captions"], "cta": p.data["cta"],
                    "duration": tl.get("duration"), "segments": len(tl.get("edl", [])),
                    "video": {"exists": preview.exists(), "version": int(preview.stat().st_mtime) if preview.exists() else 0},
                    "rendering": state.rendering, "dirty": state.dirty, "log": state.last_log, "error": state.last_error,
                    "styles": [n for n, _ in __import__("reels_engine.style", fromlist=["list_styles"]).list_styles()],
                })
            elif path == "/video":
                f = p.exports / "preview.mp4"
                if not f.exists():
                    self.send_response(404); self.end_headers(); return
                self._send_file(f, "video/mp4")
            elif path == "/cover":
                f = p.exports / "cover.jpg"
                if not f.exists():
                    self.send_response(404); self.end_headers(); return
                self._send_file(f, "image/jpeg")
            else:
                self.send_response(404); self.end_headers()

        def _send_file(self, f, ctype):
            size = f.stat().st_size
            rng = self.headers.get("Range")
            start, end = 0, size - 1
            if rng and rng.startswith("bytes="):
                a, _, b = rng[6:].partition("-")
                start = int(a or 0); end = int(b) if b else size - 1
                end = min(end, size - 1)
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.send_response(200)
            self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(end - start + 1)); self.send_header("Cache-Control", "no-store"); self.end_headers()
            with open(f, "rb") as fh:
                fh.seek(start); remaining = end - start + 1
                while remaining > 0:
                    chunk = fh.read(min(1 << 16, remaining))
                    if not chunk: break
                    try: self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError): return
                    remaining -= len(chunk)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            p = Project(state.project.dir)   # fresh read, then write
            ed = p.data["edit"]
            try:
                act = self.path
                if act == "/api/cut":
                    idx = set(int(i) for i in body.get("indices", []))
                    ed["removed"] = sorted(set(ed["removed"]) | idx); ed["kept"] = [k for k in ed["kept"] if k not in idx]
                elif act == "/api/restore":
                    idx = set(int(i) for i in body.get("indices", []))
                    ed["removed"] = [i for i in ed["removed"] if i not in idx]
                    ed["kept"] = sorted(set(ed["kept"]) | (idx & set(ed.get("auto_removed") or [])))
                elif act == "/api/hook":
                    ed["hook"] = body.get("range")
                elif act == "/api/zoom":
                    if body.get("clear"): ed["zooms"] = []
                    else: ed["zooms"].append({"start": float(body["start"]), "end": float(body["end"]), "scale": float(body.get("scale", 1.2))})
                elif act == "/api/speed":
                    ed["speed"] = float(body["speed"]) if body.get("speed") else None
                elif act == "/api/style":
                    p.data["style"] = body["style"]
                elif act == "/api/captions":
                    for k in ("mode", "zone", "size", "enabled"):
                        if k in body: p.data["captions"][k] = body[k]
                elif act == "/api/fix":
                    p.data["captions"].setdefault("fixes", {})[str(int(body["index"]))] = body["text"]
                elif act == "/api/cta":
                    p.data["cta"] = {"type": body.get("type") or None, "keyword": (body.get("keyword") or "").upper() or None, "text": body.get("text") or None}
                elif act == "/api/render":
                    with state.lock:
                        state.final_requested = True
                else:
                    self._json({"ok": False, "error": "unknown action"}, 404); return
                p.save()
                state.project = p
                state.touch()
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 400)
    return H


def serve(project, port=8765, open_browser=True):
    state = State(project)
    t = threading.Thread(target=render_loop, args=(state,), daemon=True); t.start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state))
    url = f"http://127.0.0.1:{port}/"
    log(f"live editor at {url}  (Ctrl+C to stop). Edits re-render the preview automatically.")
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("stopped")
