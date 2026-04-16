"""
Ghostwriter Agent
-----------------
Writes personalized cold pitch emails to playlist curators on behalf of indie artists.

Strategy:
  - Takes Arbitrage Agent output (high-opportunity artists) as input
  - Pulls curator data: playlist name, follower count, genre tags, submission history
  - Uses Claude API to generate a tailored, non-spammy pitch email per curator
  - Saves drafts to outputs/emails/ for human review before sending

Output: one .txt or .md file per email in outputs/emails/
  Format: outputs/emails/{artist_slug}_{curator_slug}_{date}.md

Email structure:
  1. Subject line (A/B variant included)
  2. Opening hook referencing the curator's specific playlist
  3. Artist bio (2 sentences max)
  4. Streaming stats + regional traction (from arbitrage data)
  5. Track recommendation + one-line pitch
  6. Clear CTA — no pressure, easy reply
  7. Links: Spotify, SubmitHub (if applicable)
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

# Output directory for generated emails
EMAIL_OUTPUT_DIR = "scoute/outputs/emails"

# Claude model to use for generation
CLAUDE_MODEL = "claude-opus-4-6"

# Curator database — real Spotify playlists scraped 2026-04-16
# Source: scripts/find_real_curators.py (10,000–500,000 followers, Indian music searches)
# submission_pref and contact must be researched manually per curator.
SAMPLE_CURATORS = [

    # ── Hindi indie / bollywood indie (3) ────────────────────────────────────
    {
        "name": "Travel Songs (Hindi) | Bollywood Roadtrip Hindi | Indie Travels",
        "curator": "Aesthetic Gaane",
        "platform": "Spotify",
        "followers": 223089,
        "genres": ["hindi indie", "bollywood", "indian indie"],
        "submission_pref": "Hindi travel and road-trip vibes. Pitch melodic, feel-good Hindi indie tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/3IpDoXyKOPgxJvUJYsagyM",
    },
    {
        "name": "Hindi Pop Songs",
        "curator": "mahimarajvirsingh",
        "platform": "Spotify",
        "followers": 44237,
        "genres": ["hindi pop", "bollywood", "hindi indie"],
        "submission_pref": "Popular Hindi pop. Pitch catchy, contemporary Hindi tracks with broad appeal.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/2PAqtb7l2I7qQfMZ3HAvwQ",
    },
    {
        "name": "hIndie",
        "curator": "Rajanand Lonkar",
        "platform": "Spotify",
        "followers": 21979,
        "genres": ["hindi indie", "indian indie", "indie pop"],
        "submission_pref": "Curated Hindi indie discoveries. Pitch emerging Indian artists with original sound.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/6dqSUaCBtM5O5uB17pMwOx",
    },

    # ── Indian hip hop / desi rap (2) ─────────────────────────────────────────
    {
        "name": "Trending Hindi Rap Songs 2026 \u2022 Best Hindi Rap Songs",
        "curator": "i lovemusic",
        "platform": "Spotify",
        "followers": 21549,
        "genres": ["indian hip hop", "hindi rap", "desi rap"],
        "submission_pref": "Current Hindi rap and trap. Pitch new Indian rap releases with strong hooks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0Y4bUX4CmHmHBGMGl5kTYs",
    },
    {
        "name": "EK Number Hip Hop (Indian Hip Hop Hits)",
        "curator": "Radial India",
        "platform": "Spotify",
        "followers": 13310,
        "genres": ["indian hip hop", "desi hip hop", "hip hop"],
        "submission_pref": "Best of Indian hip hop. Pitch quality desi hip hop with strong bars and production.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/5F8CSMQKK7pIKxzZwTFp3d",
    },

    # ── Desi beats / party (3) ────────────────────────────────────────────────
    {
        "name": "Desi songs which make you wanna chammak challo",
        "curator": "Moxie",
        "platform": "Spotify",
        "followers": 79305,
        "genres": ["desi beats", "bollywood", "indian pop"],
        "submission_pref": "High-energy desi bangers. Pitch upbeat Indian tracks built for dancing and vibes.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/6kO2BzLITX9a6HEUSDCAvS",
    },
    {
        "name": "INDIAN PARTY HITS",
        "curator": "Aliyah",
        "platform": "Spotify",
        "followers": 17384,
        "genres": ["indian pop", "bollywood", "desi rap"],
        "submission_pref": "Indian party playlist spanning Bollywood and desi rap. Pitch crowd-pleasing Indian bangers.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/2hBKJPwmU90BZeo38tKGXo",
    },
    {
        "name": "Desi Party",
        "curator": "shenaeze",
        "platform": "Spotify",
        "followers": 12356,
        "genres": ["desi beats", "bhangra", "bollywood"],
        "submission_pref": "Desi party anthems. Pitch bhangra-influenced or high-energy Indian dance tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/57AAwzBOUfqAYDs36pn5NT",
    },

    # ── Indian rap / remix (2) ────────────────────────────────────────────────
    {
        "name": "\ud83c\uddee\ud83c\uddf3Indian remix\ud83c\uddee\ud83c\uddf3",
        "curator": "Bertram O'Reilly Poulsen",
        "platform": "Spotify",
        "followers": 177658,
        "genres": ["indian rap", "bollywood remix", "desi beats"],
        "submission_pref": "Indian remixes and rap tracks. Pitch bold remixes or rap-infused Indian productions.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/4TwPUSsqgK1BYQxatjvfPL",
    },
    {
        "name": "Indian meme music",
        "curator": "Aksel",
        "platform": "Spotify",
        "followers": 54514,
        "genres": ["indian rap", "desi hip hop", "indian pop"],
        "submission_pref": "Viral Indian tracks with internet cultural appeal. Pitch tracks with meme or social-media momentum.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/2klzGhzIW5IVrBXhwId8gg",
    },

    # ── Bollywood / Indian indie (2) ─────────────────────────────────────────
    {
        "name": "Best Hindi Songs of All Time 2025",
        "curator": "Rohit",
        "platform": "Spotify",
        "followers": 28439,
        "genres": ["bollywood", "hindi pop", "indian indie"],
        "submission_pref": "Best-of Hindi music curation. Pitch timeless or modern Hindi tracks with strong emotional pull.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/6jyIEc6gUd2yFJOlFMc9Nb",
    },
    {
        "name": "Famous Indian Song",
        "curator": "Carlo.Chua",
        "platform": "Spotify",
        "followers": 25198,
        "genres": ["indian indie", "bollywood", "indian pop"],
        "submission_pref": "Iconic Indian songs. Pitch standout Indian tracks that feel timeless or culturally significant.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/48ENNm8esDEe3pSu30HYsz",
    },
]


def slugify(text: str) -> str:
    """Convert a string to a URL/filename-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_prompt(artist: dict, curator: dict) -> str:
    """
    Construct the Claude prompt that generates the pitch email.
    Artist data comes from the Arbitrage Agent output.
    """
    return f"""You are a music industry PR specialist writing a cold pitch email to a playlist curator.

CURATOR DETAILS:
- Playlist: {curator['name']}
- Curator name: {curator['curator']}
- Platform: {curator['platform']}
- Followers: {curator['followers']:,}
- Genres they cover: {', '.join(curator['genres'])}
- Submission preferences: {curator['submission_pref']}

ARTIST DETAILS:
- Artist name: {artist['artist']}
- Hot regions (strong streaming traction): {', '.join(artist.get('hot_regions', []))}
- Global Spotify followers: {artist.get('global_followers', 0):,}
- Arbitrage score (0-1, higher = bigger undiscovered gap): {artist.get('arbitrage_score', 0)}
- Spotify URL: {artist.get('spotify_url', 'N/A')}

INSTRUCTIONS:
Write a cold pitch email with the following structure:
1. Subject line (provide 2 A/B variants labeled [A] and [B])
2. Personalized opening that references the curator's specific playlist — show you've actually listened
3. 2-sentence artist bio emphasizing the regional momentum angle
4. Key stats: regional streams, follower count, arbitrage opportunity framing
5. One-line pitch for the specific track
6. Soft CTA — no pressure, make it easy to say yes or just reply
7. Signature block with Spotify link

Tone: professional but human. Not salesy. Max 250 words in the body.
Output only the email — no commentary before or after."""


