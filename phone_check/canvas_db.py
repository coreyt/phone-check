"""Canvas hash → GPU chip lookup and passive calibration storage.

iOS 12.2+ returns "Apple GPU" via WebGL instead of the specific chip name.
Canvas fingerprinting produces a hash unique to each GPU generation; this
module manages the mapping from those hashes to chip names (e.g. "A16").

The authoritative mapping lives in data/canvas_hashes.json (checked into the
repo).  Runtime observations from passive calibration go to a temp file that
can be periodically merged.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "canvas_hashes.json"
_RUNTIME_FILE = Path("/tmp/canvas_hashes_runtime.json")

# Cached authoritative hash→chip mapping, loaded once.
_cache: dict[str, str] | None = None


def load_hashes() -> dict[str, str]:
    """Read the checked-in JSON and return ``{hash: chip}``."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        data = json.loads(_DATA_FILE.read_text())
        _cache = data.get("hashes", {})
    except (FileNotFoundError, json.JSONDecodeError):
        _cache = {}
    return _cache


def lookup_chip(canvas_hash: str) -> str | None:
    """Look up a canvas hash → GPU chip name, or ``None``."""
    return load_hashes().get(canvas_hash)


def record_observation(canvas_hash: str, chip: str) -> None:
    """Append a hash→chip observation to the runtime temp file.

    Skips if the hash is already in the authoritative file.
    """
    if canvas_hash in load_hashes():
        return

    runtime = _load_runtime()
    if canvas_hash in runtime:
        return
    runtime[canvas_hash] = chip
    _RUNTIME_FILE.write_text(json.dumps(runtime, indent=2))


def get_runtime_observations() -> dict[str, str]:
    """Read runtime observations for diagnostics."""
    return _load_runtime()


def _load_runtime() -> dict[str, str]:
    try:
        return json.loads(_RUNTIME_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
