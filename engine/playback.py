"""Output-device enumeration and sequential wav playback (virtual-mic sink)."""

import asyncio
import logging

log = logging.getLogger(__name__)


PREFERRED_HOSTAPI = "Windows WASAPI"


def _normalize_devices(raw: list[dict], default_index: int) -> list[dict]:
    outs = [d for d in raw if d.get("max_output_channels", 0) > 0]
    # Windows lists every device once per host API (MME, DirectSound, WASAPI,
    # WDM-KS) — keep only the WASAPI entries when any exist to avoid duplicates.
    wasapi = [d for d in outs if d.get("hostapi_name") == PREFERRED_HOSTAPI]
    chosen = wasapi or outs
    return [
        {"index": d["index"], "name": d["name"], "is_default": d["index"] == default_index}
        for d in chosen
    ]


def find_virtual_cable(devices: list[dict]) -> int | None:
    for d in devices:
        if "CABLE Input" in d["name"]:
            return d["index"]
    return None


def list_output_devices() -> list[dict]:
    import sounddevice as sd

    hostapis = list(sd.query_hostapis())
    raw = [
        {**d, "index": i, "hostapi_name": hostapis[d["hostapi"]]["name"]}
        for i, d in enumerate(sd.query_devices())
    ]
    default_out = sd.default.device[1]
    # When filtering to WASAPI, the global default index (usually an MME entry)
    # won't survive — use WASAPI's own default output instead.
    for api in hostapis:
        if api["name"] == PREFERRED_HOSTAPI and api.get("default_output_device", -1) >= 0:
            default_out = api["default_output_device"]
            break
    return _normalize_devices(raw, default_out)


def test_tone(device: int | None = None) -> None:
    import numpy as np
    import sounddevice as sd

    sr = 48000
    t = np.linspace(0, 0.4, int(sr * 0.4), endpoint=False)
    tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype("float32")
    sd.play(tone, sr, device=device)
    sd.wait()


class AudioPlayer:
    """Plays wavs sequentially to one output device. One consumer task."""

    def __init__(self, device: int | None = None) -> None:
        self.device = device
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._consume())

    async def enqueue(self, wav_path) -> None:
        await self._queue.put(wav_path)

    def drain(self) -> None:
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()

    async def wait_idle(self) -> None:
        await self._queue.join()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _consume(self) -> None:
        while True:
            wav_path = await self._queue.get()
            try:
                await asyncio.to_thread(self._play_blocking, wav_path)
            except Exception:
                log.exception("Playback failed for %s", wav_path)
            finally:
                self._queue.task_done()

    def _play_blocking(self, wav_path) -> None:
        import sounddevice as sd
        import soundfile as sf

        data, sr = sf.read(str(wav_path), dtype="float32")
        sd.play(data, sr, device=self.device)
        sd.wait()
