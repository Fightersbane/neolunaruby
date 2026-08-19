# Engine Extraction + Virtual-Mic Playback (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the synthesis core into an `engine/` package and add sequential audio playback to a selectable output device (virtual mic), driveable headless from a CLI.

**Architecture:** `engine/pipeline.py` (moved, unchanged API) synthesizes wavs; new `engine/playback.py` enumerates output devices, detects VB-Audio Cable, and plays wavs sequentially via `sounddevice`; new `engine/cli.py` wires them for headless use. `bot.py` keeps working against the moved module.

**Tech Stack:** Python 3.13, sounddevice (PortAudio), soundfile, pytest, existing pipeline (kokoro-onnx + ultimate-rvc).

**Spec:** `docs/superpowers/specs/2026-08-19-desktop-app-design.md`

## Global Constraints

- Windows venv: run everything with `.venv\Scripts\python.exe` from the repo root.
- Never call ultimate-rvc's `run_pipeline`; only the held converter in `engine/pipeline.py`.
- `onnxruntime-gpu==1.23.2` stays pinned; do not add deps that pull `onnxruntime`.
- `models/`, `audio/`, `.env` stay gitignored; never commit them.
- All presets/labels user-visible must say "Miku"; public text says "accessibility tool" — no personal references.
- Sequential speech: messages must never overlap or cut each other off.
- Commit format: end body with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (use a `@'...'@` here-string for multi-line -m in PowerShell).

---

### Task 1: Move pipeline.py into engine/ package

**Files:**
- Create: `engine/__init__.py` (empty)
- Move: `pipeline.py` → `engine/pipeline.py` (git mv; one path fix)
- Modify: `bot.py:14`, `smoke_test.py:14`, `test_pipeline.py:5` (imports)

**Interfaces:**
- Produces: `from engine import pipeline` — everything else (`pipeline.synthesize`, `SETTINGS`, `VOICE_PRESETS`, `validate_text`, `model_available`, `purge_outputs`, `warmup`, `MAX_TEXT_LEN`, `MIKU_DIR`) unchanged.

- [ ] **Step 1: Move the file**

```powershell
New-Item -ItemType File engine\__init__.py -Force | Out-Null
git mv pipeline.py engine/pipeline.py
```

- [ ] **Step 2: Fix BASE_DIR (now one level deeper)**

In `engine/pipeline.py`, change:

```python
BASE_DIR = Path(__file__).resolve().parent
```

to:

```python
BASE_DIR = Path(__file__).resolve().parents[1]
```

- [ ] **Step 3: Update the three imports**

In `bot.py` and `smoke_test.py`: `import pipeline` → `from engine import pipeline`.
In `test_pipeline.py`: `import pipeline` → `from engine import pipeline`.

- [ ] **Step 4: Verify everything still works**

Run: `.venv\Scripts\python.exe -m pytest test_pipeline.py -q` → 17 passed.
Run: `.venv\Scripts\python.exe -c "import bot; print(bot.FFMPEG)"` → prints ffmpeg path.
Also check the path fix: `.venv\Scripts\python.exe -c "from engine import pipeline; print(pipeline.MIKU_DIR)"` → must end in `neolunamiku\models\voice_models\Miku` (NOT `engine\models\...`).

- [ ] **Step 5: Commit**

`git add -A; git commit` — message: `refactor: move pipeline into engine package`

---

### Task 2: Device enumeration + virtual-cable detection (TDD)

**Files:**
- Create: `engine/playback.py`
- Test: `test_playback.py` (repo root, matching test_pipeline.py convention)
- Modify: `requirements.txt` (add `sounddevice`)

**Interfaces:**
- Produces: `list_output_devices() -> list[dict]` (each `{"index": int, "name": str, "is_default": bool}`), `_normalize_devices(raw: list[dict], default_index: int) -> list[dict]`, `find_virtual_cable(devices: list[dict]) -> int | None`.

- [ ] **Step 1: Install dep, record it**

`pip install sounddevice` in the venv; add `sounddevice` line to requirements.txt under discord.py.

- [ ] **Step 2: Write failing tests**

```python
# test_playback.py
from engine import playback


RAW = [
    {"name": "Microphone (Realtek)", "max_output_channels": 0, "index": 0},
    {"name": "Speakers (Realtek)", "max_output_channels": 2, "index": 1},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2, "index": 2},
]


class TestNormalizeDevices:
    def test_keeps_only_output_devices(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["index"] for d in devs] == [1, 2]

    def test_marks_default(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["is_default"] for d in devs] == [True, False]


class TestFindVirtualCable:
    def test_finds_cable_input(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert playback.find_virtual_cable(devs) == 2

    def test_none_when_absent(self):
        devs = playback._normalize_devices(RAW[:2], default_index=1)
        assert playback.find_virtual_cable(devs) is None
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv\Scripts\python.exe -m pytest test_playback.py -q`
Expected: FAIL — `module 'engine.playback' not found` / AttributeError.

- [ ] **Step 4: Minimal implementation**

```python
# engine/playback.py
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
```

- [ ] **Step 5: Run tests → pass, then commit**

Run: `.venv\Scripts\python.exe -m pytest test_playback.py test_pipeline.py -q` → all pass.
`git add -A; git commit` — message: `feat: output device enumeration and cable detection`

---

### Task 3: AudioPlayer sequential queue (TDD)

**Files:**
- Modify: `engine/playback.py` (append class)
- Test: `test_playback.py` (append)

