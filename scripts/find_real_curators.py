"""
scripts/find_real_curators.py
------------------------------
Uses Spotify API to find real playlist curators per genre.

Searches Spotify playlists for each target genre, filters by follower count,
and saves the top 5 per genre to scoute/data/real_curators.json.

Usage:
    python scripts/find_real_curators.py

Requires:
    SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env
"""

import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

GENRES = [
    "hip hop",
    "soul",
    "indie pop",
    "electronic",
    "R&B",
    "funk",
    "metalcore",
    "k-pop",
]

MIN_FOLLOWERS = 10_000
MAX_FOLLOWERS = 500_000
TOP_N = 5
OUTPUT_PATH = Path("scoute/data/real_curators.json")


# ── Spotify auth ──────────────────────────────────────────────────────────────

def get_token() -> str:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {creds}"},
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def spotify_get(token: str, path: str, params: dict = None) -> dict:
    resp = requests.get(
        f"https://api.spotify.com/v1{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Fetch playlists for a genre ───────────────────────────────────────────────

def search_playlists(token: str, genre: str) -> list[dict]:
    results = []
    try:
        data = spotify_get(token, "/search", {
            "q": genre,
            "type": "playlist",
            "market": "US",
            "limit": 10,
        })
    except Exception as e:
        print(f"  [!] Search failed for '{genre}': {e}")
        return []

    items = data.get("playlists", {}).get("items", []) or []

    for pl in items:
        if not pl:
            continue
        pl_id = pl.get("id")
        if not pl_id:
            continue

        # Fetch full playlist to get follower count
        try:
            full = spotify_get(token, f"/playlists/{pl_id}", {
                "fields": "id,name,followers,owner,external_urls",
                "market": "US",
            })
            followers = full.get("followers", {}).get("total", 0) or 0
        except Exception:
            continue

        if not (MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS):
            continue

        owner = full.get("owner", {})
        results.append({
            "playlist_name": full.get("name", ""),
            "owner_name": owner.get("display_name") or owner.get("id", ""),
            "followers": followers,
            "genre": genre,
            "spotify_url": full.get("external_urls", {}).get("spotify", ""),
            "playlist_id": pl_id,
        })

    results.sort(key=lambda x: x["followers"], reverse=True)
    return results[:TOP_N]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Getting Spotify access token...")
    token = get_token()
    print("Token OK.\n")

    all_curators = []

    for genre in GENRES:
        print(f"Searching: {genre}")
        playlists = search_playlists(token, genre)
        print(f"  Found {len(playlists)} matching playlists")
        all_curators.extend(playlists)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(all_curators, indent=2), encoding="utf-8")
    print(f"\nSaved {len(all_curators)} curators to {OUTPUT_PATH}")

    print("\n" + "=" * 92)
    print(f"{'#':<4} {'Playlist':<35} {'Owner':<22} {'Followers':>10}  {'Genre'}")
    print("=" * 92)
    for i, c in enumerate(all_curators, 1):
        name = c["playlist_name"][:34].encode("ascii", "replace").decode()
        owner = c["owner_name"][:21].encode("ascii", "replace").decode()
        print(f"{i:<4} {name:<35} {owner:<22} {c['followers']:>10,}  {c['genre']}")
    print("=" * 92)


if __name__ == "__main__":
    main()
