---
name: channel-ops
description: "Runs the day's YouTube work from the Channel Panel plan: launches comment, research, Shorts and long-video agents in parallel, prepares the upload queue and writes a reasoned run report. Use when the user types /channel-ops."
---

# /channel-ops — the channel manager

This skill is the **manager**: it reads the plan, launches agents, delivers results. *How* to research and produce is written in their own skills (`channel-research`, `channel-production`); don't repeat it here.

Reports go in the user's language (`report_language` in config). On-screen text, titles, descriptions and comment replies go in each channel's language. **Never play audio or video on the user's computer** — check media silently (ffprobe, ebur128, extracted frames).

## Constants
- Config: `$YT_HOME/config.json` (see `config/config.example.json`): `panel_url`, `timezone`, `local_root`, `channels[]` with `slug, name, channelId, niche, category, rules`.
- Panel database (Artifact DB at `panel_url`):
  - `channels/<slug>`: `{name, url, channelId, order, days:{mon..sun:{tasks:{research,shorts,video,comments}, booked}}}`
  - `competitors/<slug>`: `{list:[{channelId, name, subscribers, why}], updated}` (filled by channel-research)
  - `config/settings`: `{autoReply, autoUpload}`
  - `replies/<commentId>`: `{channel, video, author, comment, commentId, draft, status: pending|approved|rejected|sent, date}`
  - `runs/<YYYY-MM-DD-HHmm>`: `{date, status: ok|partial|error, summary:[...], reportFile}`
  - `queue/<file name>`: `{channel, file, title, description, tags, publishAt, category, thumb, status: pending|done|error, videoId, addedAt, doneAt}`
- Tool: `tools/ytool.py` with `YT_HOME` holding `client_secret.json` and `tokens/<slug>.json`.
- Local folder (`local_root`):
  - `_to_upload/videos/<Channel name>/` long videos + thumbnails + `.txt`; `_to_upload/shorts/<Channel name>/` Shorts + `.txt`. Nothing is left loose in `_to_upload/` itself.
  - `_to_upload/_uploaded/<date>/` finished; `_to_delete/` for the user to trash
  - `reports/`, `research/<YYYY-MM-DD>/<slug>.md`, `_archive/<Channel name>/`

## 0. Preparation
1. Get the current time in `timezone` → today's weekday key (mon..sun).
2. Read `channels`, `config/settings`, `competitors`, and `replies` with `status == "approved"` from the panel.
3. Make sure the local folder is reachable. If access is denied, ask the user once; keep doing cloud work meanwhile.
4. Set up the tool: copy `ytool.py`, `client_secret.json` and the tokens into `YT_HOME`. Without keys, skip comments/calendar/competitor work and say so in the report.
5. Load each channel's `rules` and `niche` — they are passed to agents verbatim.

## 1. Calendar (collision prevention)
For each channel `ytool.py calendar <slug> --days 8`. Write a `booked` summary for each of the next 7 days (`3 Shorts`, `1 Video + 2 Shorts`, or `""`) in one batch update.

**Slot rule** (you hand slots to agents): learn the channel's habit from its calendar (which hours it publishes Shorts / long videos). For new Shorts pick free Shorts hours within the next 14 days; for a long video the first day without one. Also treat every `queue` record with `status == "pending"` as occupying its `publishAt`. Never suggest "publish now". Don't put a type on today if today already has it.

## 2. Send approved replies
Each `approved` reply: `ytool.py reply <slug> <commentId> "<draft>"` → on success `status: "sent"`.

## 2b. Finalize uploads (videos the user dragged into Studio)
Also called by `/channel-admin`. The user only drags files into Studio; everything else happens here.
1. Take `queue` records with `status == "pending"`. None → skip.
2. For their channels run `ytool.py pending <slug>` → private, unscheduled uploads with their original `file` name.
3. **Match by file name only.** Never touch an unmatched video. If two uploads share a name, take the newest and report the other.
4. For each match write a meta `.json` from the record (`title, description, tags, publishAt, category, thumb` = local path to the thumbnail) and run `ytool.py finalize <slug> <videoId> <meta.json>`. `finalize` re-reads the channel calendar right before scheduling; if the slot is taken or already past, it moves to the same time on the next free day and returns `shifted` + `shift_reason` — put those in the report. If the thumbnail fails because the video is still processing, mark the record done with `thumbPending: true` and retry only the thumbnail next run.
5. Update the record: `status: "done"`, `videoId`, actual `publishAt`, `doneAt`.
6. Move that video's local files to `_to_upload/_uploaded/<YYYY-MM-DD>/` and append `✅ ready (youtu.be/…)` to its line in `UPLOAD-LIST.txt`.
7. Report per channel: file → title → planned time → actual time → shift reason; unmatched videos and why; files still waiting in the queue.
Never publish immediately, never delete, never make public: only `private` + `publishAt`.

