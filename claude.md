# neolunamiku

Accessibility tool: the user types, a Hatsune Miku voice speaks in Discord calls.
Strictly private, non-commercial use — never redistribute the Miku RVC model or any
generated voice content.

## Stack

- Python 3.13 venv at `.venv` (Windows). Always run via `.venv\Scripts\python.exe`.
- `bot.py` — discord.py bot (/say, /join, /leave, /pitch, /voice, /speed).
- `pipeline.py` — synthesis: kokoro-onnx local TTS on CUDA → ultimate-rvc voice
  conversion (edge-tts cloud fallback engine). Holds models resident; see gotchas.
- Desktop app phase (Tauri app + Python engine over WebSocket) is specced in
  `docs/superpowers/specs/2026-08-19-desktop-app-design.md`.

## Commands

- Tests: `.venv\Scripts\python.exe -m pytest test_pipeline.py -q`
- Headless voice check (cold/warm latency + output wav): `.venv\Scripts\python.exe smoke_test.py "text"`
- Run bot: `.venv\Scripts\python.exe bot.py` (needs `.env` with DISCORD_TOKEN, GUILD_ID)
- Install deps: `pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128`

## Critical gotchas (these cost real debugging time)

1. NEVER call ultimate_rvc's `run_pipeline()`: it rebuilds the voice converter on
   every call (~15s/message). Use the held `VoiceConverter` in `pipeline.py`;
   `RMVPE` and `faiss.read_index` are functools.cache-patched there — removing
   those patches costs 172MB + 350MB disk loads per message.
2. `onnxruntime-gpu` must stay pinned to 1.23.2 (CUDA-12 build matching torch
   cu128 DLLs). Plain `onnxruntime` or 1.29+ silently falls back to CPU. Kokoro
   needs `os.add_dll_directory(torch/lib)` before session creation.
3. `rmvpe.pt` is NOT auto-downloaded by ultimate-rvc — it lives in
   `models/rvc/predictors/` (fetched from JackismyShephard/ultimate-rvc HF Resources).
4. Latency budget: warm synthesis ~1.1s (kokoro ~0.2s + RVC ~0.8s on RTX 3060 Ti).
   Deployment target is an RTX 2070 running games concurrently — keep
   VRAM around 1GB and GPU bursts short.

## Conventions

- TDD for pure logic (tests live in `test_pipeline.py`); integration is verified
  by listening via `smoke_test.py`, not asserted in unit tests.
- `models/`, `audio/`, and `.env` are gitignored and must never be committed.
