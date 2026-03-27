"""
Scout Agent
-----------
Crawls Reddit and Twitter/X to find trending songs and emerging artists.

Data sources:
  - Reddit: r/hiphopheads, r/indieheads, r/rnb, r/trap, r/electronicmusic, etc.
  - Twitter/X: trending music hashtags, quote-tweet chains around new drops

Output: saves structured JSON to data/scout_results.json
  {
    "song": "...",
    "artist": "...",
    "source": "reddit | twitter",
    "mentions": 0,
    "sentiment": 0.0,
    "first_seen": "ISO timestamp",
    "url": "..."
  }
"""

import os
import re
import json
import logging
import time
from datetime import datetime, timezone

import requests
import tweepy

logger = logging.getLogger(__name__)

# --- Reddit config ---
SUBREDDITS = [
    "hiphopheads",
    "indieheads",
    "listentothis",
    "rnb",
    "electronicmusic",
]

REDDIT_HEADERS = {"User-Agent": "scoute-bot/1.0 by akash"}

# Most music subreddits use "Artist - Song Title [genre] (year)" in post titles.
# listentothis uses "Artist -- Song Title [genre]"
TITLE_PATTERN = re.compile(
    r"^(?P<artist>.+?)\s*[-–—]{1,2}\s*(?P<song>.+?)"  # Artist - Song
    r"(?:\s*\[(?P<genre>[^\]]+)\])?"                    # optional [genre]
    r"(?:\s*\((?P<year>\d{4})\))?$",                    # optional (year)
    re.IGNORECASE,
)

# Minimum upvote score for a post to be included
MIN_SCORE = 50

# --- Twitter/X config ---
TWITTER_QUERY = (
    "(#NewMusic OR #IndieArtist OR #HipHop OR #RnB OR #EDM) "
    "(spotify.com OR music.apple.com) "
    "lang:en -is:retweet"
)

# Regex to pull Spotify track URLs from tweet text
SPOTIFY_TRACK_RE = re.compile(r"spotify\.com/track/([A-Za-z0-9]+)")


def _twitter_client() -> tweepy.Client:
    return tweepy.Client(bearer_token=os.environ["TWITTER_BEARER_TOKEN"])


# Matches any bracketed tag at the start of a title, e.g. [FRESH], [DISCUSSION], [AMA]
REDDIT_PREFIX_RE = re.compile(r"^(\[[^\]]+\]\s*)+", re.IGNORECASE)

# Words that strongly suggest the left side of a " - " split is the song, not the artist.
# Used to detect and fix reversed "Song - Artist" titles.
_SONG_INDICATOR_WORDS = re.compile(
    r"\b(official|video|audio|lyrics|ft\.?|feat\.?|prod\.?|remix|edit|mix|version|live|acoustic|cover|remaster)\b",
    re.IGNORECASE,
)


def _parse_title(title: str) -> tuple[str, str] | None:
    """
    Extract (artist, song) from a subreddit post title.

    Steps:
      1. Strip all bracketed prefixes: [FRESH], [VIDEO], [DISCUSSION], [AMA], etc.
      2. Match "Artist - Song [genre] (year)" pattern.
      3. Detect reversed "Song - Artist" titles and swap them.
      4. Reject obviously bad parses (single chars, pure numbers, etc.)
    """
    # Step 1 — strip all leading bracketed tags
    title = REDDIT_PREFIX_RE.sub("", title.strip()).strip()

    # Step 2 — match the standard pattern
    m = TITLE_PATTERN.match(title)
    if not m:
        return None

    artist = m.group("artist").strip()
    song = m.group("song").strip()

    # Step 3 — detect reversed titles: if the "artist" side contains song-indicator
    # words (Official, Video, feat., etc.) but the "song" side does not, swap them.
    artist_looks_like_song = bool(_SONG_INDICATOR_WORDS.search(artist))
    song_looks_like_song = bool(_SONG_INDICATOR_WORDS.search(song))
    if artist_looks_like_song and not song_looks_like_song:
        artist, song = song, artist

    # Step 4 — reject bad parses
    if len(artist) < 2 or len(song) < 2:
        return None

    return artist, song


