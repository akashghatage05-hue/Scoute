"""
Arbitrage Agent
---------------
For each artist found by the Scout Agent, cross-references two data sources:

  1. Deezer public API (no key needed) — global fan count as a reach proxy
  2. Scout Agent Reddit score — current social buzz

Arbitrage score = log10(reddit_score + 1) / log10(deezer_fans + 10)

High Reddit buzz + low Deezer fans = undiscovered artist worth watching.
Spotipy is used only to resolve a Spotify profile URL for each artist.

Output: saves to scoute/data/arbitrage_results.json
"""

import json
import logging
import math
import os
import time
from datetime import datetime, timezone

import requests
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

logger = logging.getLogger(__name__)

SCOUT_RESULTS_PATH = "scoute/data/scout_results.json"
OUTPUT_PATH = "scoute/data/arbitrage_results.json"

DEEZER_SEARCH = "https://api.deezer.com/search/artist"
DEEZER_HEADERS = {"User-Agent": "scoute-bot/1.0"}

# ── Filters ──────────────────────────────────────────────────────────────────
# Artists with fewer fans than this are likely Deezer mismatches (wrong artist
# returned because the name is too generic or the real artist isn't on Deezer).
MIN_DEEZER_FANS = 100

# Artists above this threshold are already mainstream — not an arbitrage opportunity.
MAX_DEEZER_FANS = 200_000

# Single-word names under 4 chars, or names made entirely of common generic words,
# are almost certainly bad title parses ("magic", "move", "body", etc.).
GENERIC_WORDS = {
    "magic", "move", "body", "love", "new", "feel", "good", "real",
    "live", "free", "play", "soul", "fire", "gold", "rise", "wild",
    "light", "dark", "blue", "red", "gone", "stay", "run", "fly",
}

def _is_valid_artist_name(name: str) -> bool:
    """Return False if the name is too short or made up entirely of generic words."""
    if len(name.strip()) < 4:
        return False
    words = set(name.lower().split())
    if words and words.issubset(GENERIC_WORDS):
        return False
    return True


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def _spotify_client() -> spotipy.Spotify:
    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        )
    )


def fetch_deezer_artist(name: str) -> dict | None:
    """
    Search Deezer for an artist by name (no API key required).
    Returns the top result dict with nb_fan, or None if not found.
    """
    try:
        resp = requests.get(
            DEEZER_SEARCH,
            params={"q": name, "limit": 1},
            headers=DEEZER_HEADERS,
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return data[0] if data else None
    except Exception as e:
        logger.warning(f"Deezer lookup failed for '{name}': {e}")
        return None


def fetch_spotify_url(sp: spotipy.Spotify, name: str) -> str:
    """
    Search Spotify for an artist and return their profile URL.
    Used only for the output link — no follower/popularity data needed.
    """
    try:
        results = sp.search(q=f"artist:{name}", type="artist", limit=1)
        items = results.get("artists", {}).get("items", [])
        if items:
            return items[0]["external_urls"].get("spotify", "")
    except Exception as e:
        logger.debug(f"Spotify URL lookup failed for '{name}': {e}")
    return ""


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_arbitrage_score(reddit_score: int, deezer_fans: int) -> float:
    """
    Score = log10(reddit_score + 1) / log10(deezer_fans + 10)

    - High reddit_score + low deezer_fans → high score (hidden gem)
    - High reddit_score + high deezer_fans → lower score (already mainstream)
    - log10 on both sides keeps the scale balanced for very large numbers.
    """
    return round(math.log10(reddit_score + 1) / math.log10(deezer_fans + 10), 4)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def find_arbitrage_opportunities(scout_tracks: list[dict]) -> list[dict]:
    """
    For each unique artist in scout_tracks, fetch Deezer fan count and
    compute the arbitrage score against their Reddit buzz score.
    """
    sp = _spotify_client()

    # Deduplicate artists — keep the highest Reddit-scored track per artist
    seen: dict[str, dict] = {}
    for track in scout_tracks:
        artist = track.get("artist", "").strip()
        if not artist:
            continue
        key = artist.lower()
        if key not in seen or track.get("score", 0) > seen[key].get("score", 0):
            seen[key] = track

    opportunities = []

    for key, track in seen.items():
        artist_name = track["artist"]
        reddit_score = track.get("score", 0)

        # Filter 3 — skip bad parses before hitting any API
        if not _is_valid_artist_name(artist_name):
            logger.debug(f"  Skipping '{artist_name}' — generic or too-short name.")
            continue

        logger.info(f"Looking up: {artist_name} (reddit score: {reddit_score})")

        deezer = fetch_deezer_artist(artist_name)
        if not deezer:
            logger.debug(f"  No Deezer result — skipping.")
            continue

        deezer_fans = deezer.get("nb_fan", 0)
        deezer_url = deezer.get("link", "")

        # Filter 1 — too few fans means Deezer returned the wrong artist
        if deezer_fans < MIN_DEEZER_FANS:
            logger.debug(f"  Skipping '{artist_name}' — only {deezer_fans} Deezer fans (likely mismatch).")
            continue

        # Filter 2 — too many fans means already mainstream
        if deezer_fans > MAX_DEEZER_FANS:
            logger.debug(f"  Skipping '{artist_name}' — {deezer_fans:,} Deezer fans (already mainstream).")
            continue
        arb_score = compute_arbitrage_score(reddit_score, deezer_fans)

        spotify_url = fetch_spotify_url(sp, artist_name)

        opportunities.append({
            "artist": artist_name,
            "deezer_fans": deezer_fans,
            "reddit_score": reddit_score,
            "arbitrage_score": arb_score,
            "deezer_url": deezer_url,
            "spotify_url": spotify_url,
            "subreddit": track.get("subreddit", ""),
            "snapshot_date": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(0.3)  # be polite to Deezer

    # Rank by arbitrage score descending
    opportunities.sort(key=lambda x: x["arbitrage_score"], reverse=True)
    for i, opp in enumerate(opportunities, start=1):
        opp["rank"] = i

    return opportunities


def save_results(opportunities: list[dict], output_path: str = OUTPUT_PATH) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(opportunities, f, indent=2)
    logger.info(f"Saved {len(opportunities)} opportunities to {output_path}")


def run(scout_tracks: list[dict] | None = None) -> list[dict]:
    """
    Entry point called by main.py.
    If scout_tracks is not provided, loads from scoute/data/scout_results.json.
    """
    if scout_tracks is None:
        with open(SCOUT_RESULTS_PATH) as f:
            scout_tracks = json.load(f)

    opportunities = find_arbitrage_opportunities(scout_tracks)
    save_results(opportunities)
    logger.info(f"Arbitrage Agent complete — {len(opportunities)} artists ranked.")
    return opportunities
