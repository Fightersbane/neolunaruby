"""Self-update, two modes:

- git checkouts (developer machines): fetch + fast-forward pull.
- installed copies (no .git): download the main-branch zip from GitHub and
  overlay the code paths, never touching models/, .env, config.json, .venv.

Both modes then sync dependencies and respawn the app. Nothing updates
without the user's explicit confirmation in the UI.
"""

import logging
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parents[1]
VERSION_FILE = BASE / "VERSION"
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"
REPO = "Fightersbane/neolunaruby"
ZIP_URL = f"https://codeload.github.com/{REPO}/zip/refs/heads/main"
RAW_VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/VERSION"

# Paths replaced by a zip-overlay update. Everything else (models/, .env,
# config.json, .venv, audio/) is user state and must survive updates.
CODE_PATHS = [
    "app", "engine", "scripts", "tests", "docs", ".github",
    "bot.py", "requirements.txt", "VERSION", "CHANGELOG.md",
    "README.md", "LICENSE", "claude.md", ".env.example", ".gitignore",
]


def current_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


def mode(base: Path = BASE) -> str:
    return "git" if (Path(base) / ".git").is_dir() else "zip"


def _git(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=BASE, capture_output=True, text=True, timeout=timeout, check=True
    )


def check() -> dict:
    """How far behind the published main branch we are."""
    if mode() == "git":
        _git("fetch", "origin", "main", timeout=60)
        behind = int(_git("rev-list", "--count", "HEAD..origin/main").stdout.strip())
        return {"version": current_version(), "behind": behind}
    import requests

    r = requests.get(RAW_VERSION_URL, timeout=30)
    r.raise_for_status()
    remote = r.text.strip()
    return {"version": current_version(), "behind": int(remote != current_version())}


def apply() -> None:
    """Bring the code to published main and sync dependencies."""
    if mode() == "git":
        _git("pull", "--ff-only", "origin", "main", timeout=300)
    else:
        _apply_zip_overlay()
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "-r", str(BASE / "requirements.txt"),
            "--extra-index-url", TORCH_INDEX,
        ],
        cwd=BASE, check=True, timeout=1800,
    )


def _apply_zip_overlay() -> None:
    import requests

    with tempfile.TemporaryDirectory(prefix="neoluna_update_") as tmp:
        tmp = Path(tmp)
        zip_path = tmp / "main.zip"
        with requests.get(ZIP_URL, timeout=300) as r:
            r.raise_for_status()
            zip_path.write_bytes(r.content)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        root = next(p for p in tmp.iterdir() if p.is_dir())  # neolunaruby-main/
        for rel in CODE_PATHS:
            src = root / rel
            dst = BASE / rel
            if not src.exists():
                continue
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)


def spawn_new_instance() -> None:
    """Launch the updated app; the caller then shuts this instance down."""
    subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=BASE,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