**Interfaces:**
- Produces: `AudioPlayer(device: int | None)` with `start()`, `async enqueue(wav_path)`, `drain()`, `async stop()`, and `_play_blocking(path)` (the seam tests monkeypatch).

- [ ] **Step 1: Write failing tests**

```python
# append to test_playback.py
import asyncio


class TestAudioPlayer:
    def _player_with_recorder(self, monkeypatch, played, delay=0.0):
        player = playback.AudioPlayer(device=None)

        def fake_play(path):
            import time
            time.sleep(delay)
            played.append(path)

        monkeypatch.setattr(player, "_play_blocking", fake_play)
        return player

    def test_plays_in_order(self, monkeypatch):
        async def run():
            played = []
            player = self._player_with_recorder(monkeypatch, played, delay=0.01)
            player.start()
            await player.enqueue("a.wav")
            await player.enqueue("b.wav")
            await player.enqueue("c.wav")
            await player.wait_idle()
            await player.stop()
            return played

        assert asyncio.run(run()) == ["a.wav", "b.wav", "c.wav"]

    def test_drain_discards_pending(self, monkeypatch):
        async def run():
            played = []
            player = self._player_with_recorder(monkeypatch, played, delay=0.05)
            player.start()
            await player.enqueue("a.wav")
            await player.enqueue("b.wav")
            await asyncio.sleep(0.01)  # a.wav is mid-play
            player.drain()
            await player.wait_idle()
            await player.stop()
            return played

        assert asyncio.run(run()) == ["a.wav"]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python.exe -m pytest test_playback.py -q`
Expected: FAIL — `AudioPlayer` not defined.

- [ ] **Step 3: Implement**

```python
# append to engine/playback.py
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
```

- [ ] **Step 4: Run tests → pass, then commit**

Run: `.venv\Scripts\python.exe -m pytest test_playback.py test_pipeline.py -q` → all pass.
`git add -A; git commit` — message: `feat: sequential AudioPlayer for virtual-mic sink`

---

### Task 4: Headless CLI

**Files:**
- Create: `engine/cli.py`
- Create: `engine/__main__.py` (2 lines, so `python -m engine` works)

**Interfaces:**
- Consumes: `pipeline.synthesize`, `pipeline.validate_text`, `pipeline.model_available`, `playback.list_output_devices`, `playback.find_virtual_cable`, `playback.AudioPlayer`.
- Produces: `python -m engine --list-devices`; `python -m engine --device N "text"` (one-shot); `python -m engine --device N` (stdin REPL, blank line/EOF exits). `--device cable` resolves via `find_virtual_cable`; omitted = system default.

- [ ] **Step 1: Implement**

```python
# engine/cli.py
"""Headless driver: synthesize typed text and play it to an output device."""

import argparse
import asyncio
import sys

from engine import pipeline, playback


def _resolve_device(arg: str | None) -> int | None:
    if arg is None:
        return None
    devices = playback.list_output_devices()
    if arg == "cable":
        cable = playback.find_virtual_cable(devices)
        if cable is None:
            sys.exit("No VB-Audio Cable found. Install it from https://vb-audio.com/Cable/")
        return cable
    return int(arg)


async def _speak_loop(device: int | None, one_shot: str | None) -> None:
    if not pipeline.model_available():
        sys.exit(f"No Miku model in {pipeline.MIKU_DIR}")
    player = playback.AudioPlayer(device=device)
    player.start()
    await pipeline.warmup()
    print("ready")

    async def say(text: str) -> None:
        err = pipeline.validate_text(text)
        if err:
            print(err, file=sys.stderr)
            return
        wav = await pipeline.synthesize(text)
        await player.enqueue(wav)

    if one_shot is not None:
        await say(one_shot)
    else:
        while True:
            # read stdin off-thread: a blocking read would stall the playback task
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line or not line.strip():
                break
            await say(line.strip())
    await player.wait_idle()
    await player.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="engine", description="Miku voice engine (headless)")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device", help="output device index, or 'cable'")
    parser.add_argument("text", nargs="?", help="speak this and exit; omit for stdin REPL")
    args = parser.parse_args()

    if args.list_devices:
        for d in playback.list_output_devices():
            marker = "*" if d["is_default"] else " "
            print(f"{marker} {d['index']:>3}  {d['name']}")
        return
    asyncio.run(_speak_loop(_resolve_device(args.device), args.text))


if __name__ == "__main__":
    main()
```

```python
# engine/__main__.py
from engine.cli import main

main()
```

- [ ] **Step 2: Verify device listing**

Run: `.venv\Scripts\python.exe -m engine --list-devices`
Expected: table of output devices, one marked `*` as default. (No cable on the dev machine is fine.)

- [ ] **Step 3: Audible E2E on default device**

Run: `.venv\Scripts\python.exe -m engine "Engine test, can you hear me?"`
Expected: `ready` after warmup, then Miku speaks from the default speakers; exits cleanly. The person at the machine confirms audibility.

- [ ] **Step 4: Full suite + commit**

Run: `.venv\Scripts\python.exe -m pytest test_playback.py test_pipeline.py -q` → all pass.
`git add -A; git commit` — message: `feat: headless engine CLI with device selection`

---

### Task 5: Final verification + push

- [ ] **Step 1: Regression sweep**

Run all: pytest (both files), `python -c "import bot"`, `python -m engine --list-devices`, and `python smoke_test.py "quick check"` (still <2.5s warm).

- [ ] **Step 2: Push**

`git push origin main`. Confirm CI-free repo shows the new engine/ package.
