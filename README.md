# neolunamiku

Type it, and Hatsune Miku says it in your voice call. 🎤

An accessibility tool for taking part in voice calls by typing. Runs entirely on your own GPU — text becomes Miku-voiced speech in about a second, spoken into a Discord voice channel today, and (soon) into a virtual microphone that works in any app, DM calls included.

**Voice pipeline:** [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) local TTS → [RVC](https://github.com/JackismyShephard/ultimate-rvc) voice conversion with a community Miku model → CUDA. No cloud services in the voice path; warm latency ~1.1 s on an RTX 3060 Ti at under 1 GB of VRAM (games run fine alongside it).

## Current status

- ✅ **Discord bot** — working. `/say`, `/join`, `/leave`, `/voice` (Miku variants), `/pitch`, `/speed`.
- ✅ **Desktop app** — working: main window with settings/telemetry/history-replay, global-hotkey overlay, system tray, output-device picker (point it at a virtual cable and it's a microphone in any app). Run: `python -m app.main`. Headless: `python -m engine --device cable`.
- 🚧 **In development** — Discord DM input (`/say` inside DM conversations), bot-mode toggle in the app.
- 🔮 **Planned** — Windows installer, slim build, Linux support, sing/cover mode. Design: [`docs/superpowers/specs/2026-08-19-desktop-app-design.md`](docs/superpowers/specs/2026-08-19-desktop-app-design.md).

## Setup (dev, Windows)

Requires: Python 3.13, an NVIDIA GPU, [FFmpeg](https://ffmpeg.org) (`winget install Gyan.FFmpeg`).

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128
```

**Models** (not bundled — ~1.2 GB total, one time):

1. A Hatsune Miku **RVC v2** model (`.pth` + `.index`) → `models/voice_models/Miku/`. Community models are on Hugging Face and voice-models.com; use one trained for RVC v2/rmvpe.
2. Kokoro TTS: [`kokoro-v1.0.onnx` + `voices-v1.0.bin`](https://github.com/thewh1teagle/kokoro-onnx/releases) → `models/kokoro/`.
3. RMVPE pitch model: [`rmvpe.pt`](https://huggingface.co/JackismyShephard/ultimate-rvc/tree/main/Resources/predictors) → `models/rvc/predictors/`.

**Discord bot**: create an application at the [developer portal](https://discord.com/developers/applications), copy the bot token, then:

```powershell
copy .env.example .env   # paste DISCORD_TOKEN and your server's GUILD_ID
python bot.py
```

Invite the bot with scopes `bot` + `applications.commands` and permissions View Channels / Connect / Speak. First launch warms the models (~30 s); after that `/say` responds in about a second.

## Test the voice without Discord

```powershell
python smoke_test.py "Hello, this is a test"
```

Prints cold/warm latency and the output wav path. Tune `SETTINGS` in `pipeline.py` (or use `/pitch` and `/speed` live).

## Development

```powershell
python -m pytest test_pipeline.py -q
```

Performance-critical details (resident model caching, onnxruntime pinning) are documented in [`claude.md`](claude.md) and as comments in `pipeline.py`.

## License & credits

Non-commercial accessibility project. The Miku RVC voice model is community-made, is **not** distributed with this repo, and is for private non-commercial use — don't redistribute it or publish content made with it. Hatsune Miku is © Crypton Future Media. Built on [ultimate-rvc](https://github.com/JackismyShephard/ultimate-rvc), [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), [discord.py](https://github.com/Rapptz/discord.py), and [VB-Audio Cable](https://vb-audio.com/Cable/) (planned).