def fetch_reddit_trending(limit: int = 50) -> list[dict]:
    """
    Fetch hot posts from music subreddits using Reddit's public .json feeds.
    No API key required — uses a browser-like User-Agent header.
    Scores each track by upvotes + comment count combined.
    """
    logger.info("Fetching Reddit trending tracks...")
    tracks: list[dict] = []

    for sub_name in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit={limit}"
        try:
            resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
            resp.raise_for_status()
            posts = resp.json()["data"]["children"]
        except Exception as e:
            logger.warning(f"Error fetching r/{sub_name}: {e}")
            time.sleep(1)
            continue

        for post in posts:
            data = post["data"]

            # Skip pinned mod posts, self/text posts, and low-score posts
            if data.get("stickied"):
                continue
            if data.get("is_self"):
                continue
            if data.get("score", 0) < MIN_SCORE:
                continue

            parsed = _parse_title(data["title"])
            if not parsed:
                continue
            artist, song = parsed

            score = data.get("score", 0) + data.get("num_comments", 0)
            tracks.append({
                "artist": artist,
                "song": song,
                "source": "reddit",
                "subreddit": sub_name,
                "mentions": 1,
                "score": score,
                "upvotes": data.get("score", 0),
                "comments": data.get("num_comments", 0),
                "sentiment": 0.0,
                "first_seen": datetime.fromtimestamp(
                    data["created_utc"], tz=timezone.utc
                ).isoformat(),
                "url": data.get("url", ""),
                "reddit_url": f"https://reddit.com{data.get('permalink', '')}",
            })

        # Be polite — Reddit rate-limits aggressive crawlers
        time.sleep(1)

    logger.info(f"Reddit: {len(tracks)} tracks found across {len(SUBREDDITS)} subreddits.")
    return tracks


def fetch_twitter_trending(limit: int = 100) -> list[dict]:
    """
    Search recent tweets for music hashtags that contain Spotify or Apple Music links.
    Ranks by retweet + like count as a proxy for velocity.
    Returns a list of track dicts.
    """
    logger.info("Fetching Twitter trending tracks...")
    client = _twitter_client()
    tracks: list[dict] = []

    try:
        response = client.search_recent_tweets(
            query=TWITTER_QUERY,
            max_results=min(limit, 100),  # API max per request is 100
            tweet_fields=["created_at", "public_metrics", "entities", "author_id"],
            expansions=["author_id"],
            user_fields=["name", "username"],
        )
    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
        return []

    if not response.data:
        logger.info("No tweets returned.")
        return []

    # Build author_id → username lookup from the includes
    users = {u.id: u for u in (response.includes.get("users") or [])}

    for tweet in response.data:
        text = tweet.text
        metrics = tweet.public_metrics or {}
        engagement = metrics.get("retweet_count", 0) + metrics.get("like_count", 0)

        # Extract Spotify track ID from the tweet text/URLs
        spotify_match = SPOTIFY_TRACK_RE.search(text)
        spotify_url = (
            f"https://open.spotify.com/track/{spotify_match.group(1)}"
            if spotify_match
            else ""
        )

        # Best-effort artist/song extraction from tweet text.
        # Format commonly seen: "Artist - Song Title https://..."
        parsed = _parse_title(text)
        if parsed:
            artist, song = parsed
        else:
            # Fall back: use the author's display name as artist, leave song blank.
            # The Arbitrage Agent can enrich via Spotify metadata using the URL.
            author = users.get(tweet.author_id)
            artist = author.name if author else "Unknown"
            song = ""

        tracks.append({
            "artist": artist,
            "song": song,
            "source": "twitter",
            "mentions": 1,
            "score": engagement,
            "sentiment": 0.0,
            "first_seen": tweet.created_at.isoformat() if tweet.created_at else datetime.now(timezone.utc).isoformat(),
            "url": spotify_url or f"https://twitter.com/i/web/status/{tweet.id}",
            "tweet_id": str(tweet.id),
        })

    logger.info(f"Twitter: {len(tracks)} tracks found.")
    return tracks


def deduplicate(tracks: list[dict]) -> list[dict]:
    """Merge duplicate track entries across sources, summing mention counts."""
    seen: dict[str, dict] = {}
    for track in tracks:
        key = f"{track.get('artist', '').lower()}|{track.get('song', '').lower()}"
        if key in seen:
            seen[key]["mentions"] += track.get("mentions", 1)
            seen[key]["score"] = seen[key].get("score", 0) + track.get("score", 0)
        else:
            seen[key] = dict(track)
    results = list(seen.values())
    results.sort(key=lambda t: t.get("score", 0), reverse=True)
    return results


def save_results(tracks: list[dict], output_path: str = "scoute/data/scout_results.json") -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(tracks, f, indent=2)
    logger.info(f"Saved {len(tracks)} tracks to {output_path}")


def run() -> list[dict]:
    """Entry point called by main.py."""
    reddit_tracks = fetch_reddit_trending()
    twitter_tracks = fetch_twitter_trending()
    all_tracks = deduplicate(reddit_tracks + twitter_tracks)
    save_results(all_tracks)
    logger.info(f"Scout Agent complete — {len(all_tracks)} unique trending tracks found.")
    return all_tracks
