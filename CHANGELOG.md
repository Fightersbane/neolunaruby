# Changelog

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
