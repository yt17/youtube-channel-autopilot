---
name: channel-production
description: "Produces upload-ready YouTube Shorts or long videos: title alternatives, thumbnails, hooks, script, voice, SFX, dynamic captions, SEO package, Shorts cut from long videos, and a reasoned production report."
---

# Channel production

Video content in the channel's language; report to the caller in the user's language. If a general video-making skill is available, load it and follow it for the technical parts — this skill sets the channel standards and the steps.

**Never play audio or video on the user's computer.** Check with ffprobe, ffmpeg (ebur128 / volumedetect) and extracted PNG frames you look at.

## Input (from the caller; otherwise make a reasonable assumption and state it in the report)
- Channel: slug, name, `niche`, `rules`
- Format: `shorts` (count, default 3) or `long` (1 video + 2 Shorts cut from it)
- Publishing slots (date/time for each output)
- Research files path; if none, run `channel-research` in quick mode
- `YT_HOME` (to see your own recent titles: `ytool.py competitor-videos <slug> <own UC> --days 60 --count 50`)

## Channel standards (owner's rules — don't bend them)
- **No slideshows, nothing that looks AI-made.** Real moving footage from Pexels, Pixabay, Wikimedia Commons (licences that allow reuse; credit in the description when required). Frequent cuts, motion, varied shots.
- Format: voice-over + on-screen text + music.
- **Every video different:** different voice, caption style, pacing. Videos made the same day never share a template.
- No copyrighted music, clips, show scenes or unlicensed celebrity photos. For person-focused topics use licensed generic footage + text. No readable logos, app screens or news text in frame.
- Channel-specific rules come from `rules` in config.
- Packaging (title, description, thumbnail) is complete before upload; the owner doesn't want to edit after uploading.

## Steps

### 1. Topic and angle
Pick a ⭐ idea from research that the channel **hasn't done yet** (compare with the last 60 days of titles). Verify every fact with at least one reliable source; never invent numbers or quotes; drop what can't be verified.

### 2. Title (10 alternatives → 1)
Write 10 titles in different patterns: curiosity gap, number/record, "Why…", contrarian, hidden truth, comparison, question. Score each 1–5 for clarity, curiosity, accuracy (no lying clickbait), length (≤60 chars ideal, excluding `#shorts`). Pick the top; keep the other 9 in the `.txt` as "Backup titles".

### 3. Thumbnail (long videos)
3 variants, 1280×720 JPG: different composition and text (max 4 bold words, readable on a phone), high contrast, one focal point; text complements rather than repeats the title. Image from licensed frames of the video or licensed stock. Mark the recommended one. For each, add a one-line design idea + a detailed prompt for an image generator in the `.txt` (optional for the owner; default delivery is a real-footage thumbnail).

### 4. Hook
Write 3, pick the strongest. Shorts: first 1.5 s — visual hook + one line that opens a question, never the channel name. Long: first 15 s — promise + tension + a hint of the payoff.

### 5. Script (retention)
- Shorts: 60–120 words, one idea, new information every 3–5 s, ending loops back to the start or lands a punchline.
- Long: open with an open loop; a pace change / pattern interrupt every 20–40 s; clear chapters; a second hook mid-way; deliver the promised answer at the end. No filler.
- Write it with a shot list: for each sentence a stock-footage search query and the on-screen text.

### 6. Voice-over
A natural neural TTS voice (e.g. `edge-tts`); different voices for videos made the same day. Synthesize sentence by sentence: small `rate`/`pitch` changes on emphasis, 300–600 ms silence before tension, short pauses before lists and numbers. Save word timings (WordBoundary); if unavailable, distribute by word length within the sentence.

### 7. Music and SFX
Make a **cue sheet** (second → event): whoosh on section changes, riser before the big reveal, hit/impact on the key number, a short punch at the start of Shorts. Royalty-free sources (Pixabay music/SFX, CC0) or synthesize with ffmpeg/Python (filtered noise sweep = whoosh). Music ~-18 dB under the voice, ducked during speech (sidechain).

### 8. Captions (dynamic)
Word by word: 2–4 words on screen, the spoken word highlighted (colour/scale), burned in with an ASS file. Shorts safe area: keep clear of the bottom 20% and the right-edge buttons; text slightly below centre. Different font/colour scheme per video.

### 9. Edit and render
- Shorts: 1080×1920, 20–50 s, cuts every 1.5–4 s. Long: 1920×1080, cuts every 3–6 s; punch-ins on key moments.
- Scale clips to target first, then one final encode: H.264 `-preset veryfast` + AAC, -14 LUFS. Keep Shorts under ~28 MB if your transfer channel has a 30 MB limit.
- Check: ffprobe (duration, resolution, audio), ebur128, frames from start/middle/end (caption overflow, black frames, watermarks).

### 10. SEO package (`.txt`)
- `Title:` chosen
- `Description:` main keyword + curiosity in the first 2 lines; short summary; chapters from `0:00` for long videos; `Sources:` links; footage/music credits when required
- `Tags:` 10–15, comma-separated · `Hashtags:` 3 · `Suggested publish:` the slot · `Backup titles:` 9 · long videos: `Thumbnail:` recommended variant + others + prompts

Plus a same-name **`.json`** (used by auto-upload and the queue):
`{"title": "...", "description": "<full description + hashtags>", "tags": ["..."], "publishAt": "<ISO 8601 with offset, e.g. 2026-11-05T21:00:00+03:00>", "thumb": "<recommended thumbnail file name or null>", "category": "<YouTube category id from config>"}`

### 11. Shorts cut from the long video (format `long`)
Pick the 2 strongest self-contained segments (30–55 s, first second is a hook). Convert to 9:16 (centre crop, or blurred background + video in the middle), re-time captions, end with "Full video on the channel". Each gets its own `#shorts` title, `.txt` and `.json`, with a line pointing to the long video.

## Output
Under `out/_to_upload/` (file names unique, only letters, digits, `_ - .` — matching after upload is by file name):
- Long: `<slug>_<YYYY-MM-DD>.mp4`, `.txt`, `.json`, `<slug>_<YYYY-MM-DD>_thumb_A.jpg` / `_B` / `_C`
- Shorts: `shorts/<slug>_<YYYY-MM-DD>_<n>.mp4` + `.txt` + `.json` (cuts: `_cut1`, `_cut2`)
Working files: `work/<slug>_<format>/`.

## 📋 Summary report (mandatory, every run)
One section per video; also saved as `report.md` in the working folder (standalone runs: `reports/<YYYY-MM-DD-HHmm>_production.md`):

1. **Topic and why:** which research idea (⭐ rank, evidence: trend/competitor/comment/news), why the channel hasn't done it, why this format.
2. **Title decision:** top 3 titles with scores; one line on why the winner.
3. **Hook and structure:** chosen hook, script structure (chapters/loop), why this pacing.
4. **Sources:** table of key claim → source link. Claims removed because they couldn't be verified.
5. **Footage, voice, music:** clip count and site + licence; chosen voice and why (how it differs from today's other videos); music source; SFX.
6. **Technical check:** duration, resolution, size, LUFS, any issue seen in frames.
7. **Publishing:** slot and why this time.
8. **Risks/notes:** copyright, synthetic-voice disclosure, anything uncertain.

Return to caller: 6–10 line summary per video.
