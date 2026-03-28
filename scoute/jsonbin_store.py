"""
JSONbin.io data store
---------------------
Bridges the local pipeline (which can reach Reddit) and the Railway
dashboard (which cannot, because Reddit blocks cloud-server IPs).

Architecture:
  Local machine  → runs pipeline → uploads JSON to JSONbin.io via API
  Railway server → dashboard reads JSON from JSONbin.io via API

Required environment variables (set in .env locally, Variables tab on Railway):
  JSONBIN_MASTER_KEY     — master key from jsonbin.io/app/settings
  JSONBIN_SCOUT_BIN_ID   — bin ID for scout_results  (printed on first upload)
  JSONBIN_ARB_BIN_ID     — bin ID for arbitrage_results (printed on first upload)
"""

import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.jsonbin.io/v3/b"
_SCOUT_PATH = "scoute/data/scout_results.json"
_ARB_PATH = "scoute/data/arbitrage_results.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _key() -> str:
    return os.environ.get("JSONBIN_MASTER_KEY", "")


def _headers(include_meta: bool = False) -> dict:
    h = {
        "X-Master-Key": _key(),
        "Content-Type": "application/json",
    }
    if not include_meta:
        h["X-Bin-Meta"] = "false"
    return h


# ---------------------------------------------------------------------------
# Public: status
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    """Return True when JSONBIN_MASTER_KEY is present in the environment."""
    return bool(_key())


# ---------------------------------------------------------------------------
# Public: low-level bin operations
# ---------------------------------------------------------------------------

def read_bin(bin_id: str) -> list | dict | None:
    """
    Fetch the latest record from a bin.
    Returns None on any failure so callers can fall back to local files.
    """
    try:
        resp = requests.get(
            f"{_BASE}/{bin_id}/latest",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("record")
    except Exception as exc:
        logger.warning(f"JSONbin read failed (bin {bin_id}): {exc}")
        return None


def write_bin(bin_id: str, data: list | dict) -> bool:
    """Overwrite a bin with new data. Returns True on success."""
    try:
        resp = requests.put(
            f"{_BASE}/{bin_id}",
            json=data,
            headers=_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning(f"JSONbin write failed (bin {bin_id}): {exc}")
        return False


def create_bin(name: str, data: list | dict) -> str:
    """Create a new named bin and return its ID."""
    h = _headers(include_meta=True)
    h["X-Bin-Name"] = name
    resp = requests.post(_BASE, json=data, headers=h, timeout=20)
    resp.raise_for_status()
    return resp.json()["metadata"]["id"]


# ---------------------------------------------------------------------------
# Public: high-level upload (called by main.py after pipeline runs)
# ---------------------------------------------------------------------------

def upload_results(
    scout_path: str = _SCOUT_PATH,
    arb_path: str = _ARB_PATH,
) -> None:
    """
    Upload local JSON results to JSONbin.io after the pipeline runs.

    - If JSONBIN_MASTER_KEY is not set, logs a message and returns silently.
    - If bin IDs are already in env, overwrites the existing bins.
    - If bin IDs are missing, creates new bins and prints the IDs so you
      can add them to .env and to Railway's Variables tab.
    """
    if not is_configured():
        logger.info("JSONBIN_MASTER_KEY not set — skipping cloud upload.")
        return

    def _load(path: str) -> list:
        p = Path(path)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    scout_data = _load(scout_path)
    arb_data = _load(arb_path)
    scout_id = os.environ.get("JSONBIN_SCOUT_BIN_ID", "")
    arb_id = os.environ.get("JSONBIN_ARB_BIN_ID", "")

    # ── Scout bin ──────────────────────────────────────────────────────────
    if scout_id:
        if write_bin(scout_id, scout_data):
            logger.info(f"Scout results uploaded to JSONbin (bin {scout_id}, {len(scout_data)} tracks)")
    else:
        scout_id = create_bin("scoute-scout-results", scout_data)
        logger.info(f"Created scout bin: {scout_id}")
        _print_new_bin("JSONBIN_SCOUT_BIN_ID", scout_id)

    # ── Arbitrage bin ──────────────────────────────────────────────────────
    if arb_id:
        if write_bin(arb_id, arb_data):
            logger.info(f"Arb results uploaded to JSONbin (bin {arb_id}, {len(arb_data)} artists)")
    else:
        arb_id = create_bin("scoute-arb-results", arb_data)
        logger.info(f"Created arb bin: {arb_id}")
        _print_new_bin("JSONBIN_ARB_BIN_ID", arb_id)


def _print_new_bin(var_name: str, bin_id: str) -> None:
    print("\n" + "=" * 54)
    print("  NEW JSONBIN BIN CREATED")
    print("  Add this to .env AND to Railway > Variables:")
    print(f"  {var_name}={bin_id}")
    print("=" * 54 + "\n")
