#!/usr/bin/env python3
"""ytool — a tiny YouTube Data API v3 CLI for channel-ops (official API only, no browser automation).

Files (default ~/youtube/_system, override with YT_HOME):
  client_secret.json   Google Cloud > Credentials > OAuth client ID (Desktop app)
  tokens/<slug>.json   created once per channel by auth-url / auth-code

Setup:
  auth-url  <slug>               consent link to open in a browser
  auth-code <slug> <url|code>    paste the localhost URL you were redirected to; token is saved
  whoami    <slug>

Own channel:
  comments  <slug> [--days 7]    new top-level comments you have not replied to (JSON)
  reply     <slug> <commentId> <text>
  calendar  <slug> [--days 14]   scheduled / recently published videos (JSON)
  pending   <slug> [--count 50]  private, unscheduled uploads (with original fileName) — what you just dragged into Studio
  finalize  <slug> <videoId> <meta.json>   set title/description/tags/category/thumbnail and schedule (collision-safe)
  upload    <slug> <video.mp4> <meta.json> resumable upload as private + publishAt

Competitors / trends (any channel's token works; quota cost in parentheses, 10,000 units/day):
  search-channels   <slug> "<query>" [--count 10]                          (100)
  competitor-videos <slug> <UC..,UC..> [--days 7] [--count 15]             (~3 per channel)
  video-comments    <slug> <videoId> [--count 60]                          (1)
  trend             <slug> "<query>" [--days 7] [--count 15] [--type shorts|video]  (~101)

meta.json: {"title": "...", "description": "...", "tags": [...], "publishAt": "2026-11-05T21:00:00+03:00",
            "category": "24", "thumb": "path/to/thumb.jpg" | null}
"""
import json, os, sys, time, urllib.parse, datetime as dt, re
import requests

HOME = os.environ.get("YT_HOME", os.path.expanduser("~/youtube/_system"))
SCOPES = "https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/youtube.upload"
REDIRECT = "http://localhost:8765/"
API = "https://youtube.googleapis.com/youtube/v3/"
LOCAL_TZ = dt.datetime.now().astimezone().tzinfo  # times in `calendar` output use your machine's zone


def client():
    with open(os.path.join(HOME, "client_secret.json")) as f:
        c = json.load(f)
    return c.get("installed") or c.get("web")


def tok_path(k):
    return os.path.join(HOME, "tokens", k + ".json")


def save_tok(k, t):
    os.makedirs(os.path.join(HOME, "tokens"), exist_ok=True)
    with open(tok_path(k), "w") as f:
        json.dump(t, f, indent=1)


def access(k):
    with open(tok_path(k)) as f:
        t = json.load(f)
    if t.get("access_token") and t.get("expires_at", 0) > time.time() + 60:
        return t["access_token"]
    c = client()
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    j = r.json()
    t["access_token"] = j["access_token"]
    t["expires_at"] = time.time() + j.get("expires_in", 3600)
    save_tok(k, t)
    return t["access_token"]


