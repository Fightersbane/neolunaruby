# Development

## Layout

```
app/       pywebview desktop app (windows, tray, hotkey, bridge, updater, ui/)
engine/    synthesis and audio: pipeline, playback, discord client, vendored rvc/
bot.py     standalone Discord bot entry point
scripts/   manual tools (smoke_test.py: synthesize to wav, print latency)
tests/     unit tests - hardware-free by design (audio/GPU seams are faked)
docs/      specs and implementation plans
```

## Environment

Python 3.13 venv at `.venv`. See `requirements.txt` for install commands,
the onnxruntime post-install step, and optional torch pruning.

## Commands

```powershell
.venv\Scripts\python.exe -m pytest -q                    # unit tests
.venv\Scripts\python.exe scripts\smoke_test.py "text"    # real synthesis + latency
.venv\Scripts\python.exe -m app.main                     # desktop app
.venv\Scripts\python.exe -m engine --device cable        # headless mic mode
```

## Workflow

`main` is branch-protected: feature branch -> commit -> push -> PR -> CI green ->
squash-merge. The in-app updater fast-forwards users to `origin/main`, so main
must always be releasable. Bump `VERSION` and `CHANGELOG.md` on notable merges.

Conventions, performance gotchas, and hard-won audio/Windows lessons live in
[`claude.md`](../claude.md) - read it before touching `engine/`.
