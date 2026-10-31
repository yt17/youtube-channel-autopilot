---
name: channel-admin
description: "Opens the Channel Panel and finalizes videos the user dragged into YouTube Studio: fills title, description, tags, thumbnail and schedule (collision-checked), then reports. Use for /channel-admin, 'open the panel' or 'I uploaded them'."
---

# /channel-admin — open the panel + finalize uploads

Reply in the user's language, briefly.

1. **Open the panel** (`panel_url` from config).
2. **Check the queue:** any `queue` records with `status == "pending"`?
   - Yes: load the `channel-ops` skill and run only **"0. Preparation" steps 3–4** (local folder, tool setup) and **"2b. Finalize uploads"**. Don't start agents or produce anything.
   - No: skip.
3. Read `channels`, `config/settings`, `replies` (`pending`), `runs` (latest 1).
4. **📋 Report** (mandatory; also save as `reports/<YYYY-MM-DD-HHmm>_channel-admin.md`):
   - **Finalized uploads** — table per channel: file → title → planned time → actual time → shift reason (`slot already taken in calendar` / `slot time had passed`). Each video's channel calendar was re-checked right before scheduling.
   - **Unmatched:** videos found in Studio but not in the queue (left untouched) and queued files not found in Studio ("you haven't uploaded these yet") — count per channel and the first few file names.
   - **Queue status:** videos left per channel and the furthest scheduled date.
   Then short status lines:
   - Today's ticked tasks: channel → tasks; if any, "type /channel-ops to run them"
   - Number of reply drafts waiting for approval ("press Approve in the panel")
   - Auto-upload on/off
   - Date and status of the last run
5. If the user asks for a panel change ("move the long video to Thursday", "turn on auto-reply"), update the doc (with `if_version`) and confirm in one sentence.

How to use the panel (if asked):
- Each row is a channel, each column a weekday; Research / Shorts / Video / Comments chips toggle tasks and save instantly.
- The box under each cell shows what's already booked that day (refreshed from YouTube on every `/channel-ops`). Orange = day already has content; new videos go to the first free slot.
- "Upload queue": produced videos. Drag the .mp4s into Studio, close without details, type `/channel-admin` — title, description, tags, thumbnail and schedule fill in. Don't rename files.
- "Let Claude upload videos" on → you don't upload anything.
- Reply drafts wait for approval at the bottom; "Send without approval" sends them directly.
