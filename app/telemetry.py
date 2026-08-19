"""GPU stats via NVML; degrades to None on non-NVIDIA machines."""

import logging

log = logging.getLogger(__name__)
_nvml_handle = None
_nvml_failed = False


def gpu_stats():
    global _nvml_handle, _nvml_failed
    if _nvml_failed:
        return None
    try:
        import pynvml

        if _nvml_handle is None:
            pynvml.nvmlInit()
            _nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(_nvml_handle).gpu
        mem = pynvml.nvmlDeviceGetMemoryInfo(_nvml_handle)
        return {
            "util": int(util),
            "vram_used_mb": int(mem.used / 2**20),
            "vram_total_mb": int(mem.total / 2**20),
        }
    except Exception:
        _nvml_failed = True
        log.info("NVML unavailable; GPU telemetry disabled.", exc_info=True)
        return None
