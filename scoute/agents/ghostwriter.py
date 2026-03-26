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

import anthropic

logger = logging.getLogger(__name__)

# Output directory for generated emails
EMAIL_OUTPUT_DIR = "scoute/outputs/emails"

# Claude model to use for generation
CLAUDE_MODEL = "claude-opus-4-6"

# Curator database placeholder — in production, pull from a scraped/enriched DB
SAMPLE_CURATORS = [
    {
        "name": "The Indie Pulse",
        "curator": "Jamie Rivera",
        "platform": "Spotify",
        "followers": 42000,
        "genres": ["indie pop", "bedroom pop", "lo-fi"],
        "submission_pref": "Only accepts tracks under 3 months old",
        "contact": "jamie@indiepulse.fm",
    },
    {
        "name": "Global Sounds Weekly",
        "curator": "Priya Nair",
        "platform": "Spotify",
        "followers": 18500,
        "genres": ["world music", "afrobeats", "latin"],
        "submission_pref": "Prefers emerging artists with under 10k monthly listeners",
        "contact": "submissions@globalsoundsweekly.com",
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
            logger.info(f"Generating email: {artist['artist']} → {curator['name']}")
            email_content = generate_email(artist, curator, client)
            filepath = save_email(email_content, artist, curator)
            saved_files.append(filepath)

    logger.info(f"Ghostwriter Agent complete — {len(saved_files)} emails generated.")
    return saved_files