## 3. Agents (one message, parallel, max 4)
Group today's tasks by channel; don't start an agent with nothing to do. Give each agent full context (they don't see this conversation): channel names/slugs/IDs, rules, `YT_HOME`, output folder, publishing slots, panel URL, competitor list. Before production, copy the channel's research files from the last 7 days into `out/input/` and pass the path.

| Agent | When | Prompt core |
|---|---|---|
| **Comments** | any channel has `comments` | Apply "Comment work" below |
| **Research** | any channel has `research` | "Load the `channel-research` skill and run it in full mode for these channels" |
| **Shorts** | any channel has `shorts` | "Load `channel-production`; format: shorts; 3 per channel; slots: …" |
| **Long video** | any channel has `video` | "Load `channel-production`; format: long; 1 video + 2 Shorts cut from it; slots: …" |

Research and production can run the same day in parallel; production uses existing research, or runs `channel-research` in quick mode itself. **Every agent must end with its 📋 summary report** (see each skill).

### Comment work (give this to the comments agent verbatim)
1. `ytool.py comments <slug> --days 7` → unanswered comments.
2. Skip spam, hate, links/ads, and comments that already have a `replies/<commentId>` doc.
3. Write a short (1–2 sentences), warm reply in the channel's voice. Answer questions correctly (search if needed); if unsure, don't invent. Thank critics without getting defensive. An occasional natural question that leads to the next video is fine.
4. `autoReply` true → send and mark `sent`; false → save as `pending` in the panel for approval.
5. Report: comments per channel, sent/pending, recurring questions and requests (valuable for research).

## 4. Check, upload and deliver
1. `ffprobe` every video (duration, resolution, audio stream). Broken → don't deliver, report it.
2. **`autoUpload` true:** `ytool.py upload <slug> <mp4> <same-name.json>` (private + publishAt, thumbnail for long videos). If YouTube locks it private without a schedule (unaudited API project), say "schedule it in Studio" in the report. Back up uploaded files to `_to_upload/_uploaded/<date>/`.
3. **false (default):** copy files to the local folder: long videos to `_to_upload/videos/<Channel name>/`, Shorts to `_to_upload/shorts/<Channel name>/` (long videos and Shorts kept apart, one subfolder per channel, so the user can bulk-drag each folder into that channel's Studio). The queue record's `thumb` is relative to `_to_upload/`, e.g. `videos/<Channel name>/<name>_thumb_A.jpg`. Large files may need re-encoding or splitting depending on the transfer channel. `.json` sidecars stay in the cloud. Create a `queue/<file name>` record for each video (batch `set`) from the agent's `.json`, with `status: "pending"`.
4. Copy research files to `research/<date>/`.
5. **Upload list:** prepend this run's section to `_to_upload/UPLOAD-LIST.txt`:
   ```
   === Saturday 31 Oct 2026 run ===
   [Channel A] → videos/Channel A/
   - channel-a_2026-10-31.mp4 (+ thumb_B recommended) → Mon 2 Nov 19:00 → "<title>"
   [Channel A] → shorts/Channel A/
   - channel-a_2026-10-31_1.mp4 → Thu 5 Nov 21:00 → "<title>"
   ```

## 5. Log and report (mandatory — every run ends with a reasoned report)
Merge the agents' reports into **one run report** and put it in three places: the chat, `reports/<YYYY-MM-DD-HHmm>_channel-ops.md`, and the panel `runs/<id>` (`status`, 4–8 line `summary`, `reportFile`).

Order:
1. **Summary (3–5 lines):** what ran, videos produced, comments, research; overall state.
2. **📤 Upload list** — per channel: | Channel | File | Type | Publish time | Title |. With manual upload add: "**Your only job:** drag the .mp4s in `_to_upload/videos/<Channel>` and `_to_upload/shorts/<Channel>` into that channel's Studio, close without filling anything, then type `/channel-admin`. Don't rename files — matching is by file name."
3. **🔎 Research** (per channel): competitors scanned and why they were chosen, what broke out (with numbers), audience gaps, ⭐ chosen ideas + the reason for each, sources, confidence/limits.
4. **🎬 Production** (per video): why this topic (which evidence), title decision (top 3 candidates + why the winner), sources (claim → link), footage/voice/music and licences, technical check, why this slot, risks.
5. **💬 Comments:** counts, sent/pending, recurring asks and what they mean for the next content.
6. **📅 Calendar:** booked days updated, anything shifted and why.
7. **⚠️ Issues and next step:** errors, leftovers, one next step for the user.

Never invent a reason an agent didn't give; write "not reported by agent".

## One-time setup
1. Google Cloud Console → enable **YouTube Data API v3** → OAuth consent screen (External; add yourself as test user) → Credentials → OAuth client ID → **Desktop app** → download JSON to `$YT_HOME/client_secret.json`.
2. For each channel: `ytool.py auth-url <slug>` → open, pick the channel (brand account), allow. The browser lands on `localhost:8765` ("can't connect") — copy that full URL and run `ytool.py auth-code <slug> "<url>"`.
3. In "Testing" mode refresh tokens can expire after 7 days; repeat step 2 or switch the consent screen to "In production" (personal use needs no verification, you'll just see a warning screen).
