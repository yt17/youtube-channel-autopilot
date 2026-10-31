---
name: channel-research
description: "Topic research for YouTube channels based on trends, competitor outliers and comment mining; writes prioritized ideas per channel plus a reasoned summary report. Called from /channel-ops or on its own."
---

# Channel research

Report in the user's language; suggested titles and hooks in the channel's language. Don't invent anything: every claim and number has a source.

## Input
- Channel(s): slug, name, YouTube ID, `niche`, `rules` (from config; if run alone, ask which channel)
- Mode: **full** (default) or **quick** (when a production agent needs a topic fast: shorten steps 3–5, 5 ideas are enough)
- `YT_HOME` and `ytool.py`

## Quota
YouTube API: 10,000 units/day. One run spends at most ~1,200: per channel at most 2 `trend` + 1 `search-channels` (~100 each); the rest is cheap.

## Steps (per channel)

### 1. Competitor list
Read `competitors/<slug>` from the panel. Fewer than 3? Fill it:
- channels that repeat across 2 `trend` queries + 1 `search-channels` query
- criteria: same niche, same language, uploaded in the last 30 days, ideally 5k–2M subscribers (giants are not good models), 5–6 channels
- `set` `{list:[{channelId, name, subscribers, why}], updated}`. Never re-add a channel the user removed in the panel.

### 2. What broke out at competitors
`ytool.py competitor-videos <slug> <UC..,UC..> --days 7 --count 20`. A video is an **outlier** if its `views_per_day` is more than **2×** that competitor's average. Find the common pattern: topic, title shape, length, Shorts vs long.

### 3. Niche trends
- `ytool.py trend <slug> "<niche query>" --days 7 --type shorts` and, if needed, `--type video` (max 2 queries per channel)
- Web search for the last 7 days of news in the niche. Check dates; never present old news as new.

### 4. Comment mining
Comments of the top 3 outliers: `ytool.py video-comments <slug> <videoId> --count 80`. Look for:
- questions ("why…?", "what about…?"), requests ("do one on…", "part 2"), gaps ("you forgot…"), corrections, the most-liked emotions
- your own channel's recent comments too (`ytool.py comments <slug> --days 30`)
Summarize; quote at most 10 words.

### 5. What works on your own channel
`ytool.py competitor-videos <slug> <your UC ID> --days 30 --count 30` → best and worst 5; differences in title/topic/length. List topics already covered (to avoid repeats).

### 6. Ideas
8–10 ideas (5 in quick mode). Each:
- **Working title** + **angle** (how this channel tells it differently)
- **Why now:** trend / competitor / comment evidence (which step it came from)
- **Gap:** what competitors didn't cover, what commenters ask
- **Format:** Shorts / long / both; estimated length
- **Hook** (first 3 seconds: visual + line)
- **Sources:** verified links
Mark the best 3 **⭐ priority** (demand evidence × channel fit × producibility — can licensed real footage be found?).

## Output
`out/research/<YYYY-MM-DD>/<slug>.md`:
1. Summary (5 lines): what's happening in the niche this week
2. Competitor outliers (table: video, channel, views/day, why it worked)
3. Audience gaps
4. Own channel: what works / doesn't + covered topics
5. Ideas (⭐ first)
6. Sources

## 📋 Summary report (mandatory, every run)
Put it at the top of the `.md` ("Run report") and return it to the caller. The user wants to see *what was chosen and why*. Per channel:

1. **What was scanned:** competitors (name, subscribers, *why this channel* — niche match, size, recent activity); trend queries used; number of videos and comments examined; news sources.
2. **Analysis — what we saw:** 3–5 outliers (views/day, × channel average) and the **common pattern**; 3–5 audience gaps; what works / doesn't on your channel and the likely reason (with numbers).
3. **Chosen ideas and why:** one line per ⭐ idea — which evidence (trend/competitor/comment/news), why it fits, why now. If a strong candidate was dropped, say why.
4. **Sources:** every source — link + what it supports + publication date. List claims you dropped because they couldn't be verified.
5. **Confidence and limits:** data freshness, small samples, API quota used.

Return to caller: max 15 lines per channel + file path.
