"""
SCOUTE — AI Music Intelligence Platform
========================================
Orchestrates three agents in sequence:

  1. Scout Agent      → finds trending songs on Reddit & Twitter
  2. Arbitrage Agent  → identifies artists blowing up regionally but unknown globally
  3. Ghostwriter Agent → writes cold pitch emails to playlist curators

Usage:
  python main.py                   # run all three agents
  python main.py --agent scout     # run only the Scout Agent
  python main.py --agent arbitrage # run only the Arbitrage Agent
  python main.py --agent ghost     # run only the Ghostwriter Agent
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from scoute.agents import scout, arbitrage, ghostwriter

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scoute.main")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all() -> None:
    logger.info("=== SCOUTE starting full pipeline ===")

    # Stage 1 — Scout
    logger.info("--- Stage 1: Scout Agent ---")
    trending_tracks = scout.run()

    if not trending_tracks:
        logger.warning("Scout Agent returned no tracks. Using empty list for downstream agents.")

    # Stage 2 — Arbitrage
    logger.info("--- Stage 2: Arbitrage Agent ---")
    opportunities = arbitrage.run(trending_tracks)

    if not opportunities:
        logger.warning("Arbitrage Agent found no opportunities. Ghostwriter will not run.")
        return

    # Stage 3 — Ghostwriter
    logger.info("--- Stage 3: Ghostwriter Agent ---")
    email_files = ghostwriter.run(opportunities)

    logger.info("=== SCOUTE pipeline complete ===")
    logger.info(f"Trending tracks found : {len(trending_tracks)}")
    logger.info(f"Arbitrage opportunities: {len(opportunities)}")
    logger.info(f"Emails generated       : {len(email_files)}")
    for path in email_files:
        logger.info(f"  → {path}")


def run_agent(agent_name: str) -> None:
    if agent_name == "scout":
        scout.run()
    elif agent_name == "arbitrage":
        # Arbitrage needs Scout output; load from file if it exists
        import json
        scout_results_path = "scoute/data/scout_results.json"
        if os.path.exists(scout_results_path):
            with open(scout_results_path) as f:
                tracks = json.load(f)
        else:
            logger.warning("No scout_results.json found — running Scout Agent first.")
            tracks = scout.run()
        arbitrage.run(tracks)
    elif agent_name == "ghost":
        import json
        arbitrage_results_path = "scoute/data/arbitrage_results.json"
        if os.path.exists(arbitrage_results_path):
            with open(arbitrage_results_path) as f:
                opportunities = json.load(f)
        else:
            logger.warning("No arbitrage_results.json found — running full pipeline first.")
            run_all()
            return
        ghostwriter.run(opportunities)
    else:
        logger.error(f"Unknown agent: {agent_name}. Choose from: scout, arbitrage, ghost")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCOUTE AI Music Intelligence Platform")
    parser.add_argument(
        "--agent",
        choices=["scout", "arbitrage", "ghost"],
        help="Run a single agent instead of the full pipeline",
    )
    args = parser.parse_args()

    if args.agent:
        run_agent(args.agent)
    else:
        run_all()
