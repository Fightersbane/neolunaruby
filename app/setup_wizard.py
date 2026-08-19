"""First-run setup: check and download the model assets the voice needs.

Nothing here ships in the repo or installer - assets stream from their
official sources on first launch. The Miku RVC model comes from its public
community source and is downloaded on explicit user action only.
"""

import logging
import tempfile
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

REPO_BASE = Path(__file__).resolve().parents[1]

# min_bytes guards against truncated downloads counting as installed.
ASSETS = [
    {
        "name": "kokoro model",
        "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        "dest": "models/kokoro/kokoro-v1.0.onnx",
        "min_bytes": 250_000_000,
    },
    {
        "name": "kokoro voices",
        "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
        "dest": "models/kokoro/voices-v1.0.bin",
        "min_bytes": 20_000_000,
    },
    {
        "name": "pitch model (rmvpe)",
        "url": "https://huggingface.co/JackismyShephard/ultimate-rvc/resolve/main/Resources/predictors/rmvpe.pt",
        "dest": "models/rvc/predictors/rmvpe.pt",
        "min_bytes": 150_000_000,
    },
    {
        "name": "voice embedder",
        "url": "https://huggingface.co/JackismyShephard/ultimate-rvc/resolve/main/Resources/embedders/contentvec/pytorch_model.bin",
        "dest": "models/rvc/embedders/contentvec/pytorch_model.bin",
        "min_bytes": 300_000_000,
    },
    {
        "name": "voice embedder config",
        "url": "https://huggingface.co/JackismyShephard/ultimate-rvc/resolve/main/Resources/embedders/contentvec/config.json",
        "dest": "models/rvc/embedders/contentvec/config.json",
        "min_bytes": 100,
    },
    {
        "name": "Miku voice model",
        "url": "https://huggingface.co/javinfamous/infamous_miku_v2/resolve/main/infamous_miku_v2.zip",
        "dest": "models/voice_models/Miku/infamous_miku_v2.pth",
        "min_bytes": 40_000_000,
        "zip": True,  # zip containing the .pth and .index; extracted flat into Miku/
    },
]


def missing_assets(base: Path = REPO_BASE) -> list[str]:
    missing = []
    for a in ASSETS:
        dest = Path(base) / a["dest"]
        if not dest.is_file() or dest.stat().st_size < a["min_bytes"]:
            missing.append(a["name"])
    return missing


def setup_complete(base: Path = REPO_BASE) -> bool:
    return not missing_assets(base=base)


def download_assets(progress_cb, base: Path = REPO_BASE) -> None:
    """Download every missing asset. progress_cb(name, done_bytes, total_bytes)
    is called as data streams; a name with done == total means finished."""
    import requests

    todo = set(missing_assets(base=base))
    for a in ASSETS:
        if a["name"] not in todo:
            continue
        dest = Path(base) / a["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=dest.parent, suffix=".part") as tmp:
            tmp_path = Path(tmp.name)
            with requests.get(a["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                for chunk in r.iter_content(chunk_size=1 << 20):
                    tmp.write(chunk)
                    done += len(chunk)
                    progress_cb(a["name"], done, total)
        if a.get("zip"):
            _extract_flat(tmp_path, dest.parent)
            tmp_path.unlink(missing_ok=True)
        else:
            tmp_path.replace(dest)
        progress_cb(a["name"], 1, 1)


def _extract_flat(zip_path: Path, dest_dir: Path) -> None:
    """Extract a model zip so the .pth/.index land directly in dest_dir,
    regardless of folder nesting inside the archive."""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            target = dest_dir / Path(info.filename).name
            with z.open(info) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
