# Changelog

## 0.4.0 — 2026-08-19

- Renamed to neolunaruby. Voice presets are still named Miku.
- Windows installer (`neolunaruby-setup-<version>.exe`, about 2 MB): installs per-user,
  then the first launch installs Python, FFmpeg and dependencies by itself.
- First-run wizard downloads the voice models with per-file progress and takes an
  optional Discord bot token, so no terminal or manual file placement is needed.
- Updates work for installed copies too: a zip overlay replaces code only and never
  touches models, settings or the environment. Applying still needs your confirmation.

## 0.3.0 — 2026-08-19

- Slim build: RVC inference code vendored into `engine/rvc/`, ultimate-rvc and its
  app/training stack removed from dependencies. Environment shrinks 7.5 GB -> 5.6 GB
  (torch's CUDA runtime is the remaining floor). Only the rmvpe pitch method ships.
- requirements.txt is now the single, inference-only dependency file with documented
  post-install steps.
- MIT license, user-facing README, branch protection with required CI, PR-based flow.

## 0.2.0 — 2026-08-19

- Discord integration lives in the desktop app: `/say` works inside DM conversations
  (user-installable, auto-enabled install contexts), plain DMs to the bot are spoken,
  allowlist-gated, optional visible `🎤 text` transcript in the chat.
- Output mode toggle: virtual mic ⇄ server voice channel.
- One-click VB-Cable download/install; devices persist by name; WASAPI sample-rate
  auto-conversion (fixes silent playback); "Hear it too" monitor output.
- Hotkey recorder, system tray, UI restructured into Speak / History / Settings.
- Self-update from GitHub via the version chip; CI (pytest + compileall) on every push.

## 0.1.0 — 2026-08-19

- First working build: local kokoro→RVC Miku voice (~1.1s warm), Discord bot with
  `/say` `/join` `/leave` `/voice` `/pitch` `/speed`, desktop app shell with telemetry,
  history/replay, hotkey overlay, headless engine CLI.
