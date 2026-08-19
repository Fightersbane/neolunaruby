"""Engine-hosted Discord client: remote text inputs and the voice-channel sink.

Inputs (all allowlist-gated):
- /say — user-installable, works inside DM conversations and servers
- plain DMs sent to the bot
Outputs: hands text to the app via on_speak; plays wavs into a server VC when
the app is in bot mode.
"""

import asyncio
import logging

import discord
from discord import app_commands

from engine.playback import find_ffmpeg

log = logging.getLogger(__name__)


class MikuClient(discord.Client):
    def __init__(self, on_speak, allowed_ids, guild_id=None, on_status=None) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self._on_speak = on_speak          # async (text, origin) -> None
        self._allowed_ids = allowed_ids    # () -> set[int]
        self._guild_id = guild_id
        self._on_status = on_status or (lambda s: None)
        self._voice_lock = asyncio.Lock()
        self._ffmpeg = find_ffmpeg()
        self._register_commands()

    # ---- helpers -----------------------------------------------------
    def _allowed(self, user_id: int) -> bool:
        return user_id in self._allowed_ids()

    @property
    def voice_connected(self) -> bool:
        return any(g.voice_client and g.voice_client.is_connected() for g in self.guilds)

    async def play_voice(self, wav_path) -> bool:
        vc = next(
            (g.voice_client for g in self.guilds if g.voice_client and g.voice_client.is_connected()),
            None,
        )
        if vc is None:
            return False
        async with self._voice_lock:
            done = asyncio.Event()
            loop = asyncio.get_running_loop()

            def after(err, done=done):
                if err:
                    log.error("Voice playback error: %s", err)
                loop.call_soon_threadsafe(done.set)

            vc.play(discord.FFmpegPCMAudio(str(wav_path), executable=self._ffmpeg), after=after)
            await done.wait()
        return True

    # ---- lifecycle ----------------------------------------------------
    async def setup_hook(self) -> None:
        # user-install commands only exist on the GLOBAL sync
        await self.tree.sync()
        if self._guild_id:
            guild = discord.Object(id=int(self._guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_ready(self) -> None:
        log.info("Discord connected as %s", self.user)
        self._on_status(f"connected as {self.user}")

    # ---- DM input -------------------------------------------------------
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is not None or message.author.bot:
            return
        if not self._allowed(message.author.id):
            await message.channel.send(
                f"You're not on the allowlist. Ask the owner to add your ID: `{message.author.id}`"
            )
            return
        text = message.content.strip()
        if not text:
            return
        await self._on_speak(text, "dm")
        try:
            await message.add_reaction("✅")
        except discord.HTTPException:
            pass

    # ---- commands --------------------------------------------------------
    def _register_commands(self) -> None:
        @self.tree.command(description="Speak a message in Miku's voice")
        @app_commands.allowed_installs(guilds=True, users=True)
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        @app_commands.describe(text="What Miku should say")
        async def say(interaction: discord.Interaction, text: str) -> None:
            if not self._allowed(interaction.user.id):
                await interaction.response.send_message(
                    f"You're not on the allowlist. Ask the owner to add your ID: `{interaction.user.id}`",
                    ephemeral=True,
                )
                return
            await interaction.response.defer(ephemeral=True)
            try:
                await self._on_speak(text, "slash")
            except Exception as exc:
                log.exception("speak from /say failed")
                await interaction.followup.send(f"Couldn't speak that: {type(exc).__name__}", ephemeral=True)
                return
            await interaction.followup.send(f'Speaking: "{text}"', ephemeral=True)

        @self.tree.command(description="Bring Miku into your current voice channel")
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

        @self.tree.command(description="Disconnect Miku from voice")
        @app_commands.guild_only()
        async def leave(interaction: discord.Interaction) -> None:
            vc = interaction.guild.voice_client
            if isinstance(vc, discord.VoiceClient) and vc.is_connected():
                await vc.disconnect()
                await interaction.response.send_message("Left the voice channel.", ephemeral=True)
            else:
                await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
