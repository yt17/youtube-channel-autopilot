# How I Run Four YouTube Channels From One Chat Window

*Claude does the research, the videos and the scheduling. I drag a folder into Studio.*

![The daily loop](https://raw.githubusercontent.com/yt17/youtube-channel-autopilot/main/docs/flow.png)

I'm a software developer. I have a full-time job, and on the side I run four small faceless YouTube channels: a sports stats Shorts channel, a pop-culture channel, an "evidence file" explainer channel and an ambient sounds channel.

Each one needs the same things every week. Figure out what's working in the niche, make Shorts and long videos, write titles and descriptions, schedule them so they don't collide, answer comments, clean up the files. Multiply that by four and it stops being a hobby.

So I sat down with Claude and built this. Now a normal day looks like this: I type `/channel-ops`, later I drag a folder into YouTube Studio, then I type `/channel-admin`. That's it.

The code and skills are on GitHub: [github.com/yt17/youtube-channel-autopilot](https://github.com/yt17/youtube-channel-autopilot)

## What's in it

There are three parts.

A planning panel. It's a small Claude Artifact with a database behind it. Rows are channels, columns are weekdays, and I click chips like Research, Shorts, Video or Comments to decide what happens when. Each cell also shows what's already scheduled on YouTube that day, so I don't stack two long videos on the same evening by accident.

![The Channel Panel (demo data)](https://raw.githubusercontent.com/yt17/youtube-channel-autopilot/main/docs/panel.png)

Five skills. A skill is just a folder with a `SKILL.md` that tells Claude how to do one job:

- `/channel-ops` is the manager. It reads today's plan, checks each channel's calendar and starts up to four agents in parallel: comments, research, Shorts and long video.
- `channel-research` looks at competitors' recent videos, finds the ones that did more than twice their channel's average, reads their comments and comes back with ideas.
- `channel-production` makes the videos: ten title candidates, three hooks, script, voice, stock footage, sound effects, word-by-word captions, thumbnails, and two Shorts cut out of every long video.
- `/channel-admin` fills in the details for whatever I just uploaded and schedules it.
- `/channel-cleanup` checks that uploads really exist on YouTube and moves the local files to a `_to_delete` folder.

I started with one big skill that did everything. It got long and messy fast. Splitting it up made each part easier to fix, and I can run research or production on their own when I want.

A small Python CLI. `ytool.py` talks to the official YouTube Data API. No browser automation, nothing that clicks around YouTube pretending to be me. I didn't want to risk the channels.

## The upload trick

This is the part I'm happiest with.

My first plan was to upload everything through the API. That technically works, but YouTube can lock videos uploaded from an unaudited Google Cloud project to private. Getting a project audited is a whole process.

Then I noticed YouTube keeps the original file name of every upload. So now Claude puts finished videos in one folder per channel, and I drag that folder into Studio and close the window without typing anything. Afterwards `/channel-admin` lists my private, unscheduled uploads, matches each one to its queue record by file name, and fills in the title, description, tags, thumbnail and publish time.

Dragging a folder takes ten seconds. Everything I used to type by hand is gone.

The one rule: don't rename the files.

## Things that went wrong

Plenty did.

While testing the upload command, it actually uploaded an empty video called "test" to one of my channels. It had to be deleted by hand in Studio, and that command is gone now.

When I moved my old files into the new structure, some old plan files said 22 videos were "uploaded". They weren't on YouTube at all. If I had trusted the plan, those would have been lost or uploaded twice. Now nothing gets marked as done until it's checked against the API.

Scheduling also bit me. A slot that was free in the morning can be taken by the time I upload, because I sometimes schedule something by hand in between. So the finalize step now reloads the channel's whole schedule right before setting the publish time. If that minute is taken, or already in the past, it moves the video to the same time on the next free day and tells me why. When I moved 83 old unuploaded videos into the queue, this is what spread them out without collisions.

One night a preview played out loud on my laptop. Now every skill has the same rule: never play audio or video on my machine. Checks are done silently with `ffprobe`, loudness analysis and a few still frames.

And the cleanup alone freed about 81 GB on my Desktop. I didn't know I was keeping that much junk.

## Reports, with reasons

The first versions just said things like "3 Shorts produced". That told me nothing about whether to trust the result.

Now every skill has to end with a report that explains itself. Research has to list which competitors it looked at and why those, which videos broke out and by how much, what people keep asking in the comments, why it picked each idea, and every source with a date. Production has to show the top three titles with scores, where each fact came from, which voice it used, and the technical checks. The report lands in the chat, in a `reports/` folder and in the panel.

This changed how I use the system more than anything else. I actually read the reports, and when something looks off I can see where it came from.

## A few rules the videos follow

No slideshows. Real stock footage with licences that allow reuse, lots of cuts, and a different voice and caption style for each video made on the same day. No copyrighted music or clips. Comment replies are drafted, but they wait in the panel until I approve them, unless I switch that off.

## Try it

```
skills/            the five skills
tools/ytool.py     YouTube Data API CLI
panel/panel.html   the planning panel (Claude Artifact with a database)
config/            example config: your channels, niches and rules
docs/              diagram and screenshot
```

1. In Google Cloud, enable YouTube Data API v3, set up an OAuth consent screen with yourself as a test user, and create an OAuth client of type Desktop app. Save the JSON as `$YT_HOME/client_secret.json`.
2. Authorize each channel:
   ```bash
   export YT_HOME=~/youtube/_system
   python3 tools/ytool.py auth-url my-channel
   python3 tools/ytool.py auth-code my-channel "http://localhost:8765/?code=..."
   python3 tools/ytool.py calendar my-channel
   ```
3. Copy `config/config.example.json` to `$YT_HOME/config.json` and describe your channels.
4. Ask Claude to publish `panel/panel.html` as an Artifact with a database, add your channels, and put its URL in the config.
5. Add the skills and type `/channel-ops`.

Don't commit `client_secret.json` or the `tokens/` folder. The `.gitignore` already skips them.

If you build something with it, or find a better way to do the upload part, I'd like to hear about it.
