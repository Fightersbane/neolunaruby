"""Output-device enumeration and sequential wav playback (virtual-mic sink)."""

import asyncio
import logging

log = logging.getLogger(__name__)


def _normalize_devices(raw: list[dict], default_index: int) -> list[dict]:
    return [
        {"index": d["index"], "name": d["name"], "is_default": d["index"] == default_index}
        for d in raw
        if d.get("max_output_channels", 0) > 0
    ]


def find_virtual_cable(devices: list[dict]) -> int | None:
    for d in devices:
        if "CABLE Input" in d["name"]:
            return d["index"]
    return None


def list_output_devices() -> list[dict]:
    import sounddevice as sd

    raw = [{**d, "index": i} for i, d in enumerate(sd.query_devices())]
    default_out = sd.default.device[1]
    return _normalize_devices(raw, default_out)
