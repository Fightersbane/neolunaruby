"""GPU stats via NVML, scoped to this app where the driver allows.

- app VRAM: torch's CUDA pool (covers RVC; the kokoro onnx session adds a
  little on top that torch can't see).
- GPU util: per-process SM utilization when nvmlDeviceGetProcessUtilization
  is supported, else whole-device util (util_scope says which).
"""

import logging
import os

log = logging.getLogger(__name__)
_nvml_handle = None
_nvml_failed = False
_last_util_ts = 0


def _app_vram_mb():
    try:
        import torch

        if torch.cuda.is_available():
            return int(torch.cuda.memory_reserved() / 2**20)
    except Exception:
        log.debug("torch VRAM query failed", exc_info=True)
    return None


def gpu_stats():
    global _nvml_handle, _nvml_failed, _last_util_ts
    if _nvml_failed:
        return None
    try:
        import pynvml

        if _nvml_handle is None:
            pynvml.nvmlInit()
            _nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(_nvml_handle)
        stats = {
            "util": int(pynvml.nvmlDeviceGetUtilizationRates(_nvml_handle).gpu),
            "util_scope": "system",
            "vram_used_mb": int(mem.used / 2**20),
            "vram_total_mb": int(mem.total / 2**20),
            "app_vram_mb": _app_vram_mb(),
        }
        try:
            samples = pynvml.nvmlDeviceGetProcessUtilization(_nvml_handle, _last_util_ts)
            _last_util_ts = max((s.timeStamp for s in samples), default=_last_util_ts)
            mine = [s.smUtil for s in samples if s.pid == os.getpid()]
            if mine:
                stats["util"] = int(mine[-1])
                stats["util_scope"] = "app"
        except Exception:
            pass  # unsupported driver or no samples yet; keep device-wide util
        return stats
    except Exception:
        _nvml_failed = True
        log.info("NVML unavailable; GPU telemetry disabled.", exc_info=True)
        return None
