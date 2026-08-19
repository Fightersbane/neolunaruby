"""Discord bot: /say speaks typed text into the voice channel in a Miku voice."""

import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv

import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("neolunamiku")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

MODEL_MISSING_MSG = (
    "No Miku voice model installed. Download a community 'Hatsune Miku RVC v2' model "
    "(voice-models.com, weights.gg, or Hugging Face) and place the .pth and .index files in "
    f"{pipeline.MIKU_DIR}"
)


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    # winget installs land here before a fresh shell picks up PATH
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for exe in packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"):
        return str(exe)
    sys.exit("ffmpeg not found. Install it with: winget install Gyan.FFmpeg (then open a new terminal)")


FFMPEG = find_ffmpeg()


class MikuBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.queue: asyncio.Queue[tuple[int, Path]] = asyncio.Queue()

    async def setup_hook(self) -> None:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        asyncio.create_task(self.playback_loop())
        pipeline.purge_outputs()
        if pipeline.model_available():
            asyncio.create_task(self.warmup())
        else:
            log.error(MODEL_MISSING_MSG)

    async def warmup(self) -> None:
        try:
            await pipeline.warmup()
            log.info("Pipeline warm — first /say will be fast.")
        except Exception:
            log.exception("Warmup failed; /say will still be attempted on demand.")

    async def playback_loop(self) -> None:
        while True:
            guild_id, wav = await self.queue.get()
            guild = self.get_guild(guild_id)
            vc = guild.voice_client if guild else None
            if isinstance(vc, discord.VoiceClient) and vc.is_connected():
                done = asyncio.Event()

                def after(err: Exception | None, done: asyncio.Event = done) -> None:
                    if err:
                        log.error("Playback error: %s", err)
                    self.loop.call_soon_threadsafe(done.set)

                try:
                    vc.play(discord.FFmpegPCMAudio(str(wav), executable=FFMPEG), after=after)
                    await done.wait()
                except Exception:
                    log.exception("Could not play %s", wav)
            else:
                log.warning("Not connected to voice; dropping queued message.")
            self.queue.task_done()

    def drain_queue(self) -> None:
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()


client = MikuBot()


@client.event
async def on_ready() -> None:
    log.info("Logged in as %s. Miku is ready.", client.user)


@client.tree.command(description="Speak a message into the voice channel as Miku")
@app_commands.guild_only()
@app_commands.describe(text="What Miku should say")
async def say(interaction: discord.Interaction, text: str) -> None:
    err = pipeline.validate_text(text)
    if err:
        await interaction.response.send_message(err, ephemeral=True)
        return
    if not pipeline.model_available():
        await interaction.response.send_message(MODEL_MISSING_MSG, ephemeral=True)
        return

    # Synthesis takes ~1-2s; past the 3s interaction deadline if queued behind others.
    await interaction.response.defer(ephemeral=True)

    vc = interaction.guild.voice_client
    if not (isinstance(vc, discord.VoiceClient) and vc.is_connected()):
        state = interaction.user.voice
        if state is None or state.channel is None:
            await interaction.followup.send("Join a voice channel first (or use /join).", ephemeral=True)
            return
        await state.channel.connect()

    try:
        wav = await pipeline.synthesize(text)
    except Exception as exc:
        log.exception("Synthesis failed for %r", text)
        await interaction.followup.send(
            f"Synthesis failed: {type(exc).__name__}. Check the bot console for details.", ephemeral=True
        )
        return

    await client.queue.put((interaction.guild_id, wav))
    await interaction.followup.send(f'Speaking: "{text}"', ephemeral=True)


@client.tree.command(description="Bring Miku into your current voice channel")
@app_commands.guild_only()
async def join(interaction: discord.Interaction) -> None:
    state = interaction.user.voice
    if state is None or state.channel is None:
        await interaction.response.send_message("You're not in a voice channel.", ephemeral=True)
        return
    vc = interaction.guild.voice_client
    if isinstance(vc, discord.VoiceClient) and vc.is_connected():
        await vc.move_to(state.channel)
    else:
        await state.channel.connect()
    await interaction.response.send_message(f"Joined {state.channel.name}.", ephemeral=True)


@client.tree.command(description="Disconnect Miku from voice")
@app_commands.guild_only()
async def leave(interaction: discord.Interaction) -> None:
    vc = interaction.guild.voice_client
    if isinstance(vc, discord.VoiceClient) and vc.is_connected():
        client.drain_queue()
        await vc.disconnect()
        await interaction.response.send_message("Left the voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("Not in a voice channel.", ephemeral=True)


@client.tree.command(description="Tune Miku's pitch (RVC transpose in semitones)")
@app_commands.guild_only()
@app_commands.describe(semitones="Semitones up (+) or down (-); default is +2")
async def pitch(interaction: discord.Interaction, semitones: app_commands.Range[int, -12, 12]) -> None:
    pipeline.SETTINGS["n_semitones"] = semitones
    await interaction.response.send_message(f"Pitch transpose set to {semitones:+d} semitones.", ephemeral=True)


@client.tree.command(description="Switch the base TTS voice fed into the Miku model")
@app_commands.guild_only()
@app_commands.choices(
    name=[app_commands.Choice(name=label, value=label) for label in pipeline.VOICE_PRESETS]
)
async def voice(interaction: discord.Interaction, name: app_commands.Choice[str]) -> None:
    pipeline.apply_voice_preset(name.value)
    await interaction.response.send_message(f"Base voice set to {name.value}.", ephemeral=True)


@client.tree.command(description="Set Miku's speaking speed")
@app_commands.guild_only()
@app_commands.describe(multiplier="1.0 = natural, 1.1 = slightly fast (default), up to 2.0")
async def speed(interaction: discord.Interaction, multiplier: app_commands.Range[float, 0.5, 2.0]) -> None:
    pipeline.SETTINGS["speed"] = multiplier
    await interaction.response.send_message(f"Speed set to {multiplier}x.", ephemeral=True)


def main() -> None:
    if not TOKEN:
        sys.exit("DISCORD_TOKEN is not set. Copy .env.example to .env and paste your bot token.")
    if not pipeline.model_available():
        log.warning(MODEL_MISSING_MSG)
    client.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
