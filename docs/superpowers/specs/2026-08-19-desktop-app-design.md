# neolunamiku desktop app — design spec

**Date:** 2026-08-19 · **Status:** draft for review

## Purpose

An accessibility tool: a desktop app for speaking in any voice call by typing. Typed text becomes Miku-voiced audio routed into a **virtual microphone**, which Discord (DM calls, group calls, servers), games, and any other app see as a normal mic. The existing Discord **bot mode** is retained as a secondary output mode in the same UI. Target machine: Windows, RTX 2070 (8GB), games running concurrently; Linux supported as a target. Strictly non-commercial.

## Requirements (agreed)

- **Mic mode is the priority**; bot mode secondary. One UI; the two *output* modes are mutually exclusive.
- **Global hotkey overlay** (e.g. Ctrl+Shift+M): always-on-top input box over any game; Enter speaks, Esc hides. Full settings window separate.
- **Discord DM input**: typing a DM *to the bot* speaks it through the local mic (see Input paths).
- **Speed above all**: type→sound ≤ ~1s (current pipeline: ~1.1s to file; mic mode skips the Discord-bot hop).
- **Pitch and speed as settings** (sliders) plus voice presets — every preset is labeled Miku; presets differ only in the hidden base voice and transpose. Cloud presets are offline backups.
- **Telemetry in the UI**: GPU utilization/VRAM, per-message latency, engine state.
- **Message history with replay**: recent messages listed; click to replay the cached wav to the active output.
- **In-app update**: pulls latest from the public GitHub repo.
- Windows primary, **Linux support** planned; **easy setup, clear instructions**; installer eventually.
- **App off ⇒ zero interference**: never touches system default devices; a closed app means the virtual cable simply carries silence and the real mic setup is untouched.
- Cute Miku-themed UI (teal #39C5BB), light/dark aware.
- GPU budget: pipeline is ~0.9GB VRAM, busy ~1s per message — verified fine alongside a running game on 8GB.

## Stack decision: all-Python

One process, one toolchain. We ship a multi-GB Python+model stack regardless, so a Rust shell adds a second toolchain and an IPC layer for no latency or size benefit (UI was never the bottleneck; inference time is GPU kernel time).

- **UI**: `pywebview` — web-tech frontend (HTML/JS/CSS on disk) in a native window, Python `js_api` bridge. Overlay = second frameless always-on-top pywebview window toggled by a global hotkey (`keyboard` lib on Windows; Linux needs input-group perms — documented).
- **Engine**: the existing `pipeline.py` plus a playback/queue layer, running on an asyncio loop in a background thread of the same process.
- **Packaging**: PyInstaller onedir later; Phase A is `setup.ps1` + README.

## Architecture (single process)

```
┌───────────────────────────────────────────────────────────────┐
│ app.py                                                        │
│  ├── ui: pywebview main window + overlay (hotkey toggled)     │
│  │     js_api: say(), set(), get_state(), replay(), update()  │
│  ├── engine thread (asyncio): synthesis queue → active sink   │
│  │     ├── mic sink: sounddevice → virtual cable output       │
│  │     └── bot sink: discord.py voice (server VCs)            │
│  ├── discord client (also in engine loop):                    │
│  │     bot-DM input + slash commands + voice when bot mode    │
│  └── telemetry: pynvml GPU stats, per-message timings         │
└───────────────────────────────────────────────────────────────┘
```

`bot.py` remains a thin standalone entry point (bot-only use never breaks). The engine components live in `engine/` so both entry points share them.

## Input paths (any can be active)

1. **App window / hotkey overlay** — primary.
2. **Discord DM to the bot** — the bot receives DMs (message content in DMs needs no privileged intent) and forwards them to the engine; in mic mode they play through the virtual mic, in bot mode through the VC. Works from a phone. Restricted to configured Discord user IDs.
3. **Slash commands** — unchanged in bot mode.

Reading a *user account's* DM conversations with other people (self-bots, BetterDiscord/Vencord client mods) is Discord-ToS-forbidden (ban risk) and permanently out of scope. "DM the bot" gives the same convenience legitimately.

## Modes (output)

`mode: mic | bot` — mic plays to the selected audio device (VB-Audio Cable on Windows; PipeWire/Pulse null-sink on Linux, created at startup, no driver); bot plays into a server VC. Switching modes swaps the sink; one synthesis queue serves both. Bots cannot join DM/group calls (API restriction) — mic mode covers those.

## Telemetry & history

- Telemetry strip: engine state, last-message latency (TTS ms + RVC ms + total), GPU util % and VRAM via `pynvml`, sampled while speaking.
- History: engine keeps (text, wav path, latency, timestamp) for the last 24h (aligned with the existing wav purge). UI lists them; replay sends the cached wav to the active sink — no re-synthesis.

## Updates

Phase A: "Update" button = `git pull` + `pip install -r requirements.txt` + engine restart, with a version/commit label in the UI. Repo is public (github.com/Fightersbane/neolunamiku); tokens/models/audio are gitignored — nothing in the repo is private. Later: GitHub Releases + packaged updater.

## Setup story

- Phase A: `setup.ps1` + README — venv, deps, first-run model downloads (kokoro from GitHub releases, rmvpe from HF; Miku RVC model fetched by the user with a guided prompt), VB-Cable install link + detection.
- Phase B: installer with a first-run wizard (model downloads with progress, cable check).
- The Miku RVC model is never redistributed in repo or installer — first-run download by the user; private non-commercial use.

## Footprint (measured 2026-08-19)

Models 1.24GB (embedder 361MB, Miku index 351MB, kokoro 310MB, rmvpe 173MB, Miku .pth 53MB) + venv 7.3GB (torch/CUDA dominates). Reduction levers, in order of payoff: int8 kokoro variant (310→88MB), vendoring only ultimate-rvc's inference subpackage to drop its gradio/training/yt-dlp deps (venv likely −2GB+), smaller faiss index (quality tradeoff). torch+CUDA (~3GB) is the irreducible cost of GPU RVC.

## Error handling

- Engine failure → UI state + restart button (one auto-restart).
- Cable missing → device picker guidance with install link (Windows) / auto null-sink (Linux).
- Models missing → first-run downloader; `say` refused with a clear error until ready.
- Bot token invalid → surfaced in UI; mic mode unaffected.
- Update failure → rollback message (`git merge --abort`), app keeps running old version.

## Testing

- pytest: engine protocol/queue handlers + existing pipeline tests.
- Device-enumeration smoke test; audible test-tone button.
- E2E: overlay → type → hear Miku in a Discord DM call via the cable; latency shown in UI.
- Regression: bot mode passes the existing Discord test flow.

## Phasing (each phase gets its own implementation plan)

1. **Engine extraction + mic mode**: engine/ package, playback queue → sounddevice, device picker logic, works headless via a tiny CLI. E2E: hear audio on a chosen device.
2. **App shell**: pywebview window + overlay + hotkey + settings + telemetry + history/replay.
3. **Discord integration**: bot-DM input, bot output mode toggle.
4. **Updater + setup script.**
5. **Packaging/installer**, then **Linux**.

## Future: sing mode & audio lab (scoped, not built)

Most ingredients are already installed as ultimate-rvc dependencies:

- **Cover mode**: drop an audio file → vocals separated (`audio-separator`, installed) → RVC-converted to Miku → remixed with the instrumental. This is ultimate-rvc's headline feature; exposing it in the UI is mostly plumbing.
- **Autotune**: `convert_audio(f0_autotune=True)` already exists — a UI toggle.
- **Effects**: reverb/EQ/compression via `pedalboard` (installed) as post-processing presets ("concert Miku", "radio", etc.).
- **True lyric→melody singing synthesis** (type lyrics + notes, Miku sings): requires a singing-synthesis model (DiffSinger-class) — large separate project; revisit on demand.

## Out of scope

- Reading user-account DMs / client mods (ToS).
- Mobile.
- Streaming/sentence-chunked synthesis (revisit only if long messages feel slow).
