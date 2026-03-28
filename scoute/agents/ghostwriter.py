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

# Curator database — 20 curators across 8 genres
# In production, replace with a live scraped + enriched database.
SAMPLE_CURATORS = [

    # ── Hip hop / rap (4) ────────────────────────────────────────────────────
    {
        "name": "Street Signals",
        "curator": "Marcus Webb",
        "platform": "Spotify",
        "followers": 87000,
        "genres": ["hip hop", "rap", "underground hip hop"],
        "submission_pref": (
            "Focused on lyricism over production — wants artists who have something "
            "to say. No mumble rap. Prefers tracks with under 500k streams so the "
            "playlist is the first real exposure."
        ),
        "contact": "marcus@streetsignals.co",
    },
    {
        "name": "Drill Season",
        "curator": "Darius Okafor",
        "platform": "Spotify",
        "followers": 54000,
        "genres": ["uk drill", "chicago drill", "trap"],
        "submission_pref": (
            "Only UK and Chicago drill — no exceptions. Wants tracks released in the "
            "last 60 days. Checks SoundCloud play velocity before adding anything."
        ),
        "contact": "darius@drillseason.uk",
    },
    {
        "name": "Block Report",
        "curator": "Aaliya Thompson",
        "platform": "Spotify",
        "followers": 31000,
        "genres": ["hip hop", "rap", "conscious rap", "jazz rap"],
        "submission_pref": (
            "Specialises in hip hop with live instrumentation or jazz influence. "
            "Strongly prefers independent artists. Will not add major label signees."
        ),
        "contact": "submissions@blockreport.fm",
    },
    {
        "name": "Unsigned & Unfiltered",
        "curator": "Jerome 'JB' Baptiste",
        "platform": "Spotify",
        "followers": 19500,
        "genres": ["hip hop", "rap", "bedroom rap", "lo-fi hip hop"],
        "submission_pref": (
            "Exclusively unsigned artists — if you have a label deal, this isn't the "
            "playlist for you. Loves raw, unpolished recordings that feel real. "
            "Under 5k monthly listeners preferred."
        ),
        "contact": "jb@unsignedunfiltered.com",
    },

    # ── R&B / soul (3) ───────────────────────────────────────────────────────
    {
        "name": "Silk & Static",
        "curator": "Renee Holloway",
        "platform": "Spotify",
        "followers": 62000,
        "genres": ["r&b", "neo soul", "alternative r&b"],
        "submission_pref": (
            "Looking for R&B with texture — not polished radio fodder. Appreciates "
            "artists who blend genres. Has a soft spot for DIY production with "
            "professional-quality vocals. No features-only submissions."
        ),
        "contact": "renee@silkandstatic.com",
    },
    {
        "name": "Late Night Feels",
        "curator": "Tobias Mensah",
        "platform": "Spotify",
        "followers": 44500,
        "genres": ["r&b", "soul", "quiet storm", "slow jams"],
        "submission_pref": (
            "Slow-tempo R&B and soul only — BPM under 90 is a strong signal. "
            "The playlist is late-night driving music. Emotionally direct lyrics "
            "are prioritised over technical vocal runs."
        ),
        "contact": "tobias@latenightfeels.fm",
    },
    {
        "name": "Church Clothes",
        "curator": "Simone Adeyemi",
        "platform": "Spotify",
        "followers": 27000,
        "genres": ["soul", "gospel soul", "r&b", "neo soul"],
        "submission_pref": (
            "Soul music with spiritual or emotional depth. Doesn't have to be "
            "religious but needs to feel like it means something. Simone personally "
            "listens to every submission — expects a genuine intro in the pitch."
        ),
        "contact": "simone@churchclothes.co",
    },

    # ── Indie / bedroom pop (3) ──────────────────────────────────────────────
    {
        "name": "The Indie Pulse",
        "curator": "Jamie Rivera",
        "platform": "Spotify",
        "followers": 42000,
        "genres": ["indie pop", "bedroom pop", "lo-fi"],
        "submission_pref": (
            "Only accepts tracks under 3 months old. Gravitates toward artists "
            "who self-produce. Has a strong bias toward female and non-binary "
            "artists — actively trying to balance the playlist."
        ),
        "contact": "jamie@indiepulse.fm",
    },
    {
        "name": "Four Walls",
        "curator": "Elspeth Crane",
        "platform": "Spotify",
        "followers": 23000,
        "genres": ["bedroom pop", "dream pop", "shoegaze", "indie folk"],
        "submission_pref": (
            "Intimate, homemade-sounding records only. Elspeth curates for "
            "headphone listening — nothing that sounds like it was mixed for "
            "festival stages. Debut EPs and singles especially welcome."
        ),
        "contact": "elspeth@fourwalls.fm",
    },
    {
        "name": "Static Bloom",
        "curator": "Noah Fitzpatrick",
        "platform": "Spotify",
        "followers": 16000,
        "genres": ["indie rock", "emo", "indie pop", "post-punk"],
        "submission_pref": (
            "Indie and emo with melodic hooks — not screamo, not hardcore. "
            "Noah updates the playlist every Friday. Pitches sent Monday–Wednesday "
            "have the best chance of making the next cycle."
        ),
        "contact": "noah@staticbloom.net",
    },

    # ── Electronic / dance (3) ───────────────────────────────────────────────
    {
        "name": "Warehouse Frequency",
        "curator": "Lena Kovacs",
        "platform": "Spotify",
        "followers": 71000,
        "genres": ["techno", "house", "electronic", "dance"],
        "submission_pref": (
            "Warehouse and club-focused electronic only. Lena DJs herself and "
            "only adds tracks she would play at 2am. Demos are fine — she doesn't "
            "care about mastering as long as the energy is right."
        ),
        "contact": "lena@warehousefreq.com",
    },
    {
        "name": "Dissolve",
        "curator": "Finn Albrecht",
        "platform": "Spotify",
        "followers": 38000,
        "genres": ["ambient", "electronic", "downtempo", "future beats"],
        "submission_pref": (
            "Slow, textural electronic music for focus and late nights. Finn "
            "specifically looks for artists from outside Western Europe and the US — "
            "strong interest in Southeast Asian and African electronic producers."
        ),
        "contact": "finn@dissolveplaylist.com",
    },
    {
        "name": "Peak Hour",
        "curator": "Camille Dubois",
        "platform": "Spotify",
        "followers": 29000,
        "genres": ["afro house", "afrobeats", "latin house", "dance"],
        "submission_pref": (
            "Dancefloor-ready only. Camille curates for gym and pregame playlists "
            "— high energy, rhythmic, global influences. Especially interested in "
            "afro house and latin-inflected dance tracks."
        ),
        "contact": "camille@peakhourmusic.com",
    },

    # ── K-pop / J-music (2) ──────────────────────────────────────────────────
    {
        "name": "Seoul to the World",
        "curator": "Hana Yoshida",
        "platform": "Spotify",
        "followers": 58000,
        "genres": ["k-pop", "k-indie", "k-r&b"],
        "submission_pref": (
            "K-pop and Korean indie — both big acts and deep cuts. Hana is "
            "particularly interested in artists breaking outside South Korea for "
            "the first time. Highlights artists with strong fancam or short-form "
            "video traction."
        ),
        "contact": "hana@seoultotheworldfm.com",
    },
    {
        "name": "Shibuya Crossing",
        "curator": "Kenji Mori",
        "platform": "Spotify",
        "followers": 21000,
        "genres": ["j-pop", "city pop", "j-rock", "japanese indie"],
        "submission_pref": (
            "Japanese music only — city pop revivals, contemporary J-pop, and "
            "Japanese indie. Kenji is actively looking for artists under 50k "
            "monthly listeners who are building international audiences."
        ),
        "contact": "kenji@shibuyacrossing.fm",
    },

    # ── Funk / soul classics (2) ─────────────────────────────────────────────
    {
        "name": "Crate Therapy",
        "curator": "Winston Osei",
        "platform": "Spotify",
        "followers": 34000,
        "genres": ["funk", "soul", "classic soul", "rare groove"],
        "submission_pref": (
            "Classic and modern funk — Winston runs a vintage record shop and "
            "curates this playlist as a companion to his weekly radio show. "
            "New artists are welcome if they have genuine funk roots, not just "
            "funk-influenced pop."
        ),
        "contact": "winston@cratetherapy.fm",
    },
    {
        "name": "Mothership Groove",
        "curator": "Diana Ferreira",
        "platform": "Spotify",
        "followers": 17500,
        "genres": ["funk", "afrobeat", "soul", "jazz funk"],
        "submission_pref": (
            "Groove-first curation — Diana wants to feel the pocket immediately. "
            "Strong affinity for afrobeat and jazz-funk crossover artists. "
            "Will fast-track submissions that include a live session video."
        ),
        "contact": "diana@mothershipgroove.com",
    },

    # ── Metalcore / punk (2) ─────────────────────────────────────────────────
    {
        "name": "Breakdown Theory",
        "curator": "Sam Kowalski",
        "platform": "Spotify",
        "followers": 46000,
        "genres": ["metalcore", "post-hardcore", "hardcore"],
        "submission_pref": (
            "Metalcore and post-hardcore with melodic elements — not pure death "
            "metal. Sam updates weekly and is actively hunting for acts playing "
            "small venues who haven't been picked up by algorithm playlists yet."
        ),
        "contact": "sam@breakdowntheory.net",
    },
    {
        "name": "Fast & Loud",
        "curator": "Bex Harrington",
        "platform": "Spotify",
        "followers": 22000,
        "genres": ["pop punk", "punk", "emo", "poppunkers"],
        "submission_pref": (
            "Pop punk and emo with no major label affiliation. Bex specifically "
            "champions artists from outside the US and UK — Australia, Brazil, "
            "Southeast Asia. If your band practises in a garage, Bex wants to hear it."
        ),
        "contact": "bex@fastandloud.fm",
    },

    # ── Mixed / discovery (1) ────────────────────────────────────────────────
    {
        "name": "Global Sounds Weekly",
        "curator": "Priya Nair",
        "platform": "Spotify",
        "followers": 18500,
        "genres": ["world music", "afrobeats", "latin", "global", "discovery"],
        "submission_pref": (
            "Priya curates this as a genuine discovery playlist — no genre "
            "restrictions, but the artist must be making their first wave of "
            "international traction. Under 10k monthly listeners on Spotify "
            "strongly preferred. Loves data — include your Reddit or TikTok stats."
        ),
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
