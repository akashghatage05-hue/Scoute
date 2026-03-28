"""
scoute/storage.py
-----------------
JSONbin.io cloud storage for SCOUTE.

  push_to_jsonbin(data, bin_name) — upload dict/list to JSONbin.
      Creates a new bin on first call; updates the existing bin on subsequent calls.
      Bin IDs are persisted locally in .jsonbin_ids.json so the same bin is reused.

  pull_from_jsonbin(bin_name) — download and return the latest record from JSONbin.
      Returns None if JSONBIN_KEY is not set or the bin has not been created yet.

Environment variable:
  JSONBIN_KEY — Master Key from jsonbin.io > API Keys tab
"""

import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jsonbin.io/v3"
_BIN_IDS_FILE = Path(".jsonbin_ids.json")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _key() -> str:
    return os.environ.get("JSONBIN_KEY", "")


def _headers(include_meta: bool = False) -> dict:
    h = {
        "X-Master-Key": _key(),
        "Content-Type": "application/json",
    }
    if not include_meta:
        h["X-Bin-Meta"] = "false"
    return h


def _load_ids() -> dict:
    if _BIN_IDS_FILE.exists():
        try:
            return json.loads(_BIN_IDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_ids(ids: dict) -> None:
    _BIN_IDS_FILE.write_text(json.dumps(ids, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def push_to_jsonbin(data: dict | list, bin_name: str) -> bool:
    """
    Upload data to JSONbin under the given bin_name.

    - First call: creates a new bin, saves its ID to .jsonbin_ids.json
    - Subsequent calls: updates the existing bin
    - Returns True on success, False on failure.
    - Silently skips (returns False) if JSONBIN_KEY is not set.
    """
    if not _key():
        logger.info("JSONBIN_KEY not set — skipping push.")
        return False

    ids = _load_ids()
    bin_id = ids.get(bin_name)

    try:
        if bin_id:
            # Update existing bin
            resp = requests.put(
                f"{BASE_URL}/b/{bin_id}",
                json=data,
                headers=_headers(),
                timeout=20,
            )
            resp.raise_for_status()
            count = len(data) if isinstance(data, list) else 1
            logger.info(f"JSONbin '{bin_name}' updated (bin {bin_id}, {count} records)")
        else:
            # Create new bin
            h = _headers(include_meta=True)
            h["X-Bin-Name"] = bin_name
            resp = requests.post(
                f"{BASE_URL}/b",
                json=data,
                headers=h,
                timeout=20,
            )
            resp.raise_for_status()
            bin_id = resp.json()["metadata"]["id"]
            ids[bin_name] = bin_id
            _save_ids(ids)
            logger.info(f"JSONbin '{bin_name}' created (bin {bin_id})")
            print(f"\n  Bin created: {bin_name} = {bin_id}")
            print(f"  .jsonbin_ids.json updated — commit this file so Railway can read it.\n")
        return True
    except Exception as exc:
        logger.warning(f"JSONbin push failed for '{bin_name}': {exc}")
        return False


def pull_from_jsonbin(bin_name: str) -> dict | list | None:
    """
    Download the latest record for bin_name from JSONbin.

    Returns the data, or None if:
      - JSONBIN_KEY is not set
      - No bin ID exists yet for this name
      - The request fails for any reason
    """
    if not _key():
        return None

    bin_id = _load_ids().get(bin_name)
    if not bin_id:
        logger.debug(f"No bin ID for '{bin_name}' in .jsonbin_ids.json — using local file.")
        return None

    try:
        resp = requests.get(
            f"{BASE_URL}/b/{bin_id}/latest",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("record")
        count = len(data) if isinstance(data, list) else 1
        logger.info(f"JSONbin '{bin_name}' pulled (bin {bin_id}, {count} records)")
        return data
    except Exception as exc:
        logger.warning(f"JSONbin pull failed for '{bin_name}': {exc}")
        return None
