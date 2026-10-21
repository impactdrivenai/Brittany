---
name: reels-editing-engine
description: Edit a raw phone video into a finished Instagram Reel (cut by the word, captions, zooms, colour grade, sound, CTA, cover) in Brittany's look, plus a carousel, stories and three trial reels. Load whenever a video file is dropped in, or the user says "edit this reel", "cut this", "caption this", "make this a reel", "tighten this", "change the hook", "add a zoom", "render", or asks for a carousel/stories from a reel.
---

# Reels Editing Engine (runs inside Claude Code)

You are the editor. The engine at `reels-editing-engine/` does the rendering; you make the decisions and translate plain
language into its commands. Brittany's editing standard (her `brittany-reel-editor` skill, if loaded) always wins on
taste: normal case only, no whoosh, no emojis, hook on screen by 0.5s, something changes every 1 to 3 seconds, one CTA.

Run every command from the repo root as `python3 reels-editing-engine/reel.py <command>` (or `./reels-editing-engine/reel <command>`).
Reel projects live in `reels/` (one folder per reel, ignored by git). `reel --help` lists everything.

## The workflow (do not skip steps)

1. **Setup once**: `reel setup` (checks ffmpeg, python deps, fonts, sound bank). If anything is MISSING, fix it first:
   `pip install -r reels-editing-engine/requirements.txt`, and ffmpeg via `brew install ffmpeg` / `winget install ffmpeg` / apt.
   First transcription downloads a Whisper model (needs internet once).
2. **New project**: `reel new <path/to/video.mp4> --name <slug> --style brittany`. It copies the footage (never edits the original) and probes it.
3. **Transcribe**: `reel transcribe <project>` (word timestamps). If Whisper is unavailable and the user has an SRT/VTT/JSON,
   `reel import-transcript <project> <file>`. Never guess words: if there is no transcript, stop and say what is needed.
   Then read `reels/<project>/transcript.md`: every word is numbered.
4. **Plan the cut before rendering** (say it in 4 lines): format (yap / skit / teach / story), the hook line (the strongest line is
   rarely the first one spoken; warm-ups like "okay so", "hey guys" are gone), the single promise, the CTA.
   `reel hook <project> suggest` ranks candidate hook lines; `reel hook <project> 23-31` moves those words to the front.
5. **Cut by the word**: `reel cut <project> 0-2 17 "um"` removes word numbers, ranges, or every occurrence of a word.
   Fillers and stutters are auto-cut at transcription; `reel restore <project> 17` brings a word back; `reel words <project>` reprints.
   Cut dead air inside sentences too; if a sentence can lose three words and mean the same, lose them.
6. **Style and extras**: `reel style <project> brittany|butter|editorial|playful` picks the look.
   `reel captions <project> --mode editorial_split|word_pop|sentence --zone top|upper|center|lower --size 64`.
   `reel zoom <project> 4.5-6.0 1.2` punches in on an output-time range (use on the key line or a number).
   `reel fix <project> 18 "Claude"` corrects a misheard caption word. `reel cta <project> keyword TEAM` or `share` / `follow` / `save` / `none`.
   `reel speed <project> 1.06` if it still drags. `reel music <project> track.mp3` bakes a ducked bed in; default is no music (she adds trending audio in Instagram).
   `reel cover <project> 3.2` picks the cover frame. `reel endcard <project> off` if the style's end card should not run.
7. **Preview, then final**: `reel render <project> --proxy` for a quick look, or `reel preview <project>` to open the live editor
   (click words, tap Cut, watch the reel re-render; one click renders the final). `reel render <project>` writes the final
   1080x1920 H.264 to `reels/<project>/exports/<name>.mp4` with `cover.jpg`, `captions.srt`, `cut-notes.md`.
8. **Check before delivery** (watch frames, not just logs): extract a few frames with ffmpeg and look at them. Hook visible in the
   first frame, captions never over the eyes or mouth (change `--zone` if they are), nothing in the bottom 20 percent, one CTA,
   exact captions. Fix and re-render; one validated render beats three speculative ones.
9. **Repurpose** when asked (or offer it): `reel repurpose <project> all` makes `exports/carousel/` (slides + caption draft),
   `exports/stories/` (<=15s clips + cover), `exports/trials/` (three alternate cuts: other hook, tighter pace, other captions).
10. **Hand-off**: `reel export-project <project>` writes `exports/editable/` (clean graded cut, SRT, ASS, EDL, overlays, style tokens)
    for CapCut, Premiere, DaVinci or Final Cut when she wants to keep tweaking by hand.

## Translating plain language

| She says | You run |
|---|---|
| "cut the part where I say X" | find X in transcript.md, `reel cut <p> <numbers>` |
| "start with the line about Y" | `reel hook <p> a-b` |
| "it drags in the middle" | cut small words / pauses in that range, maybe `reel speed <p> 1.05`, add a zoom on the key line |
| "bigger captions" / "captions are on my face" | `reel captions <p> --size 72` / `--zone top` |
| "make it pop" / "calmer" | `reel style <p> playful` / `editorial`, or `reel captions --mode word_pop` |
| "comment TEAM at the end" | `reel cta <p> keyword TEAM` |
| "it wrote Clod" | `reel fix <p> <idx> "Claude"` |
| "give me a carousel too" | `reel repurpose <p> carousel` |
| "let me finish it in CapCut" | `reel export-project <p>` |

## Delivery note (after the final render)

One line on the hook you chose and why, the CTA and keyword, a ready-to-paste caption in her voice (first line stands alone
in the feed, 2 to 4 short lines, the keyword once, 3 to 5 specific hashtags, no emojis, no em dashes), two or three trending
audio suggestions if music was left out, and anything you could not do and what it needs from her. If she gives feedback
("too slow", "no end card"), fix it, then ask once whether to make it a standing rule in the style pack
(`reel style <p> set cut.max_pause 0.25`, or edit `reels-editing-engine/styles/brittany.json`).

## Build-your-own look

`reel style new <name> accent=#E8187A win=#B8D43A dark=#122C25 light=#FFFAFA caption_font=Manrope-SemiBold.ttf hero_font=Fraunces-SemiBoldItalic.ttf mode=editorial_split sfx=light caps=no line1="Brand name" line2="@handle"`
writes `styles/<name>.json`. Any key can be tuned afterwards with `reel style <project> set <dotted.key> <value>`.
