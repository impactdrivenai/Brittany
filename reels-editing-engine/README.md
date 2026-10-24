# Reels Editing Engine

Drop a raw phone video in, get a finished Reel back in your look: cut by the word, captions in your fonts and colours,
jump-cut punch-ins and zooms, a cinematic grade, sound effects and a ducked music bed, a CTA button, an end card and a
cover image. Then turn the same reel into a carousel, stories and three trial cuts. Runs locally with ffmpeg and Python.
Claude Code drives it from plain language; the `reel` CLI and a live browser editor are there when you want hands on.

## Setup (the most technical part, once)

1. Install ffmpeg (`brew install ffmpeg` on Mac, `winget install ffmpeg` on Windows, `apt install ffmpeg` on Linux).
2. `pip install -r reels-editing-engine/requirements.txt`
3. `python3 reels-editing-engine/reel.py setup --model small` (checks everything and downloads the Whisper model).

Phone footage over about 400 MB: film 1080p at 30 fps or in short takes.

## Using it inside a Claude Code cloud session (no installs)

The container already has ffmpeg, Python and the fonts, and `.claude/settings.json` installs the transcribers when a
session starts. Open a session in this repo, give Claude the video (attach it in chat, push it to the repo, or point at a
Google Drive file under 10 MB) and say "edit this reel". Claude runs every command below for you and sends the finished
files back into the chat. Two optional one-time settings in the cloud environment (Network access, Allowed domains) make
it better: `huggingface.co` + `cdn-lfs.huggingface.co` turns on accurate Whisper transcription (otherwise the offline
pocketsphinx fallback is used and Claude proofreads the captions), and `drive.google.com` +
`drive.usercontent.google.com` + `www.googleapis.com` lets Claude pull large videos straight from a shared Drive link.

## Use

```
reel new ~/Downloads/IMG_1234.mov --name va-hiring --style brittany
reel transcribe va-hiring            # word timestamps; prints hook candidates and the numbered transcript
reel cut va-hiring 0-2 "um"          # strike words; the video follows
reel hook va-hiring 23-31            # move the strongest line to the front
reel cta va-hiring keyword TEAM      # "Comment TEAM" button in the last 2.5 seconds
reel preview va-hiring               # live editor at http://127.0.0.1:8765 : click words, tap Cut, watch it re-render
reel render va-hiring                # final 1080x1920 -> reels/<date>-va-hiring/exports/va-hiring.mp4 (+ cover.jpg, captions.srt, cut-notes.md)
reel repurpose va-hiring all         # carousel slides, story clips, three trial reels
reel export-project va-hiring        # clean cut + SRT + EDL + overlays for CapCut / Premiere / DaVinci
```

`reel --help` lists every command. Projects live in `reels/` next to this folder (override with `REELS_DIR`).

## Looks (style packs)

| Pack | Feel | Captions |
|---|---|---|
| `butter` | warm, soft, simple (the free default) | big bold word pops, centred |
| `editorial` | magazine serif hero words, muted, moody grade | editorial split, upper |
| `playful` | bright, bouncy, lively sounds | word pops, upper case |
| `brittany` | Impact Driven AI: Hot Pink, Lime, Forest, Manrope + Fraunces, warm moody grade, end card | editorial split, normal case only |

Build your own: `reel style new mylook accent=#... dark=#... light=#... caption_font=... hero_font=... mode=... sfx=light caps=no`,
then tune any key with `reel style <project> set captions.size 72`. Packs are plain JSON in `styles/`; fonts in `fonts/`.

## What happens under the hood

`transcribe.py` (faster-whisper, word timestamps) → `cut.py` (fillers, stutters and dead air out, your word cuts, hook
first, alternating punch-ins, zooms) → `render.py` renders each segment through `grade.py` (generated .cube LUT, grain,
vignette), concatenates, burns `captions.py` (ASS via libass, three caption modes), overlays the CTA from `graphics.py`,
mixes `sound.py` (voice chain to -14 LUFS, sfx from `sfx/` every 8 to 10 s, never the whoosh, music ducked under the voice),
appends the end card, writes the cover. `preview.py` is the live editor; `repurpose.py` and `export_project.py` do the rest.
Everything is a separate file in the project folder so one fix never means rebuilding the whole cut.

## Honest limits

- Transcription: faster-whisper (downloads a model on first run) with an offline pocketsphinx fallback (bundled model, rougher; proofread captions). Or import an SRT/VTT/JSON with `reel import-transcript`.
- Captions avoid the bottom 20 percent and sit in the zone you pick; there is no face detection, so if a caption lands on a face, change `--zone`.
- The editable hand-off is a clean cut + SRT + EDL + PNG overlays, not a native CapCut draft file. CapCut imports the SRT and the clips; the look carries through the style tokens and the fonts folder.
- Sound effects ship as a small synthesized starter bank. Drop your own WAV/MP3 files into `sfx/` with descriptive names (anything named whoosh or swish is ignored).
