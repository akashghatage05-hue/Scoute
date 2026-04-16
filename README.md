# SCOUTE — AI Music Intelligence, India

India's first AI music intelligence platform. SCOUTE monitors Indian music communities on Reddit daily, scores artists by the gap between their underground buzz and global reach, and matches them with relevant Spotify playlist curators.

**Find Indian artists before they blow up.**

Live demo: [scoute-production.up.railway.app](https://scoute-production.up.railway.app)

---

## The Problem

- Indie artists spend hours cold-emailing playlist curators with near-zero success rates
- Managers and labels miss breakout talent until it's too late and too expensive
- Curators are flooded with irrelevant pitches that don't match their playlist's sound

SCOUTE solves all three sides of this problem.

---

## How It Works

Three agents run in sequence:

### 1. Scout Agent
Monitors Indian and global music subreddits daily using Reddit's public JSON feeds — no API key needed.

**Indian subreddits:**
`r/IndianHipHop` · `r/hindimusic` · `r/IndianaMusic` · `r/bollywood` · `r/IndieIndia` · `r/sangheats` · `r/desirap`

**Global subreddits:**
`r/hiphopheads` · `r/indieheads` · `r/listentothis` · `r/rnb` · `r/electronicmusic` · `r/undergroundhiphop` · `r/afrobeats` · `r/kpop` · `r/bedroom_pop` · and more

Parses post titles using the standard `Artist — Song [genre]` format, strips prefixes like `[FRESH]` and `[VIDEO]`, and scores each track by upvotes + comment count.

### 2. Arbitrage Agent
Scores every artist using the **Breakout Score**:

```
Breakout Score = log(Reddit Score) / log(Deezer Fans)
```

High Reddit buzz + low Deezer fans = underground gem about to break. Pulls fan counts from the Deezer public API (no key needed) and Spotify profile URLs for quick listening links.

### 3. Ghostwriter Agent
Matches top-scoring artists with relevant Spotify playlist curators by genre. The curator database contains 12 real Indian music playlists (10k–500k followers), sourced from Spotify searches for "hindi indie", "indian hip hop", "desi beats", "indian indie", "bollywood indie", and "indian rap".

**Auto-generated pitch emails are coming soon** (requires Anthropic credits).

---

## Pipeline Flow

```
Reddit hot.json feeds (27 subreddits)
        │
        ▼
   Scout Agent
   Parses "Artist - Song [genre]" titles
   Scores by upvotes + comment count
        │
        ▼  scoute/data/scout_results.json
        │
   Arbitrage Agent
   Deezer fan lookup → Breakout Score
   High buzz / low fans = opportunity
        │
        ▼  scoute/data/arbitrage_results.json
        │
   Ghostwriter Agent
   Genre-based curator matching
   (Email generation: coming soon)
        │
        ▼  scoute/outputs/emails/
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Reddit data | Public `.json` feeds — no API key needed |
| Artist data | Deezer public API — no API key needed |
| Curator search | Spotify Web API |
| Cloud data sync | JSONbin.io |
| Deployment | Railway |
| Email generation | Anthropic Claude API (coming soon) |
| Development | Claude Code |

---

## Project Structure

```
scoute/
├── scoute/
│   ├── agents/
│   │   ├── scout.py          # Reddit crawler — 27 subreddits, RSS fallback
│   │   ├── arbitrage.py      # Deezer + Reddit Breakout Score engine
│   │   └── ghostwriter.py    # Curator database + Claude email writer
│   ├── data/                 # Runtime JSON outputs (gitignored)
│   │   ├── scout_results.json
│   │   ├── arbitrage_results.json
│   │   └── real_curators.json
│   ├── outputs/
│   │   └── emails/           # Generated pitch emails (.md)
│   ├── storage.py            # JSONbin read/write helpers
│   └── jsonbin_store.py
├── scripts/
│   └── find_real_curators.py # Spotify API — finds real curators by genre
├── dashboard.py              # Flask web dashboard
├── main.py                   # Pipeline orchestrator
├── requirements.txt
├── Procfile                  # Railway entry point
├── runtime.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/akashghatage05-hue/Scoute.git
cd Scoute
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Required | Used for | Where to get it |
|---|---|---|---|
| `SPOTIFY_CLIENT_ID` | Yes | Curator search script | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Yes | Curator search script | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| `ANTHROPIC_API_KEY` | For emails only | Ghostwriter Agent | [console.anthropic.com](https://console.anthropic.com) |
| `JSONBIN_KEY` | For cloud sync | Sync data to Railway | [jsonbin.io](https://jsonbin.io) → API Keys |
| `ADMIN_PASSWORD` | Optional | Waitlist admin page | Any string you choose |

Reddit and Deezer require **no API keys**. The Scout and Arbitrage agents work out of the box.

### 3. Run the pipeline

```bash
# Full pipeline — Scout → Arbitrage → Ghostwriter
python main.py

# Single agent
python main.py --agent scout       # Reddit crawl only
python main.py --agent arbitrage   # Scoring only (reads scout_results.json)
python main.py --agent ghost       # Email matching only (reads arbitrage_results.json)
```

### 4. Run the dashboard

```bash
python dashboard.py
```

Open [http://localhost:5000](http://localhost:5000).

### 5. Find new curators (optional)

Edit `scripts/find_real_curators.py` to change the `GENRES` search terms, then:

```bash
python scripts/find_real_curators.py
```

Requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`.

---

## Roadmap

- [ ] **Email generation** — auto-write personalised curator pitch emails via Claude API (blocked on Anthropic credits)
- [ ] **Real curator contacts** — manual research to add submission links and emails to the curator database
- [ ] **More Indian subreddits** — expand coverage as new communities grow
- [ ] **TikTok and YouTube signals** — add video virality as a second signal layer
- [ ] **User accounts and payments** — artists pay to unlock email generation and curator matching
- [ ] **Twitter/X integration** — trending music hashtags as supplementary signal

---

## Current Status

**Working prototype.** The Scout and Arbitrage agents run reliably and the live dashboard shows real data. The curator matching UI (Match Curators button) works with the 12 Indian Spotify playlists in the database.

Email generation is implemented in `ghostwriter.py` but disabled in production — it requires an active Anthropic API key with credits. The waitlist on the Emails page is live and collecting signups.

The platform is deployed and running at [scoute-production.up.railway.app](https://scoute-production.up.railway.app).
