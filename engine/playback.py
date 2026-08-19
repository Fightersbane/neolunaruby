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
