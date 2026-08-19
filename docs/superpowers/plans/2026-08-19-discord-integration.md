# Discord Integration (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The desktop app hosts the Discord client: `/say` works inside DM conversations (user-installable app), plain DMs to the bot are spoken, and a mic/bot mode toggle routes audio to the virtual mic or a server voice channel.

**Architecture:** New `engine/discord_client.py` (a `discord.Client` running on the app's EngineLoop) receives slash/DM inputs and calls back into `JsApi._speak_job`, which routes synthesized wavs to the local `AudioPlayer` (mic mode) or the Discord voice client (bot mode). `bot.py` stays standalone-usable.

**Tech Stack:** discord.py 2.7 (`allowed_installs`/`allowed_contexts` for user-install commands), existing engine/app packages.

**Spec:** `docs/superpowers/specs/2026-08-19-desktop-app-design.md`

## Global Constraints

- Same as prior plans (venv python, no run_pipeline, onnxruntime pin, Miku labels, sequential speech, commit trailer).
- Security: every Discord-originated input (slash or DM) must pass an allowlist of Discord user IDs from config; empty list = reject with a message that shows the requester's ID so it can be added.
- User-install commands only exist on GLOBAL sync — sync the tree globally, plus guild-scoped for instant testing.
- DM message content requires no privileged intent (exempt in DMs); keep all privileged intents off.

---

### Task 1: ID-list parsing + history origin (TDD)

**Files:** `app/bridge.py` (add `parse_id_list`), `app/history.py` (origin param), tests in `test_app_history.py` + new `test_app_bridge.py`.

**Interfaces:** `parse_id_list("123, 456x, 789") -> ["123", "789"]` (digits-only entries survive); `History.add(text, wav, latency_ms, origin="app")` stores `entry["origin"]`.

Steps: failing tests → run red → implement → green → commit `feat: id allowlist parsing and history origins`.

```python
# test_app_bridge.py
from app.bridge import parse_id_list

class TestParseIdList:
    def test_keeps_digit_entries_only(self):
        assert parse_id_list("123, 456x, 789 ,") == ["123", "789"]

    def test_empty_string(self):
        assert parse_id_list("") == []
```

```python
# in app/bridge.py (module level)
def parse_id_list(raw: str) -> list[str]:
    return [p.strip() for p in raw.split(",") if p.strip().isdigit()]
```

History: add `origin: str = "app"` param, store in entry; test asserts `h.add(...)["origin"] == "app"` and custom origin round-trips through `items()`.

### Task 2: engine/discord_client.py

**Files:** Create `engine/discord_client.py`; move `find_ffmpeg` from `bot.py` into `engine/playback.py` (bot.py imports it from there).

**Interfaces:**
- `MikuClient(on_speak, allowed_ids, guild_id=None, on_status=None)` — `on_speak(text: str, origin: str) -> Awaitable`, `allowed_ids() -> set[int]` (live from config), `on_status(str)` pushes "connected as X" / errors.
- `client.voice_connected -> bool`; `async client.play_voice(wav_path) -> bool` (False if no VC; serialized, uses FFmpegPCMAudio with `find_ffmpeg()`).
- Commands: `/say text` — `allowed_installs(guilds=True, users=True)` + `allowed_contexts(guilds=True, dms=True, private_channels=True)`; allowlist check (ephemeral rejection includes invoker's ID); defer → `on_speak` → ephemeral confirm. `/join`, `/leave` — guild-only, as in bot.py.
- `on_message`: DM channel + author allowlisted + not a bot → `on_speak(content, "dm")` + ✅ reaction.
- `setup_hook`: global `tree.sync()`, plus guild copy+sync when `guild_id` set.

Verify: `python -c "from engine.discord_client import MikuClient"` + full pytest. Commit `feat: engine-hosted discord client with DM and user-install say`.

### Task 3: Routing + settings in JsApi

**Files:** `app/bridge.py`, `app/config.py` (DEFAULTS: `allowed_dm_users: []`).

**Interfaces:**
- `JsApi.discord_client` (set by main), `JsApi.discord_status: str`, `set_discord_status(str)` (pushes `{"type":"discord","status":...}`).
- `async _speak_job(text, origin="app")` — validate, synthesize, history(origin), route: mode=="bot" and `discord_client.play_voice(wav)` succeeded → done, else `player.enqueue(wav)`; pushes speaking/history events. `say()` submits `_speak_job` (unchanged JS contract).
- `set_setting` new keys: `"mode"` (must be `mic`/`bot`), `"allowed_dm_users"` (string → `parse_id_list` → stored list).
- `get_state` adds `discord: {"status", "install_link", "invite_link"}` — links built from the app ID decoded from the token's first base64 segment (`https://discord.com/oauth2/authorize?client_id=<id>&integration_type=1&scope=applications.commands` for user-install; standard bot+applications.commands+permissions link for server invite).

Commit `feat: audio routing by mode and discord settings`.

### Task 4: main.py wiring + UI

**Files:** `app/main.py`, `app/ui/index.html`, `app/ui/app.js`, `app/ui/app.css`.

- main: `load_dotenv()`; if `DISCORD_TOKEN` set → create `MikuClient(on_speak=api._speak_job, allowed_ids=..., guild_id=os.getenv("GUILD_ID"), on_status=api.set_discord_status)`, `api.discord_client = client`, `loop.submit(client.start(token))`; on exit `loop.submit(client.close())` before `loop.stop()`.
- UI Voice tab, top: mode toggle (two segmented buttons: "🎤 Virtual mic" / "🤖 Server voice"); Discord section: status line (dot + text), "Allowed Discord user IDs" input + Save (comma-separated), copy-buttons for the user-install link and server invite link. `onEvent` handles `{"type":"discord"}`.
- Commit `feat: discord panel, mode toggle, client lifecycle`.

### Task 5: E2E (user-driven)

1. Portal: Installation tab → enable **User Install** context (owner does this once).
2. Restart app; UI shows "connected as RubyBot".
3. Add both users' Discord IDs to the allowlist.
4. DM the bot → spoken through the current sink; ✅ reaction appears.
5. Install the user-app via the install link; `/say hi` inside a DM conversation → spoken.
6. Toggle to bot mode, `/join` in a server VC → `/say` and app input route to the VC; toggle back to mic → routes to cable.
7. Full pytest; push.
