# neolunamiku desktop app — design spec

**Date:** 2026-08-19 · **Status:** draft for review

## Purpose

A desktop app so a mute user can speak in any voice call by typing. Her typed text becomes Miku-voiced audio routed into a **virtual microphone**, which Discord (DM calls, group calls, servers), games, and any other app see as a normal mic. The existing Discord **bot mode** is retained as a secondary mode in the same UI. Runs on her Windows PC (RTX 2070, 8GB, games running concurrently); Linux supported as a target.

## Requirements (agreed with the user)

- **Mic mode is the priority**; bot mode secondary. Both in one UI; enabling one disables the other.
- **Global hotkey overlay** (e.g. Ctrl+Shift+M): always-on-top input box over any game; Enter speaks, Esc hides. Full settings window separate.
- **Speed above all**: type→sound ≤ ~1s (current pipeline: 1.1s to file; mic mode skips the Discord-bot hop).
- **Pitch and speed exposed as settings** (sliders), plus voice presets.
- Windows primary, **Linux support** planned.
- **Easy setup, clear instructions**; installer eventually.
- **App off ⇒ zero interference**: never touches system default devices; a closed app means the virtual cable simply carries silence and her real mic setup is untouched.
- Cute Miku-themed UI.
- GPU budget: pipeline is ~0.9GB VRAM, busy ~1s per message — verified fine alongside a running game on 8GB.

## Architecture — two processes

```
┌─────────────────────────┐  WebSocket (127.0.0.1, JSON)  ┌──────────────────────────────┐
│  app (Tauri 2, Rust)    │ ─────────────────────────────►│  miku-engine (Python)        │
│  window + overlay       │  say / set / mode / get_state │  pipeline.py (TTS→RVC, GPU)  │
│  global hotkey          │ ◄─────────────────────────────│  mic sink: sounddevice →     │
│  settings UI, device    │  state / speaking / error /   │    virtual cable output      │
│  picker, engine spawn   │  devices                      │  bot sink: discord.py voice  │
└─────────────────────────┘                               └──────────────────────────────┘
```

**Why this split:** the synthesis is PyTorch/onnx — rewriting RVC in Rust gains zero latency (GPU kernel time dominates) at enormous cost. Rust/Tauri owns everything user-facing (small, fast, cross-platform, cute UI is cheap); Python owns everything audio/GPU/Discord. Audio never crosses the socket — the engine plays it directly to the chosen output device, so the protocol stays tiny.

### miku-engine (Python — evolves from existing code)

- `engine/server.py`: asyncio WebSocket server on 127.0.0.1 (random free port, written to a handshake file the app reads). Messages in: `say`, `set` (speed/pitch/preset/device/mode), `get_state`, `bot_join`/`bot_leave`. Messages out: `state`, `speaking` (with per-message latency ms), `error`, `devices`.
- `engine/playback.py` (mic mode): `sounddevice` enumerates output devices; plays synthesized float32 audio to the selected device — **VB-Audio Cable** "CABLE Input" on Windows, PipeWire/Pulse **null-sink** on Linux (created at engine startup if missing, no driver install). Queue semantics identical to the bot (sequential, no cut-offs).
- Bot mode: current `bot.py` logic refactored into `engine/discord_bot.py`, started/stopped by mode toggle; slash commands keep working. `bot.py` remains as a thin standalone entry point so bot-only use never breaks.
- `pipeline.py` unchanged (already engine-agnostic); later optimization: hand numpy straight from kokoro→RVC→playback with no temp files.

### app (Tauri 2)

- Main window: big text box + send; settings (voice preset, speed slider 0.5–2.0, pitch slider ±12, output device picker with "test tone" button, mode toggle mic/bot, bot token+server config); status strip (engine state, last-message latency).
- Overlay: frameless always-on-top mini window bound to a configurable global shortcut (Tauri global-shortcut plugin). Enter = say + hide, Esc = hide.
- Spawns/supervises the engine (auto-restart once on crash; visible state otherwise).
- Miku-themed (teal #39C5BB accents); light/dark aware.

## Mode exclusivity

`mode: "mic" | "bot"` lives in the engine. Switching to bot stops local playback and starts the Discord client; switching to mic disconnects the bot voice client. One synthesis queue serves whichever sink is active.

## DM calls

Bots cannot join DM/group calls (Discord API restriction) — mic mode is the answer there and needs nothing special: Discord just sees a microphone. Typing happens in the app/overlay; reading her Discord DMs to trigger speech from chat is user-account automation, which Discord ToS forbids (ban risk) — explicitly out of scope.

## Setup story

- Phase A (friends & family): `setup.ps1` + README — installs Python env, downloads models on first run (kokoro from GitHub releases, rmvpe from HF; Miku RVC model fetched by the user, with a guided prompt), links to VB-Cable installer and detects it.
- Phase B: Tauri bundler installer; first-run wizard does the model downloads and VB-Cable check with progress UI.
- Miku RVC model is never redistributed in the installer — first-run download by the user, private non-commercial use.

## Error handling

- Engine crash → app shows state + restart button (one auto-restart).
- Virtual cable missing → device picker shows guidance with install link (Windows) / creates null-sink (Linux).
- Models missing → first-run downloader with progress; engine refuses `say` with a clear error until ready.
- Discord token invalid (bot mode) → surfaced in UI, mic mode unaffected.
- WebSocket port conflict → random port + handshake file, retry.

## Testing

- Engine: pytest on protocol handlers (pure JSON in/out) + existing 16 pipeline tests.
- Playback: device-enumeration smoke test; audible test-tone button.
- E2E (the one that matters): overlay → type → hear Miku in a Discord DM call via the cable, measured latency shown in UI.
- Regression: bot mode still passes the existing Discord test flow.

## Phasing (each phase gets its own implementation plan)

1. **Engine service**: extract WS server + mic-mode playback (Windows), keep bot.py working. E2E: type via `wscat`, hear audio on chosen device.
2. **Tauri app**: window + settings + device picker + engine spawn + hotkey overlay.
3. **Bot mode in-engine** + UI toggle.
4. **Packaging**: installer, first-run model wizard, VB-Cable guidance.
5. **Linux**: null-sink creation, hotkey via desktop portal, packaging.

## Out of scope (YAGNI)

- Triggering speech from Discord chat messages (ToS).
- Voice training / model management UI beyond the Miku folder.
- Streaming/sentence-chunked synthesis (revisit only if long messages feel slow).
- Mobile.
