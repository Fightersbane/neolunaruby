# Windows Installer + First-Run Wizard (Phase 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A small Inno Setup `.exe` that installs the app per-user; first launch opens an in-app setup wizard that downloads dependencies and models with progress, checks VB-Cable, and takes the optional Discord token. Updates stay tiny (pull-based).

**Architecture:** Installer ships the source tree (no venv, no models, no .git) plus a bootstrap that ensures Python 3.13 (winget), creates `.venv`, and installs requirements. The app gains `app/setup_wizard.py` (asset checks + downloads with progress callbacks) surfaced as a first-run panel in the UI. `app/updater.py` becomes dual-mode: git checkouts keep `git pull`; installed copies use a GitHub zip overlay that preserves `models/`, `.env`, `config.json`, `.venv`.

**Tech Stack:** Inno Setup 6, winget (Python bootstrap), requests, existing app/engine packages.

**Spec:** `docs/superpowers/specs/2026-08-19-desktop-app-design.md`

## Global Constraints

- Same as prior plans (venv python, onnxruntime pin, Miku labels, sequential speech, TDD for pure logic, PR flow: branch -> CI -> squash-merge).
- The installer must contain no secrets and no models. The Miku model downloads from its public community source on user action; kokoro/rmvpe/contentvec download from official releases.
- Wizard and updater must keep working when the app is offline: clear errors, retry buttons, never a hang.

## Tasks

1. **Asset manifest + checks (TDD)** - `app/setup_wizard.py`: `ASSETS` manifest (name, url, dest, sha-less size check), `missing_assets() -> list[str]`, `setup_complete() -> bool`; pure logic tested with tmp dirs in `tests/test_setup_wizard.py`.
2. **Downloader with progress** - `download_assets(progress_cb)` streaming to temp then move; Miku model zip extract; bridge methods `get_setup_state()`, `run_setup()` (thread + push events `{"type":"setup", ...}`), `save_token(token)` (writes/updates `.env`, restart prompt); UI: first-run wizard panel (progress bars per asset, VB-Cable step reusing install_cable, token field, "start talking" finish).
3. **Dual-mode updater (TDD for mode pick)** - `updater.mode() -> "git"|"zip"` (`.git` dir present?); zip path: download `codeload.github.com/Fightersbane/neolunamiku/zip/refs/heads/main`, extract, overlay code dirs only (`app/ engine/ scripts/ tests/ bot.py requirements.txt VERSION CHANGELOG.md ...`), never touching `models/ .env config.json .venv audio/`; then pip sync + respawn (existing flow).
4. **Bootstrap + Inno script** - `installer/bootstrap.ps1` (ensure py 3.13 via winget, create `.venv`, pip install with the extra index + onnxruntime fix, launch app), `installer/neolunamiku.iss` (per-user LocalAppData install, Start Menu + Desktop icons from a generated `assets/miku.ico`, run bootstrap on first launch), `scripts/build_installer.ps1` (stage a clean source snapshot, run ISCC).
5. **Build + E2E on this machine** - install Inno Setup via winget, build `dist/neolunamiku-setup-<version>.exe`, install to a scratch location, run the wizard end-to-end (downloads land, app speaks), verify zip-overlay update path, then PR.
