# SCOUTE — AI Music Intelligence, India

India's first AI music intelligence platform. SCOUTE monitors Indian and global music communities on Reddit daily, scores artists by the gap between their underground buzz and global reach, and matches them with relevant Spotify playlist curators.

**Find Indian artists before they blow up.**

---

## The Problem

The Indian independent music scene is growing fast — but discovery is still broken:

- Indie artists spend hours cold-emailing playlist curators with near-zero success rates
- Managers and labels miss breakout Indian talent until it's too late and too expensive
- Curators are flooded with irrelevant pitches that don't match their playlist's sound

SCOUTE solves all three sides of this problem by automating the intelligence layer.

---

## How It Works

Three agents run in sequence:

### 1. Scout Agent
Monitors 28 Reddit music communities daily using Reddit's public JSON feeds — no API key needed.

**Indian subreddits:**
`r/IndianHipHop` · `r/hindimusic` · `r/IndianaMusic` · `r/bollywood` · `r/IndieIndia` · `r/sangheats` · `r/desirap`

**Global subreddits:**
`r/hiphopheads` · `r/indieheads` · `r/listentothis` · `r/rnb` · `r/electronicmusic` · `r/undergroundhiphop` · `r/chicagorap` · `r/ukdrill` · `r/afrobeats` · `r/latin` · `r/kpop` · `r/jmusic` · `r/bedroom_pop` · `r/poppunkers` · `r/emo` · `r/metalcore` · `r/DJs` · `r/funk` · `r/soul` · `r/jazz` · `r/futurebeats`

Parses post titles using the standard `Artist — Song [genre]` format, strips prefixes like `[FRESH]` and `[VIDEO]`, and scores each track by upvotes + comment count.

### 2. Arbitrage Agent
Scores every artist using the **Breakout Score**:

```
Breakout Score = log(Reddit Score) / log(Deezer Fans)
```

High Reddit buzz + low Deezer fans = underground artist about to break. Pulls fan counts from the Deezer public API (no key needed).

### 3. Ghostwriter Agent
Matches top-scoring artists with relevant Spotify playlist curators by genre. The curator database contains 12 real Indian music playlists (10k–500k followers), sourced from Spotify searches across "hindi indie", "indian hip hop", "desi beats", "indian indie", "bollywood indie", and "indian rap".

**Auto-generated pitch emails are coming soon** (requires Anthropic API credits).

---

## Pipeline Flow

```
Reddit hot.json feeds (28 subreddits, no API key needed)
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
   (Email auto-generation: coming soon)
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
| Cloud data sync | JSONbin.io (optional) |
| Email generation | Anthropic Claude API (coming soon) |
| Development | Claude Code |

---

## Project Structure

```
scoute/
├── scoute/
│   ├── agents/
│   │   ├── scout.py          # Reddit crawler — 28 subreddits, RSS fallback
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
├── .env.example
└── README.md
```

---

## Running Locally

### 1. Clone and install

```bash
git clone https://github.com/akashghatage05-hue/Scoute.git
cd Scoute
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Required | Used for | Where to get it |
|---|---|---|---|
| `SPOTIFY_CLIENT_ID` | Yes | Curator search script | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Yes | Curator search script | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| `ANTHROPIC_API_KEY` | For emails only | Ghostwriter Agent | [console.anthropic.com](https://console.anthropic.com) |
| `JSONBIN_KEY` | Optional | Sync data across sessions | [jsonbin.io](https://jsonbin.io) → API Keys |
| `ADMIN_PASSWORD` | Optional | Waitlist admin page | Any string you choose |

Reddit and Deezer require **no API keys**. The Scout and Arbitrage agents work out of the box.

### 3. Run the pipeline

```bash
python main.py
```

This runs all three agents in sequence: Scout → Arbitrage → Ghostwriter.

```bash
# Or run a single agent
python main.py --agent scout       # Reddit crawl only
python main.py --agent arbitrage   # Scoring only (reads scout_results.json)
python main.py --agent ghost       # Curator matching only
```

### 4. Run the dashboard

```bash
python dashboard.py
```

Open **http://127.0.0.1:5000** in your browser.

### 5. Find new curators (optional)

```bash
python scripts/find_real_curators.py
```

Edit the `GENRES` list in the script to search for different music categories. Requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.

---

## Roadmap

- [ ] **Email generation** — auto-write personalised curator pitch emails via Claude API (blocked on Anthropic credits)
- [ ] **Real curator contacts** — research and add submission links and direct emails to the curator database
- [ ] **Mobile app** — iOS/Android app for artists to access SCOUTE on the go
- [ ] **More Indian subreddits** — expand coverage as new communities grow
- [ ] **TikTok and YouTube signals** — add video virality as a second signal layer
- [ ] **User accounts and payments** — artists pay to unlock email generation and curator matching

---

## Current Status

| Feature | Status |
|---|---|
| Scout Agent (Reddit crawler) | Working |
| Arbitrage Agent (Breakout Score) | Working |
| Web Dashboard | Working |
| Curator Matching (genre-based) | Working |
| Waitlist | Working |
| Email generation | Coming soon (needs Anthropic credits) |
| Real curator contact database | Coming soon |
| Mobile app | Coming soon |

Run `python main.py` then `python dashboard.py` and open http://127.0.0.1:5000 to see it live.
