"""Vendored from ultimate_rvc.rvc.lib.predictors.f0, trimmed for neolunamiku.

Removed relative to upstream: CREPE (torchcrepe) and FCPE (torchfcpe) — this
project only ever extracts f0 with rmvpe.
"""

import os

from engine.rvc.common import RVC_MODELS_DIR
from engine.rvc.lib.predictors.RMVPE import RMVPE0Predictor


class RMVPE:
    def __init__(self, device, model_name="rmvpe.pt", sample_rate=16000, hop_size=160):
        self.device = device
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        self.model = RMVPE0Predictor(
            os.path.join(RVC_MODELS_DIR, "predictors", model_name),
            device=self.device,
        )

    def get_f0(self, x, filter_radius=0.03):
        f0 = self.model.infer_from_audio(x, thred=filter_radius)
        return f0
