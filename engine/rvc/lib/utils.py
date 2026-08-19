"""Vendored from ultimate_rvc.rvc.lib.utils, trimmed for neolunamiku.

Removed relative to upstream (all unused by this project):
- wget auto-download of embedder models (missing files now raise with the URL)
- stftpitchshift formant shifting (formant_shifting=True now raises)
- load_audio_16k / load_audio / format_title helpers (training/web only)
Only the contentvec embedder that ships in models/rvc/embedders is used.
"""

import logging
import os
import pathlib
import warnings

import numpy as np

from torch import nn
from transformers import HubertModel

import librosa
import soundfile as sf

from engine.rvc.common import RVC_MODELS_DIR

# Remove this to see warnings about transformers models
warnings.filterwarnings("ignore")

logging.getLogger("faiss.loader").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

EMBEDDER_DOWNLOAD_URL = (
    "https://huggingface.co/JackismyShephard/ultimate-rvc/resolve/main/Resources/embedders"
)


class HubertModelWithFinalProj(HubertModel):
    def __init__(self, config):
        super().__init__(config)
        self.final_proj = nn.Linear(config.hidden_size, config.classifier_proj_size)


def load_audio_infer(
    file,
    sample_rate,
    **kwargs,
):
    formant_shifting = kwargs.get("formant_shifting", False)
    if formant_shifting:
        msg = (
            "formant_shifting was removed from the slim build "
            "(stftpitchshift dependency)"
        )
        raise NotImplementedError(msg)
    try:
        file = file.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        if not pathlib.Path(file).is_file():
            raise FileNotFoundError(f"File not found: {file}")
        audio, sr = sf.read(file)
        if len(audio.shape) > 1:
            audio = librosa.to_mono(audio.T)
        if sr != sample_rate:
            audio = librosa.resample(
                audio,
                orig_sr=sr,
                target_sr=sample_rate,
                res_type="soxr_vhq",
            )
    except Exception as error:
        raise RuntimeError(f"An error occurred loading the audio: {error}")
    return np.array(audio).flatten()


def load_embedding(embedder_model, custom_embedder=None):
    embedder_root = os.path.join(str(RVC_MODELS_DIR), "embedders")
    embedding_list = {
        "contentvec": os.path.join(embedder_root, "contentvec"),
        "spin": os.path.join(embedder_root, "spin"),
        "spin-v2": os.path.join(embedder_root, "spin-v2"),
        "chinese-hubert-base": os.path.join(embedder_root, "chinese_hubert_base"),
        "japanese-hubert-base": os.path.join(embedder_root, "japanese_hubert_base"),
        "korean-hubert-base": os.path.join(embedder_root, "korean_hubert_base"),
    }

    if embedder_model == "custom":
        if pathlib.Path(custom_embedder).exists():
            model_path = custom_embedder
        else:
            print(f"Custom embedder not found: {custom_embedder}, using contentvec")
            model_path = embedding_list["contentvec"]
    else:
        model_path = embedding_list[embedder_model]
        bin_file = os.path.join(model_path, "pytorch_model.bin")
        json_file = os.path.join(model_path, "config.json")
        if not (
            pathlib.Path(bin_file).exists() and pathlib.Path(json_file).exists()
        ):
            msg = (
                f"Embedder model files missing from {model_path} — the slim build "
                "does not auto-download them. Fetch pytorch_model.bin and "
                f"config.json from {EMBEDDER_DOWNLOAD_URL}/{embedder_model}/"
            )
            raise FileNotFoundError(msg)

    models = HubertModelWithFinalProj.from_pretrained(model_path)
    return models
