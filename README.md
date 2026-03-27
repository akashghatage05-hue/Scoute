# SCOUTE — AI Music Intelligence Platform

SCOUTE uses three AI agents to surface emerging music talent before it goes mainstream, then helps indie artists get placed on playlists.

## What it does

| Agent | Job | Data source |
|---|---|---|
| **Scout** | Finds trending songs across music subreddits | Reddit public JSON feeds — no API key needed |
| **Arbitrage** | Ranks artists by buzz-to-footprint gap | Deezer public API — no API key needed |
| **Ghostwriter** | Writes cold pitch emails to playlist curators | Claude API (Anthropic) |

## How the pipeline works

```
Reddit hot.json feeds (5 subreddits)
        │
        ▼
   Scout Agent
   - Fetches hot posts from r/hiphopheads, r/indieheads,
     r/listentothis, r/rnb, r/electronicmusic
   - Parses "Artist - Song [genre]" titles
   - Strips [FRESH], [VIDEO], [DISCUSSION] prefixes
   - Scores by upvotes + comment count
        │
        ▼ scoute/data/scout_results.json
        │
   Arbitrage Agent
   - Looks up each artist on Deezer (fan count as global reach proxy)
   - Fetches Spotify profile URL via Spotipy (URL only, no chart data)
   - Arbitrage score = log10(reddit_score + 1) / log10(deezer_fans + 10)
   - High Reddit buzz + low Deezer fans = hidden gem
        │
        ▼ scoute/data/arbitrage_results.json
        │
   Ghostwriter Agent
   - Matches top artists to curator profiles by genre
   - Calls Claude API to generate personalised pitch emails
   - Each email: 2 subject line variants, artist bio, stats, soft CTA
        │
        ▼ scoute/outputs/emails/{artist}_{curator}_{date}.md
```

## Project structure

```
scoute/
├── scoute/
│   ├── agents/
│   │   ├── scout.py          # Reddit JSON feed crawler
│   │   ├── arbitrage.py      # Deezer + Reddit scoring engine
│   │   └── ghostwriter.py    # Claude-powered email writer
│   ├── data/                 # Runtime JSON outputs (gitignored)
│   └── outputs/
│       └── emails/           # Generated pitch emails (.md)
├── main.py                   # Orchestrates all three agents
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure API keys**
```bash
cp .env.example .env
```

Only two API keys are required:

| Key | Used for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Ghostwriter Agent — generates pitch emails | [console.anthropic.com](https://console.anthropic.com) |
| `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` | Arbitrage Agent — resolves Spotify profile URLs | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |

Reddit and Twitter/X API keys are **not required**. The Scout Agent uses Reddit's public `.json` feeds with a browser user-agent header. No authentication needed.

## Running the pipeline

**Full pipeline (all 3 agents in sequence):**
```bash
python main.py
```

**Single agent:**
```bash
python main.py --agent scout       # Step 1 only
python main.py --agent arbitrage   # Step 2 only (reads scout_results.json)
python main.py --agent ghost       # Step 3 only (reads arbitrage_results.json)
```

### What a real run looks like

```
2026-03-27 [INFO] scoute.main — === SCOUTE starting full pipeline ===
2026-03-27 [INFO] scoute.main — --- Stage 1: Scout Agent ---
2026-03-27 [INFO] scout — Fetching Reddit trending tracks...
2026-03-27 [INFO] scout — Reddit: 19 tracks found across 5 subreddits.
2026-03-27 [INFO] scout — Scout Agent complete — 19 unique trending tracks found.

2026-03-27 [INFO] scoute.main — --- Stage 2: Arbitrage Agent ---
2026-03-27 [INFO] arbitrage — Looking up: Larry June (reddit score: 70)
2026-03-27 [INFO] arbitrage — Looking up: Courtney Barnett (reddit score: 133)
2026-03-27 [INFO] arbitrage — Looking up: Killer Mike (reddit score: 613)
...
2026-03-27 [INFO] arbitrage — Arbitrage Agent complete — 17 artists ranked.

2026-03-27 [INFO] scoute.main — --- Stage 3: Ghostwriter Agent ---
2026-03-27 [INFO] ghostwriter — Generating email: Robyn -> The Indie Pulse
2026-03-27 [INFO] ghostwriter — Generating email: Courtney Barnett -> The Indie Pulse
2026-03-27 [INFO] ghostwriter — Generating email: Move Your Body -> Global Sounds Weekly
...
2026-03-27 [INFO] ghostwriter — Ghostwriter Agent complete - 34 emails generated.

2026-03-27 [INFO] scoute.main — === SCOUTE pipeline complete ===
2026-03-27 [INFO] scoute.main — Trending tracks found : 19
2026-03-27 [INFO] scoute.main — Arbitrage opportunities: 17
2026-03-27 [INFO] scoute.main — Emails generated       : 34
```

### Sample arbitrage rankings (real output, 2026-03-27)

| Rank | Artist | Deezer Fans | Reddit Score | Arb Score |
|------|--------|-------------|--------------|-----------|
| 1 | Robyn | 7 | 107 | 1.6526 |
| 2 | Courtney Barnett | 25 | 133 | 1.3776 |
| 3 | Move Your Body | 51 | 71 | 1.0403 |
| 4 | Larry June | 4 | 70 | 1.6152 |
| 5 | Gelli Haha | 198 | 173 | 0.9666 |
| 6 | Killer Mike | 13,787 | 613 | 0.6735 |
| 7 | Snail Mail | 10,791 | 140 | 0.5328 |

Higher arbitrage score = more Reddit buzz relative to global footprint = better discovery opportunity.

## Output files

| File | Contents |
|---|---|
| `scoute/data/scout_results.json` | Trending tracks with source, score, subreddit, URL |
| `scoute/data/arbitrage_results.json` | Artists ranked by arbitrage score with Deezer + Reddit data |
| `scoute/outputs/emails/*.md` | Generated pitch emails, one file per artist × curator pair |
