# neolunamiku

![CI](https://github.com/Fightersbane/neolunamiku/actions/workflows/ci.yml/badge.svg)

Type a message and hear it spoken in a Hatsune Miku voice - in a Discord call, a game, or any program that takes microphone input. An accessibility tool for taking part in voice calls by typing.

Everything runs on your own GPU. Text goes through [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (local TTS), then RVC voice conversion with a community Miku model. Warm latency is about 1.1 s on an RTX 3060 Ti at under 1 GB of VRAM, so games run fine alongside it. No cloud services in the voice path.

## What works today (v0.2.0)

- **Desktop app** (`python -m app.main`): say box, global-hotkey overlay, system tray, message history with replay, GPU and latency readouts, settings for voice, speed, pitch, and devices.
- **Virtual microphone**: pick "CABLE Input" as the output and Discord sees Miku as your mic - works in DM calls, group calls, servers, and games. One-click VB-Cable install and a monitor output so you hear what you send.
- **Discord, three ways**: a server bot (`/say`, `/join`, `/leave`, `/voice`, `/pitch`, `/speed`), plain DMs to the bot, and `/say` inside your own DM conversations after a one-click user install. All Discord input is limited to an allowlist of user IDs, with an optional visible transcript in the chat.
- **Self-update**: the version chip checks this repo and installs updates only after you confirm.

## Setup (Windows)

Requires Python 3.13, an NVIDIA GPU, and [FFmpeg](https://ffmpeg.org) (`winget install Gyan.FFmpeg`).

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128
```

Models (about 1.2 GB, one time, not bundled):

1. A Hatsune Miku **RVC v2** model (`.pth` + `.index`) in `models/voice_models/Miku/`. Community models are on Hugging Face and voice-models.com; pick one trained for RVC v2 with rmvpe.
2. Kokoro TTS: [`kokoro-v1.0.onnx` and `voices-v1.0.bin`](https://github.com/thewh1teagle/kokoro-onnx/releases) in `models/kokoro/`.
3. RMVPE pitch model: [`rmvpe.pt`](https://huggingface.co/JackismyShephard/ultimate-rvc/tree/main/Resources/predictors) in `models/rvc/predictors/`.

Discord is optional. To enable it, create an application in the [developer portal](https://discord.com/developers/applications), copy the bot token, then:

```powershell
copy .env.example .env   # paste DISCORD_TOKEN (GUILD_ID is optional, for instant command sync)
```

The app derives invite and install links from the token and enables user-install automatically.

## Run

```powershell
python -m app.main        # desktop app
python -m engine --device cable   # headless: type lines, speak through the virtual mic
python bot.py             # standalone Discord bot only
```

Planned: Windows installer and Linux support - see [`CHANGELOG.md`](CHANGELOG.md) for what each version added. Contributing or curious how it works? See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## License

[MIT](LICENSE) for the code here. The Miku voice model is community-made, never distributed with this project, and for private non-commercial use only - do not redistribute it or publish content made with it. Hatsune Miku is a character of Crypton Future Media. Built on [ultimate-rvc](https://github.com/JackismyShephard/ultimate-rvc), [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), [discord.py](https://github.com/Rapptz/discord.py), and [VB-Audio Cable](https://vb-audio.com/Cable/).
