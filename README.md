# SCOUTE — AI Music Intelligence Platform

SCOUTE uses AI agents to surface emerging music talent before it goes mainstream, then helps indie artists get placed on playlists.

## What it does

| Agent | Job |
|---|---|
| **Scout** | Crawls Reddit & Twitter to find trending songs in real time |
| **Arbitrage** | Finds artists blowing up in one region but unknown everywhere else |
| **Ghostwriter** | Writes cold pitch emails to playlist curators on behalf of indie artists |

## Project structure

```
scoute/
├── scoute/
│   ├── agents/
│   │   ├── scout.py          # Reddit + Twitter crawler
│   │   ├── arbitrage.py      # Regional streaming gap finder
│   │   └── ghostwriter.py    # Claude-powered email writer
│   ├── data/                 # JSON outputs from Scout + Arbitrage agents
│   └── outputs/
│       └── emails/           # Generated pitch emails (.md files)
├── main.py                   # Orchestrates all three agents
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

**1. Clone and install dependencies**
```bash
git clone <repo-url>
cd scoute
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**2. Configure API keys**
```bash
cp .env.example .env
# Edit .env with your credentials
```

You'll need API keys for:
- [Anthropic](https://console.anthropic.com) — Ghostwriter Agent
- [Reddit](https://www.reddit.com/prefs/apps) — Scout Agent
- [Twitter/X Developer](https://developer.twitter.com) — Scout Agent
- [Spotify Developer](https://developer.spotify.com/dashboard) — Arbitrage Agent

**3. Run the full pipeline**
```bash
python main.py
```

**4. Run a single agent**
```bash
python main.py --agent scout       # trending tracks only
python main.py --agent arbitrage   # regional gaps only
python main.py --agent ghost       # emails only (needs prior agent output)
```

## Output

- `scoute/data/scout_results.json` — trending tracks found across Reddit + Twitter
- `scoute/data/arbitrage_results.json` — ranked arbitrage opportunities
- `scoute/outputs/emails/` — one `.md` file per generated pitch email

## Agent pipeline

```
Reddit / Twitter
      │
      ▼
 Scout Agent  ──► scout_results.json
      │
      ▼
Arbitrage Agent ──► arbitrage_results.json
      │
      ▼
Ghostwriter Agent ──► outputs/emails/*.md
```
