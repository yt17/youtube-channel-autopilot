---
name: channel-cleanup
description: "After verifying on YouTube that uploaded videos really exist and are scheduled, moves their local files into a _to_delete folder for the user to trash. Use for /channel-cleanup or 'clean up uploaded files'."
---

# /channel-cleanup — move uploaded files to _to_delete

Reply in the user's language, briefly. This skill **never deletes permanently**; it only moves. It never touches anything on YouTube (read-only checks).

## Locations (under `local_root`)
- Sources: `_to_upload/_uploaded/<date>/` (where `/channel-admin` puts finished files), plus files still in `_to_upload/videos/<Channel>/` or `_to_upload/shorts/<Channel>/` whose `queue` record is `done`
- Target: `_to_delete/<today>/`
- Panel: `queue/<file name>` records (`status`, `videoId`, `channel`)

## Steps
1. Make sure the local folder is reachable (ask once if access is denied).
2. Set up `ytool.py` and keys (`channel-ops` → "0. Preparation" step 4) — only needed for verification.
3. **Collect candidates:** `.mp4` files in the sources; read each one's `queue/<file name>` record.
4. **Verify (all must hold):**
   - record `status == "done"` with a `videoId`
   - the video exists on YouTube (`videos.list?part=status,processingDetails&id=<videoId>`), `uploadStatus` is `processed`, and either `publishAt` is set (scheduled) or it is `public`/`unlisted`
   - anything unverified stays where it is and is listed with the reason ("not found on YouTube", "still processing", "no queue record")
5. **Move** each verified `.mp4` and its same-name `.txt`, `.json`, `_thumb_*.jpg` to `_to_delete/<date>/` with `mv`. Leave emptied folders alone.
6. **Report:** files moved and total size (`du -sh _to_delete`), what couldn't be moved and why, and a last line: "Open `_to_delete` in your file manager and move it to the trash."

## Permanent delete (only if the user explicitly says "delete them permanently")
Ask for delete permission for `_to_delete` only, then delete **only inside `_to_delete`**. Never delete anywhere else. If permission is refused, tell the user they can trash the folder themselves.
