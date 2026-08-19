"""Per-user app settings persisted to config.json (gitignored)."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULTS = {
    "hotkey": "ctrl+shift+m",
    "device": None,          # output device NAME (indices shift); None = system default
    "monitor_device": None,  # second sink to hear yourself; NAME or None = off
    "preset": "Miku",
    "speed": 1.1,
    "n_semitones": 10,
    "mode": "mic",              # mic = virtual-mic sink, bot = server voice channel
    "allowed_dm_users": [],     # Discord user IDs allowed to speak via DM / user-app /say
    "say_posts_text": True,     # /say also posts the text visibly into the conversation
    "accept_discord_input": True,  # master switch for /say and DM input
    "start_with_windows": False,
    "quick_phrases": ["yes", "no", "one sec", "brb", "haha", "thanks"],
}


def load(path: Path) -> dict:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULTS)
    return {k: raw.get(k, v) for k, v in DEFAULTS.items()}


def save(path: Path, cfg: dict) -> None:
    Path(path).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