def call(k, method, path, params=None, body=None):
    r = requests.request(method, API + path, params=params, json=body, timeout=60,
                         headers={"Authorization": "Bearer " + access(k)})
    if r.status_code >= 400:
        sys.exit(f"API error {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {}


def opt(args, name, default):
    if name in args:
        i = args.index(name)
        return int(args[i + 1])
    return default


def iso_secs(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    D, H, M, S = (int(x or 0) for x in m.groups())
    return D * 86400 + H * 3600 + M * 60 + S


def main(a):
    if len(a) < 2:
        sys.exit(__doc__)
    cmd, k = a[0], a[1]
    if cmd == "auth-url":
        c = client()
        print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code",
            "scope": SCOPES, "access_type": "offline", "prompt": "consent select_account"}))
    elif cmd == "auth-code":
        raw = a[2]
        code = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("code", [raw])[0]
        c = client()
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": c["client_id"], "client_secret": c["client_secret"], "code": code,
            "redirect_uri": REDIRECT, "grant_type": "authorization_code"}, timeout=30)
        r.raise_for_status()
        j = r.json()
        if "refresh_token" not in j:
            sys.exit("No refresh_token returned; remove the app at myaccount.google.com/permissions and try again")
        save_tok(k, {"refresh_token": j["refresh_token"], "access_token": j["access_token"],
                     "expires_at": time.time() + j.get("expires_in", 3600)})
        ch = call(k, "GET", "channels", {"part": "snippet", "mine": "true"})["items"][0]
        t = json.load(open(tok_path(k)))
        t.update(channel_id=ch["id"], channel_title=ch["snippet"]["title"])
        save_tok(k, t)
        print(json.dumps({"slug": k, "channel_id": ch["id"], "title": ch["snippet"]["title"]}, ensure_ascii=False))
    elif cmd == "whoami":
        t = json.load(open(tok_path(k)))
        print(json.dumps({"channel_id": t.get("channel_id"), "title": t.get("channel_title")}, ensure_ascii=False))
    elif cmd == "comments":
        days = opt(a, "--days", 7)
        t = json.load(open(tok_path(k)))
        cid = t["channel_id"]
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        out, page = [], None
        while True:
            p = {"part": "snippet,replies", "allThreadsRelatedToChannelId": cid, "maxResults": 100,
                 "order": "time", "textFormat": "plainText"}
            if page:
                p["pageToken"] = page
            j = call(k, "GET", "commentThreads", p)
            stop = False
            for th in j.get("items", []):
                top = th["snippet"]["topLevelComment"]
                s = top["snippet"]
                when = dt.datetime.fromisoformat(s["publishedAt"].replace("Z", "+00:00"))
                if when < since:
                    stop = True
                    break
                if s.get("authorChannelId", {}).get("value") == cid:
                    continue
                replied = any(r["snippet"].get("authorChannelId", {}).get("value") == cid
                              for r in th.get("replies", {}).get("comments", []))
                if replied:
                    continue
                out.append({"id": top["id"], "video_id": s.get("videoId") or th["snippet"].get("videoId"),
                            "author": s.get("authorDisplayName"), "text": s.get("textDisplay"),
                            "date": s["publishedAt"], "likes": s.get("likeCount", 0)})
            page = j.get("nextPageToken")
            if stop or not page:
                break
        ids = sorted({c["video_id"] for c in out if c["video_id"]})
        titles = {}
        for i in range(0, len(ids), 50):
            for v in call(k, "GET", "videos", {"part": "snippet", "id": ",".join(ids[i:i + 50])}).get("items", []):
                titles[v["id"]] = v["snippet"]["title"]
        for c in out:
            c["video"] = titles.get(c["video_id"], "")
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "reply":
        pid, text = a[2], a[3]
        j = call(k, "POST", "comments", {"part": "snippet"},
                 {"snippet": {"parentId": pid, "textOriginal": text}})
        print(json.dumps({"sent": j.get("id")}))
    elif cmd == "calendar":
        days = opt(a, "--days", 14)
        up = call(k, "GET", "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
        pl = up["contentDetails"]["relatedPlaylists"]["uploads"]
        ids, page = [], None
        for _ in range(4):
            p = {"part": "contentDetails", "playlistId": pl, "maxResults": 50}
            if page:
                p["pageToken"] = page
            j = call(k, "GET", "playlistItems", p)
            ids += [i["contentDetails"]["videoId"] for i in j.get("items", [])]
            page = j.get("nextPageToken")
            if not page:
                break
        now = dt.datetime.now(dt.timezone.utc)
        end = now + dt.timedelta(days=days)
        out = []
        for i in range(0, len(ids), 50):
            for v in call(k, "GET", "videos", {"part": "snippet,status,contentDetails",
                                                "id": ",".join(ids[i:i + 50])}).get("items", []):
                st = v["status"]
                when = st.get("publishAt") if st.get("privacyStatus") == "private" else v["snippet"]["publishedAt"]
                if not when:
                    continue
                w = dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
                if now - dt.timedelta(days=1) <= w <= end:
                    secs = iso_secs(v["contentDetails"].get("duration"))
                    out.append({"date": w.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
                                "type": "shorts" if secs <= 180 else "video", "title": v["snippet"]["title"],
                                "status": "scheduled" if st.get("publishAt") and st.get("privacyStatus") == "private" else st.get("privacyStatus")})
        out.sort(key=lambda x: x["date"])
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "search-channels":
        q, n = a[2], opt(a, "--count", 10)
        s = call(k, "GET", "search", {"part": "snippet", "q": q, "type": "channel", "maxResults": n})
        ids = [i["id"]["channelId"] for i in s.get("items", [])]
        out = []
        if ids:
            for c in call(k, "GET", "channels", {"part": "snippet,statistics", "id": ",".join(ids)}).get("items", []):
                st = c["statistics"]
                out.append({"channelId": c["id"], "name": c["snippet"]["title"],
                            "subscribers": int(st.get("subscriberCount", 0)), "videos": int(st.get("videoCount", 0)),
                            "views": int(st.get("viewCount", 0))})
        out.sort(key=lambda x: -x["subscribers"])
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "competitor-videos":
        chans, days, n = a[2].split(","), opt(a, "--days", 7), opt(a, "--count", 15)
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        now = dt.datetime.now(dt.timezone.utc)
        cs = call(k, "GET", "channels", {"part": "snippet,contentDetails", "id": ",".join(chans)}).get("items", [])
        ids, names = [], {}
        for c in cs:
            names[c["id"]] = c["snippet"]["title"]
            j = call(k, "GET", "playlistItems", {"part": "contentDetails", "maxResults": 50,
                                                  "playlistId": c["contentDetails"]["relatedPlaylists"]["uploads"]})
            for it in j.get("items", []):
                pub = it["contentDetails"].get("videoPublishedAt")
                if pub and dt.datetime.fromisoformat(pub.replace("Z", "+00:00")) >= since:
                    ids.append(it["contentDetails"]["videoId"])
        out = []
        for i in range(0, len(ids), 50):
            for v in call(k, "GET", "videos", {"part": "snippet,statistics,contentDetails",
                                                "id": ",".join(ids[i:i + 50])}).get("items", []):
                pub = dt.datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
                age = max((now - pub).total_seconds() / 86400, 0.25)
                views = int(v["statistics"].get("viewCount", 0))
                secs = iso_secs(v["contentDetails"].get("duration"))
                out.append({"videoId": v["id"], "channel": names.get(v["snippet"]["channelId"], ""),
                            "title": v["snippet"]["title"], "type": "shorts" if secs <= 180 else "video",
                            "seconds": secs, "views": views, "views_per_day": round(views / age),
                            "likes": int(v["statistics"].get("likeCount", 0)),
                            "comments": int(v["statistics"].get("commentCount", 0)),
                            "date": v["snippet"]["publishedAt"][:10]})
        out.sort(key=lambda x: -x["views_per_day"])
        print(json.dumps(out[:n], ensure_ascii=False, indent=1))
    elif cmd == "video-comments":
        # most relevant comments of any public video
        vid, n = a[2], opt(a, "--count", 60)
        j = call(k, "GET", "commentThreads", {"part": "snippet", "videoId": vid, "order": "relevance",
                                               "maxResults": min(n, 100), "textFormat": "plainText"})
        out = [{"text": t["snippet"]["topLevelComment"]["snippet"]["textDisplay"][:400],
                "likes": t["snippet"]["topLevelComment"]["snippet"].get("likeCount", 0),
                "replies": t["snippet"].get("totalReplyCount", 0)} for t in j.get("items", [])]
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "trend":
        q, days, n = a[2], opt(a, "--days", 7), opt(a, "--count", 15)
        kind = a[a.index("--type") + 1] if "--type" in a else None
        after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p = {"part": "snippet", "q": q, "type": "video", "order": "viewCount", "publishedAfter": after,
             "maxResults": 50, "relevanceLanguage": "en"}
        if kind == "shorts":
            p["videoDuration"] = "short"
        elif kind == "video":
            p["videoDuration"] = "medium"
        ids = [i["id"]["videoId"] for i in call(k, "GET", "search", p).get("items", [])]
        now = dt.datetime.now(dt.timezone.utc)
        out = []
        if ids:
            for v in call(k, "GET", "videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids)}).get("items", []):
                pub = dt.datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
                views = int(v["statistics"].get("viewCount", 0))
                out.append({"videoId": v["id"], "channel": v["snippet"]["channelTitle"], "channelId": v["snippet"]["channelId"],
                            "title": v["snippet"]["title"], "seconds": iso_secs(v["contentDetails"].get("duration")),
                            "views": views, "views_per_day": round(views / max((now - pub).total_seconds() / 86400, 0.25)),
                            "comments": int(v["statistics"].get("commentCount", 0)), "date": v["snippet"]["publishedAt"][:10]})
        out.sort(key=lambda x: -x["views_per_day"])
        print(json.dumps(out[:n], ensure_ascii=False, indent=1))
    elif cmd == "pending":
        # private, unscheduled uploads — i.e. files you dragged into Studio and closed without filling anything
        n = opt(a, "--count", 50)
        up = call(k, "GET", "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
        pl = up["contentDetails"]["relatedPlaylists"]["uploads"]
        j = call(k, "GET", "playlistItems", {"part": "contentDetails", "playlistId": pl, "maxResults": min(n, 50)})
        ids = [i["contentDetails"]["videoId"] for i in j.get("items", [])]
        out = []
        if ids:
            for v in call(k, "GET", "videos", {"part": "snippet,status,fileDetails,processingDetails",
                                                "id": ",".join(ids)}).get("items", []):
                st = v["status"]
                if st.get("privacyStatus") == "private" and not st.get("publishAt"):
                    out.append({"videoId": v["id"], "file": (v.get("fileDetails") or {}).get("fileName"),
                                "title": v["snippet"]["title"], "upload": st.get("uploadStatus"),
                                "processing": (v.get("processingDetails") or {}).get("processingStatus"),
                                "date": v["snippet"]["publishedAt"][:16]})
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "finalize":
        # finalize <slug> <videoId> <meta.json> — metadata + schedule + thumbnail for a video uploaded by hand
        vid, meta = a[2], json.load(open(a[3]))
        cur = call(k, "GET", "videos", {"part": "snippet,status", "id": vid})["items"]
        if not cur:
            sys.exit("Video not found")
        body = {"id": vid,
                "snippet": {"title": meta["title"][:100], "description": meta.get("description", "")[:5000],
                            "tags": meta.get("tags", [])[:30], "categoryId": str(meta.get("category", "24")),
                            "defaultLanguage": "en", "defaultAudioLanguage": "en"},
                "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
        if meta.get("publishAt"):
            w = dt.datetime.fromisoformat(meta["publishAt"])
            now = dt.datetime.now(dt.timezone.utc)
            reasons = []
            if w <= now + dt.timedelta(minutes=30):
                # slot already passed: same time, next day (never publish immediately)
                while w <= now + dt.timedelta(minutes=30):
                    w += dt.timedelta(days=1)
                reasons.append("slot time had passed")
            # calendar collision: another video already owns this exact minute -> move to the next day
            taken = set()
            up = call(k, "GET", "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
            pl = up["contentDetails"]["relatedPlaylists"]["uploads"]
            ids, page = [], None
            for _ in range(4):
                p = {"part": "contentDetails", "playlistId": pl, "maxResults": 50}
                if page:
                    p["pageToken"] = page
                j = call(k, "GET", "playlistItems", p)
                ids += [i["contentDetails"]["videoId"] for i in j.get("items", [])]
                page = j.get("nextPageToken")
                if not page:
                    break
            for i in range(0, len(ids), 50):
                for v in call(k, "GET", "videos", {"part": "status,snippet", "id": ",".join(ids[i:i + 50])}).get("items", []):
                    if v["id"] == vid:
                        continue
                    st = v["status"]
                    t = st.get("publishAt") or (v["snippet"]["publishedAt"] if st.get("privacyStatus") == "public" else None)
                    if t:
                        taken.add(dt.datetime.fromisoformat(t.replace("Z", "+00:00")).replace(second=0, microsecond=0))
            first = w
            while w.astimezone(dt.timezone.utc).replace(second=0, microsecond=0) in taken:
                w += dt.timedelta(days=1)
            if w != first:
                reasons.append("slot already taken in calendar")
            if reasons:
                meta["shifted_to"] = w.isoformat()
                meta["shift_reason"] = ", ".join(reasons)
            body["status"]["publishAt"] = w.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        call(k, "PUT", "videos", {"part": "snippet,status"}, body)
        out = {"videoId": vid, "url": "https://youtu.be/" + vid, "publishAt": meta.get("shifted_to") or meta.get("publishAt"),
               "shifted": bool(meta.get("shifted_to")), "shift_reason": meta.get("shift_reason"), "thumb": None}
        if meta.get("thumb") and os.path.exists(meta["thumb"]):
            with open(meta["thumb"], "rb") as f:
                tr = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                                   params={"videoId": vid}, data=f, timeout=120,
                                   headers={"Authorization": "Bearer " + access(k), "Content-Type": "image/jpeg"})
            out["thumb"] = "ok" if tr.status_code < 400 else f"error {tr.status_code}: {tr.text[:200]}"
        st = call(k, "GET", "videos", {"part": "status", "id": vid})["items"][0]["status"]
        out["status"] = {"privacyStatus": st.get("privacyStatus"), "publishAt": st.get("publishAt")}
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "upload":
        # Uploads as private + publishAt (scheduled). Note: API uploads from an unaudited Google Cloud project
        # may be locked to private by YouTube — the drag-into-Studio + finalize flow avoids that.
        vpath = a[2]
        meta = json.load(open(a[3]))
        body = {"snippet": {"title": meta["title"][:100], "description": meta.get("description", "")[:5000],
                            "tags": meta.get("tags", [])[:30], "categoryId": str(meta.get("category", "24")),
                            "defaultLanguage": "en", "defaultAudioLanguage": "en"},
                "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
        if meta.get("publishAt"):
            w = dt.datetime.fromisoformat(meta["publishAt"])
            if w <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30):
                sys.exit("publishAt must be at least 30 minutes in the future")
            body["status"]["publishAt"] = w.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        size = os.path.getsize(vpath)
        h = {"Authorization": "Bearer " + access(k), "Content-Type": "application/json; charset=UTF-8",
             "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}
        r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos",
                          params={"uploadType": "resumable", "part": "snippet,status"},
                          headers=h, data=json.dumps(body), timeout=60)
        if r.status_code >= 400:
            sys.exit(f"Could not open upload session {r.status_code}: {r.text[:500]}")
        loc = r.headers["Location"]
        vid = None
        for attempt in range(5):
            with open(vpath, "rb") as f:
                rr = requests.put(loc, data=f, timeout=3600, headers={"Content-Type": "video/mp4",
                                                                       "Authorization": "Bearer " + access(k)})
            if rr.status_code in (200, 201):
                vid = rr.json()["id"]
                break
            if rr.status_code in (500, 502, 503, 504):
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"Upload error {rr.status_code}: {rr.text[:500]}")
        if not vid:
            sys.exit("Upload did not complete after 5 attempts")
        out = {"videoId": vid, "url": "https://youtu.be/" + vid, "publishAt": meta.get("publishAt"), "thumb": None}
        if meta.get("thumb") and os.path.exists(meta["thumb"]):
            with open(meta["thumb"], "rb") as f:
                tr = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                                   params={"videoId": vid}, data=f, timeout=120,
                                   headers={"Authorization": "Bearer " + access(k), "Content-Type": "image/jpeg"})
            out["thumb"] = "ok" if tr.status_code < 400 else f"error {tr.status_code}: {tr.text[:200]}"
        st = call(k, "GET", "videos", {"part": "status", "id": vid})["items"]
        out["status"] = st[0]["status"] if st else None
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