def generate_email(artist: dict, curator: dict, client: anthropic.Anthropic) -> str:
    """
    Call Claude API to generate the pitch email.

    TODO:
      - Add retry logic for API rate limits
      - Add temperature tuning for stylistic variety across batches
      - Optionally stream the response for real-time preview
    """
    prompt = build_prompt(artist, curator)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def save_email(content: str, artist: dict, curator: dict) -> str:
    """Write the generated email to a file and return the file path."""
    os.makedirs(EMAIL_OUTPUT_DIR, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y%m%d")
    artist_slug = slugify(artist["artist"])
    curator_slug = slugify(curator["name"])
    filename = f"{artist_slug}_{curator_slug}_{date_str}.md"
    filepath = os.path.join(EMAIL_OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Pitch: {artist['artist']} → {curator['name']}\n\n")
        f.write(f"**Generated:** {datetime.utcnow().isoformat()}\n\n")
        f.write("---\n\n")
        f.write(content)
    logger.info(f"Email saved: {filepath}")
    return filepath


def run(opportunities: list[dict]) -> list[str]:
    """
    Entry point called by main.py.
    Generates one email per (artist, curator) pair and returns list of saved file paths.

    TODO:
      - Load curator list from a real database or CSV instead of SAMPLE_CURATORS
      - Match curators to artists by genre affinity (embedding similarity)
      - Add deduplication so the same artist isn't pitched to the same curator twice
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=api_key)
    saved_files = []

    for artist in opportunities:
        # Match curators whose genres overlap with the artist's hot regions/genre tags
        # For now, pitch every artist to every curator (replace with smart matching)
        matched_curators = SAMPLE_CURATORS

        for curator in matched_curators:
            logger.info(f"Generating email: {artist['artist']} -> {curator['name']}")
            email_content = generate_email(artist, curator, client)
            filepath = save_email(email_content, artist, curator)
            saved_files.append(filepath)

    logger.info(f"Ghostwriter Agent complete - {len(saved_files)} emails generated.")

    # Push emails to JSONbin so Railway dashboard can read them
    if saved_files and os.environ.get("JSONBIN_KEY"):
        try:
            from scoute.storage import push_to_jsonbin
            email_records = []
            for fp in saved_files:
                p = Path(fp) if not hasattr(fp, 'name') else fp
                p = Path(fp)
                parts = p.stem.split("_")
                artist = parts[0].replace("-", " ").title() if parts else p.stem
                curator = parts[1].replace("-", " ").title() if len(parts) > 1 else ""
                raw_date = parts[2] if len(parts) > 2 else ""
                date_fmt = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date
                content = p.read_text(encoding="utf-8") if p.exists() else ""
                email_records.append({
                    "filename": p.name,
                    "artist": artist,
                    "curator": curator,
                    "date": date_fmt,
                    "content": content,
                })
            push_to_jsonbin(email_records, "emails_list")
        except Exception as exc:
            logger.warning(f"Failed to push emails to JSONbin: {exc}")

    return saved_files
