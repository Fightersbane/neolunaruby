# neolunaruby

Accessibility tool: the user types, a Hatsune Miku voice speaks into a virtual
microphone or a Discord voice channel. Strictly private, non-commercial use -
never redistribute the Miku RVC model or any generated voice content. Public
text says only "accessibility tool"; no personal details about users.

## Stack

- Python 3.13 venv at `.venv` (Windows). Always run via `.venv\Scripts\python.exe`.
- `engine/` - synthesis + audio: `pipeline.py` (kokoro-onnx local TTS on CUDA ->
  RVC voice conversion; edge-tts cloud fallback), `playback.py` (device
  enumeration, AudioPlayer, virtual-mic sink), `discord_client.py` (bot with
  user-installable /say, DM input), `rvc/` (vendored inference code).
- `app/` - pywebview desktop app: `main.py` (windows, tray, hotkey), `bridge.py`
  (js_api), `ui/` (HTML/CSS/JS), config/history/telemetry/updater modules.
- `bot.py` - thin standalone Discord bot entry point.
- Spec: `docs/superpowers/specs/2026-08-19-desktop-app-design.md`; plans in
  `docs/superpowers/plans/`.

## Commands

- Tests (all, hardware-free): `.venv\Scripts\python.exe -m pytest -q`
- Desktop app: `.venv\Scripts\python.exe -m app.main`
- Headless mic mode: `.venv\Scripts\python.exe -m engine --device cable`
- Voice check (cold/warm latency + wav): `.venv\Scripts\python.exe scripts\smoke_test.py "text"`
- Install deps: `pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128`

## Git flow

- Never commit directly to `main` - it is branch-protected and requires the CI
  `test` check. Flow: feature branch -> commit -> push -> PR -> CI green ->
  squash-merge -> delete branch.
- The in-app updater fast-forwards users to `origin/main`, so `main` must always
  be releasable. Bump `VERSION` and `CHANGELOG.md` on notable merges.

## Critical gotchas (these cost real debugging time)

1. NEVER use upstream run_pipeline-style per-call converters: hold the
   `VoiceConverter` resident (`engine/pipeline.py`); `RMVPE` and
   `faiss.read_index` are functools.cache-patched there - removing the patches
   costs 172MB + 350MB disk loads per message.
2. `onnxruntime-gpu` must stay pinned to 1.23.2 (CUDA-12 build matching torch
   cu128 DLLs). Plain `onnxruntime` or 1.29+ silently falls back to CPU. Kokoro
   needs `os.add_dll_directory(torch/lib)` before session creation.
3. Audio on Windows: WASAPI shared mode rejects non-mix-format sample rates -
   always pass `sd.WasapiSettings(auto_convert=True)` (see `playback._play_to`).
   Persist devices by NAME (indices shift when drivers install). Never
   `sd._terminate()/_initialize()` in a live app - restart instead. Filter the
   device list to the WASAPI host API or every device appears 3-4 times.
4. `rmvpe.pt` is NOT auto-downloaded - it lives in `models/rvc/predictors/`
   (from JackismyShephard/ultimate-rvc HF Resources).
5. Latency budget: warm synthesis ~1.1s (kokoro ~0.2s + RVC ~0.8s on RTX 3060
   Ti). Deployment target is an RTX 2070 running games concurrently - keep VRAM
   around 1GB and GPU bursts short.

## Conventions

- TDD for pure logic (test_*.py at repo root); integration is verified by
  listening via `smoke_test.py`, not asserted in unit tests. Unit tests must
  stay hardware-free (fake audio/GPU seams) so CI needs no torch or models.
- `models/`, `audio/`, `.env`, `config.json` are gitignored - never commit them.
- All user-visible voice labels say "Miku". UI copy is plain and user-sided.
