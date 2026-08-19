"""Self-update from the public GitHub repo: git pull + dependency sync + restart."""

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parents[1]
VERSION_FILE = BASE / "VERSION"
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"


def current_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


def _git(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=BASE, capture_output=True, text=True, timeout=timeout, check=True
    )


def check() -> dict:
    """How many commits behind origin/main we are."""
    _git("fetch", "origin", "main", timeout=60)
    behind = int(_git("rev-list", "--count", "HEAD..origin/main").stdout.strip())
    return {"version": current_version(), "behind": behind}


def apply() -> None:
    """Fast-forward to origin/main and sync dependencies."""
    _git("pull", "--ff-only", "origin", "main", timeout=300)
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "-r", str(BASE / "requirements.txt"),
            "--extra-index-url", TORCH_INDEX,
        ],
        cwd=BASE, check=True, timeout=1800,
    )


def spawn_new_instance() -> None:
    """Launch the updated app; the caller then shuts this instance down."""
    subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=BASE,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
