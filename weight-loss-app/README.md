# Brittany's 100-Pound Mission

A custom weight-loss tracker built specifically for you — INFJ, D, 7w8, ADHD, T2D + insulin resistance, perimenopause, runs a business, has a kid. Zero-friction logging, gamification, public accountability, and a big red WALL for missed days.

## What it does

- **Tracks everything**: food + macros, weight, blood glucose, exercise, sleep, mood/energy, cycle, water, meds/supplements, symptoms, progress photos, daily notes
- **AI food logging**: type "2 eggs, avocado toast, black coffee" → gets parsed into macros automatically
- **Streak tracking + Wall of Shame**: every logged day = green, every missed day = red, visible for 30 days
- **Stakes tracker**: define your consequences ("if I miss 3 days in a row, I Venmo my sister $100") and hold yourself to them
- **Public shareable dashboard**: one-click link that shows your progress to anyone. Your eyes-on-you = fuel.
- **Weekly accountability post generator**: auto-writes a share-ready IG/FB post every week
- **Milestone tracker**: 10 milestones from 5 lbs → 100 lbs, each with a non-food reward
- **October 31 checkpoint**: 50-lb sub-goal tracked separately from the 100-lb main goal
- **Fanfare on every log**: confetti, animations, encouragement. Because your 7w8 needs dopamine.

## How to use it

### Option 1: Just open the file
1. Double-click `index.html` — it opens in your browser
2. Set up your profile (name, weights, macros) — takes 60 seconds
3. Start logging. Everything saves locally to your browser.

### Option 2: Deploy to the web (recommended — use on any device)
Push this folder to Vercel, Netlify, or GitHub Pages. It's a single static HTML file — no build step.

**Fastest path (GitHub Pages):**
```
Settings → Pages → Deploy from branch → main → /weight-loss-app
```
Then bookmark `https://<username>.github.io/<repo>/weight-loss-app/` on your phone home screen.

**Or Vercel (30 seconds):**
```
npx vercel --prod
```

### AI food logging setup (optional but recommended)
1. Go to https://console.anthropic.com and create an API key
2. In the app: Settings → paste your API key
3. Food logging now uses Claude Haiku to parse your meals accurately

Without a key, the app falls back to a built-in food database (~60 common foods) that still works but is less flexible.

## Data storage

Everything is stored in your browser's localStorage on the device you use. **Data does NOT sync between phone and desktop by default.**

To sync:
- **Simplest**: Export from one device (Settings → Export All Data), import on the other
- **Better**: Deploy the app to Vercel + hook up a backend (Supabase, Firebase) — not built in yet, but the data model is designed for it

## Sharing your progress publicly

Tap the 📤 icon in the header → copy your public dashboard link. Anyone who visits sees a live snapshot of your progress. No login needed for them.

## Reset / start over

Settings → Reset Everything. Nuclear option, wipes all data.

## Files

- `index.html` — the entire app, no dependencies
- `README.md` — this file

## Adjustments you'll probably want to make

- **Macros**: Preloaded with T2D/insulin-resistance-friendly targets (1500 cal, 140p / 100c / 60f). Adjust in Settings once you get advice from your doc.
- **Milestone rewards**: Currently placeholder — edit them in `index.html` in the `renderMilestones()` function to make them yours.
- **Stakes**: Preloaded empty — you set what actually scares you.
