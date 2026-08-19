# neolunamiku

Discord TTS bot: type `/say <text>`, hear it in a Hatsune Miku voice in your voice channel.
Built as an accessibility tool so a mute friend can take part in voice calls.

Pipeline: edge-tts (base English voice) → RVC Miku voice conversion (CUDA) → Discord voice.

## Run

```powershell
.venv\Scripts\activate
python bot.py
```

Needs:
- `.env` with `DISCORD_TOKEN=...` (and optionally `GUILD_ID=...` for instant slash-command sync)
- A Miku RVC v2 model: `.pth` + `.index` in `models/voice_models/Miku/`
- FFmpeg on PATH (`winget install Gyan.FFmpeg`)
- Internet at speak time (edge-tts is a cloud service)

## Commands

| Command | What it does |
|---|---|
| `/say text` | Speak the text in the voice channel (auto-joins yours if needed) |
| `/join` / `/leave` | Bring Miku into / out of your voice channel |
| `/pitch -12..12` | Tune the RVC transpose if the voice sounds too low/high |
| `/voice Ana\|Jenny` | Switch the base TTS voice fed into the Miku model |

## Test without Discord

```powershell
python smoke_test.py "Hello, this is a test"
```

Prints cold vs. warm synthesis latency (warm should be < 2 s) and the output wav path — listen and tune `SETTINGS` in `pipeline.py`.

## Dev

```powershell
python -m pytest test_pipeline.py -q
```

Install deps: `pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128`

The Miku model is for private, non-commercial use — don't redistribute it or publish content with it.
