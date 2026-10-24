"""Turn a saved Google Drive `download_file_content` tool result (JSON with base64 `content`) into a real file.
Large Drive downloads in Claude Code cloud sessions land in a tool-results .txt file instead of the chat; this
decodes that file so `reel new` can take it.   usage: python3 drive_result_to_file.py <tool-result.txt> <out-dir>"""
import base64, json, sys
from pathlib import Path

src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
with open(src, "rb") as f:
    head = f.read(2)
    f.seek(0)
    data = json.load(f)
content = data.get("content") or data.get("base64Content") or ""
if content.startswith("data:"):
    content = content.split(",", 1)[1]
raw = base64.b64decode(content, validate=False)
name = data.get("title") or "download.bin"
out = out_dir / name
out.write_bytes(raw)
print(f"{out} ({len(raw)/1e6:.1f} MB, {data.get('mimeType')})")
