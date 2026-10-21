# What "The Reels Editing Engine" funnel promises, and what this build does

Source: thestartupmom.com/the-reels-editing-engine (plus its waitlist and community FAQ pages, read via search
snippets; the page itself was not reachable from the build environment). Claims below are the vendor's own wording.

| Funnel claim | In this build |
|---|---|
| "Takes the footage from your camera roll and hands you back a reel that's ready to post, in your look. Takes hours of editing off your plate." | `reel new` → `transcribe` → `render`: cut, captions, grade, sound, CTA, end card, cover, in a style pack. |
| "Runs inside Claude Code. Every change lands on your reel while you watch." | `.claude/skills/reels-editing-engine/SKILL.md` lets Claude Code drive the CLI from plain language; `reel preview` is a live editor that re-renders on every change. |
| "Cut your reel by the word": a visual editor where you select words and tap Cut. | Transcript is the timeline. `reel cut 12-15 "um"` from the CLI, or click words and tap Cut in the preview page. Fillers, stutters and dead air are auto-cut; `restore` undoes. |
| Handles cutting, captions, zooms and cover images from plain-language instructions. | `cut`, `hook`, `captions`, `zoom`, `fix`, `cover`, `speed`, `cta`; the skill maps her phrases to commands. |
| Finished MP4, or an editable CapCut draft "still yours to tweak". | Finished MP4 (1080x1920, H.264, under 90 MB). `reel export-project` gives a clean graded cut + SRT + ASS + EDL + PNG overlays + style tokens for CapCut, Premiere, DaVinci or Final Cut. Not a native CapCut draft file (proprietary format). |
| Looks: Butter (free), Editorial and Playful, or build your own style kit (fonts, colours, sounds). | `styles/butter.json`, `editorial.json`, `playful.json`, plus `brittany.json` built from her editing standard. `reel style new ...` builds your own; every key tunable. |
| "Every reel you make can now turn into a carousel, stories, and three trial reels too, in your style pack." | `reel repurpose all`: carousel slides + caption draft, <=15 s story clips + cover, three trial cuts (other hook, tighter pace, other captions). |
| Edit reels without CapCut. | Everything renders locally with ffmpeg; CapCut is optional. |
| One-time purchase, every update included; "setup is the most technical part". | Open code in this repo. `reel setup` checks and installs; the README has the three setup steps. |
| No fixed reel count: "Claude runs on usage". | Same: the engine is free to run; Claude usage is the only metered part. |

What the funnel does not say that Brittany's own editing standard adds here: alternating jump-cut punch-ins, a generated
cinematic LUT per look, sound effects timed to cuts every 8 to 10 s (never the whoosh), voice chain to -14 LUFS, a music bed
ducked under speech, captions kept out of the bottom 20 percent, normal case only, one CTA, an end card.
