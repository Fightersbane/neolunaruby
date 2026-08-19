"""Path constants for the vendored RVC inference code.

Replaces ultimate_rvc.common / ultimate_rvc.rvc.common: model assets live in
this repo's models/rvc directory (rmvpe.pt under predictors/, the contentvec
embedder under embedders/contentvec/), and the sample-rate JSON configs are
vendored next to this file under configs/.
"""

from __future__ import annotations

from pathlib import Path

RVC_DIR = Path(__file__).resolve().parent
RVC_CONFIGS_DIR = RVC_DIR / "configs"

BASE_DIR = RVC_DIR.parents[1]  # repo root (engine/rvc -> engine -> repo)
MODELS_DIR = BASE_DIR / "models"
RVC_MODELS_DIR = MODELS_DIR / "rvc"
VOICE_MODELS_DIR = MODELS_DIR / "voice_models"
EMBEDDER_MODELS_DIR = RVC_MODELS_DIR / "embedders"
