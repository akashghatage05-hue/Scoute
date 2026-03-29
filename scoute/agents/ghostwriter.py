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

# Curator database — real Spotify playlists scraped 2026-03-29
# Source: scripts/find_real_curators.py (10,000–500,000 followers, top 5 per genre)
# submission_pref and contact must be researched manually per curator.
SAMPLE_CURATORS = [

    # ── Hip hop (3) ──────────────────────────────────────────────────────────
    {
        "name": "Hip Hop 2000s Music - Best Hip Hop Hits of the 00s Playlist",
        "curator": "Redlist Playlists",
        "platform": "Spotify",
        "followers": 261619,
        "genres": ["hip hop", "rap"],
        "submission_pref": "Curates best-of hip hop compilations. Pitch tracks with strong replay value and cultural staying power.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0dMexqq0XIWS3QJ74z3ZhD",
    },
    {
        "name": "90\u2019s & 2000\u2019s Hip Hop Bangers",
        "curator": "Johnny Thunder",
        "platform": "Spotify",
        "followers": 165658,
        "genres": ["hip hop", "rap"],
        "submission_pref": "Nostalgic hip hop. Pitch artists with a classic boom-bap or golden-era influence.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/04C2Ck8ZTVTBn54mOyaXuW",
    },
    {
        "name": "Best of HipHop (2000-2026)",
        "curator": "Quentin McCorvey Jr.",
        "platform": "Spotify",
        "followers": 72337,
        "genres": ["hip hop", "rap"],
        "submission_pref": "Broad hip hop spanning two decades. Pitch quality tracks regardless of sub-genre.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/62y3BHKehWnb1hlaPclDAA",
    },

    # ── Soul (3) ─────────────────────────────────────────────────────────────
    {
        "name": "2000s R&B & Hip-Hop Playlist",
        "curator": "RSullivan",
        "platform": "Spotify",
        "followers": 314871,
        "genres": ["soul", "r&b", "hip hop"],
        "submission_pref": "R&B and soul with crossover hip hop appeal. Pitch smooth, radio-ready tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/7kPPwcLvMqJT9iaVG8z2bv",
    },
    {
        "name": "Best Soul Of All Time",
        "curator": "Fred",
        "platform": "Spotify",
        "followers": 45109,
        "genres": ["soul", "classic soul"],
        "submission_pref": "Timeless soul music. Pitch artists with genuine emotional depth and soulful vocals.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/2tmhtyybSEvmwBCAATSt5V",
    },
    {
        "name": "Soul Eater | openings & endings",
        "curator": "AniPlaylist",
        "platform": "Spotify",
        "followers": 31755,
        "genres": ["soul", "anime"],
        "submission_pref": "Anime soundtrack and soul crossover. Pitch cinematic or emotionally charged tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/6RZCFELRNOFhrIZ1JseVKY",
    },

    # ── Indie pop (3) ────────────────────────────────────────────────────────
    {
        "name": "POOL PARTY 2026 - SUMMER HITS",
        "curator": "Filtr US",
        "platform": "Spotify",
        "followers": 82217,
        "genres": ["indie pop", "pop"],
        "submission_pref": "Upbeat summer and pop hits. Pitch feel-good, high-energy indie pop tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/4nFTwoPp8L6uato870FdW3",
    },
    {
        "name": "Best indie songs of all time",
        "curator": "Jen Affleck",
        "platform": "Spotify",
        "followers": 70997,
        "genres": ["indie pop", "indie rock", "alternative"],
        "submission_pref": "Best-of indie curation. Pitch tracks with lasting indie appeal and strong songwriting.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0Sm64Lu6z1OK8yM3Oeo4Wx",
    },
    {
        "name": "2010's Alternative/Indie Pop",
        "curator": "gabemendezm1",
        "platform": "Spotify",
        "followers": 23766,
        "genres": ["indie pop", "alternative"],
        "submission_pref": "2010s indie and alternative nostalgia. Pitch artists with that era's jangly, melodic aesthetic.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/3sCXpyujWoLScwx3HhvRtf",
    },

    # ── Electronic (3) ───────────────────────────────────────────────────────
    {
        "name": "LO MEJOR EN ELECTRONICA",
        "curator": "Buen chico",
        "platform": "Spotify",
        "followers": 212827,
        "genres": ["electronic", "edm", "dance"],
        "submission_pref": "Best electronic music compilation. Pitch high-energy, well-produced electronic tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0D3OBV654y6cJRwg9bztkk",
    },
    {
        "name": "Best Electronic Music Of All Time",
        "curator": "PlaylistStation",
        "platform": "Spotify",
        "followers": 75096,
        "genres": ["electronic", "edm"],
        "submission_pref": "Iconic electronic tracks. Pitch artists whose work has timeless dancefloor or listening appeal.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/3tRhisNDv5YZXPQltBbJNc",
    },
    {
        "name": "100 Most Iconic EDM Songs",
        "curator": "Ray Fontaine",
        "platform": "Spotify",
        "followers": 59993,
        "genres": ["electronic", "edm", "dance"],
        "submission_pref": "Iconic EDM deep cuts and anthems. Pitch tracks with broad electronic appeal.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/7uMtlAoZ82WCBNlHtNH35l",
    },

    # ── R&B (2) ──────────────────────────────────────────────────────────────
    {
        "name": "best rnb playlist",
        "curator": "Travnextdoor",
        "platform": "Spotify",
        "followers": 291587,
        "genres": ["r&b", "neo soul"],
        "submission_pref": "Community-built R&B. Pitch smooth, melodic R&B with strong hooks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/5zCdhPJHI9kgYsgkSBEWT0",
    },
    {
        "name": "R&B 2026 - New R&B Hits / Top RnB Songs",
        "curator": "Fox",
        "platform": "Spotify",
        "followers": 89341,
        "genres": ["r&b", "contemporary r&b"],
        "submission_pref": "Current R&B hits. Pitch new releases with contemporary production and strong vocals.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/3We3LenpVndqS3rUCP0MeY",
    },

    # ── Funk (4) ─────────────────────────────────────────────────────────────
    {
        "name": "FUNK 2026 - AS MELHORES | TOP 100",
        "curator": "pzmusicplaylists",
        "platform": "Spotify",
        "followers": 476271,
        "genres": ["funk", "brazilian funk", "phonk"],
        "submission_pref": "Brazilian funk and phonk. Pitch high-energy, bass-heavy funk tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0g9DQ9UB0Vr1y3KwgAXr1C",
    },
    {
        "name": "TOP 10 MOST VIRAL PHONK/FUNK 2026",
        "curator": "Hitsi",
        "platform": "Spotify",
        "followers": 209932,
        "genres": ["funk", "phonk"],
        "submission_pref": "Viral phonk and funk. Pitch tracks with strong TikTok or short-form video momentum.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/39yEFHNrv2IzDHxo7XaXi6",
    },
    {
        "name": "TOP FUNK/PHONK MARCH 2026",
        "curator": "melovrant",
        "platform": "Spotify",
        "followers": 131977,
        "genres": ["funk", "phonk"],
        "submission_pref": "Monthly funk/phonk drops. Pitch new releases with dark, aggressive energy.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/3nBpNPEsB5cbKUlu6iHVrm",
    },
    {
        "name": "Top 100 Funk Songs of All Time",
        "curator": "Student of Guitar",
        "platform": "Spotify",
        "followers": 11421,
        "genres": ["funk", "classic funk", "soul"],
        "submission_pref": "Classic funk deep cuts. Pitch artists with genuine groove and live-instrument funk roots.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/01ShyhH6iluuvP0fcMcwWz",
    },

    # ── Metalcore (5) ────────────────────────────────────────────────────────
    {
        "name": "Sad Metalcore - emotional metal",
        "curator": "Camille",
        "platform": "Spotify",
        "followers": 123384,
        "genres": ["metalcore", "post-hardcore", "emotional metal"],
        "submission_pref": "Emotional metalcore and post-hardcore. Pitch tracks that balance heaviness with melodic vulnerability.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/2j2EjOpLbuirl7IHx58av3",
    },
    {
        "name": "Best Metalcore Songs of All Time",
        "curator": "Discover Playlists",
        "platform": "Spotify",
        "followers": 27397,
        "genres": ["metalcore", "post-hardcore"],
        "submission_pref": "Best-of metalcore. Pitch tracks with memorable breakdowns and strong production.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/1GKqC6Rq1O3o97UwWMuiq6",
    },
    {
        "name": "New Metalcore 2026",
        "curator": "RIFF CULT",
        "platform": "Spotify",
        "followers": 19197,
        "genres": ["metalcore", "deathcore", "hardcore"],
        "submission_pref": "Current metalcore releases. Pitch new tracks from emerging or mid-tier metalcore acts.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/280unJx37YbHbRvPDlZxPi",
    },
    {
        "name": "2000s Metalcore ('00-'09)",
        "curator": "Loudwire",
        "platform": "Spotify",
        "followers": 13561,
        "genres": ["metalcore", "post-hardcore"],
        "submission_pref": "2000s metalcore revival. Pitch artists with classic metalcore energy from that golden era.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0DGWifoSIv93af63X0t1CL",
    },
    {
        "name": "gym bro metal",
        "curator": "Camille",
        "platform": "Spotify",
        "followers": 11578,
        "genres": ["metalcore", "metal", "hardcore"],
        "submission_pref": "High-energy metal for workouts. Pitch heavy, aggressive tracks with intense energy.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/1PNaaXHO0aut3nHGCiVD7o",
    },

    # ── K-pop (1) ────────────────────────────────────────────────────────────
    {
        "name": "Kpop demon hunters",
        "curator": "Evelinavasiltsov",
        "platform": "Spotify",
        "followers": 462113,
        "genres": ["k-pop"],
        "submission_pref": "K-pop fan playlist with a dark/anime aesthetic. Pitch powerful, dramatic K-pop tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/4dFzPZLPXFzUd6C0bNwIk5",
    },

    # ── Bedroom pop (1) ──────────────────────────────────────────────────────
    {
        "name": "soft pop - chill vibes",
        "curator": "Emillyy",
        "platform": "Spotify",
        "followers": 12734,
        "genres": ["bedroom pop", "lo-fi", "chill pop"],
        "submission_pref": "Soft, chill bedroom pop. Pitch intimate, lo-fi productions with gentle vocals.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0X0HGO3RiqTG40GTftGBGZ",
    },

    # ── Latin (4) ────────────────────────────────────────────────────────────
    {
        "name": "LAS MEJORES BACHATAS - Mix Bachatero 2026",
        "curator": "gabodeweb",
        "platform": "Spotify",
        "followers": 329871,
        "genres": ["latin", "bachata", "reggaeton"],
        "submission_pref": "Latin and bachata hits. Pitch romantic, rhythm-driven Latin tracks.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/23fCZVEuepIebZIFQuV2Ra",
    },
    {
        "name": "Best Latino Hits",
        "curator": "vale",
        "platform": "Spotify",
        "followers": 185695,
        "genres": ["latin", "reggaeton", "pop latino"],
        "submission_pref": "Best of Latin music. Pitch high-energy, catchy Latino tracks across sub-genres.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/0x5sdZSd4GbYmAucCshEsO",
    },
    {
        "name": "hot latina songs to hype u up",
        "curator": "Shira Gur Aryeh",
        "platform": "Spotify",
        "followers": 142155,
        "genres": ["latin", "reggaeton", "dancehall"],
        "submission_pref": "Hype Latin tracks for energy and confidence. Pitch upbeat, empowering Latin hits.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/6d6M36KHuTToUW4YMlyyaw",
    },
    {
        "name": "latino club bangers",
        "curator": "kassandra soto millan",
        "platform": "Spotify",
        "followers": 33357,
        "genres": ["latin", "reggaeton", "latin house"],
        "submission_pref": "Club-ready Latin music. Pitch dancefloor Latin tracks with strong bass and rhythm.",
        "contact": "",
        "spotify_url": "https://open.spotify.com/playlist/4uaIqklVL5SosVhleRrJ5H",
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
