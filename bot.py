"""Standalone Discord bot: voice-channel output without the desktop app.

Shares the allowlist, commands and voice sink with the app (engine/discord_client.py);
settings come from the same config.json, so both entry points behave identically.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from app import config
from engine import pipeline
from engine.discord_client import MikuClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("neolunaruby")

load_dotenv()
async def _run() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN is not set. Copy .env.example to .env and paste your bot token.")
    if not pipeline.model_available():
        sys.exit(f"No voice model installed. Put a .pth and .index in {pipeline.MIKU_DIR}")

    cfg = config.load(Path(__file__).resolve().parent / "config.json")
    pipeline.apply_voice_preset(cfg["preset"])
    pipeline.SETTINGS["speed"] = cfg["speed"]
    pipeline.SETTINGS["n_semitones"] = cfg["n_semitones"]
    pipeline.purge_outputs()

    client: MikuClient | None = None

    async def speak(text: str, origin: str) -> None:
        wav = await pipeline.synthesize(text)
        if not await client.play_voice(wav):
            log.warning("Not in a voice channel - use /join first. (%s)", origin)

    client = MikuClient(
        on_speak=speak,
        allowed_ids=lambda: {int(x) for x in cfg["allowed_dm_users"]},
        guild_id=os.getenv("GUILD_ID"),
        on_status=lambda s: log.info("Discord: %s", s),
        say_posts_text=lambda: cfg["say_posts_text"],
        input_enabled=lambda: cfg["accept_discord_input"],
    )

    async with client:
        asyncio.create_task(_warm())
        await client.start(token)


async def _warm() -> None:
    try:
        await pipeline.warmup()
        log.info("Pipeline warm - the first message will be fast.")
    except Exception:
        log.exception("Warmup failed; synthesis will still be attempted on demand.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
