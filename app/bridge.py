"""pywebview js_api: the GUI's only door into the engine."""

import json
import logging
import threading

from engine import pipeline, playback

from app import telemetry
from app.history import History

log = logging.getLogger(__name__)


def parse_id_list(raw: str) -> list[str]:
    """Comma-separated Discord user IDs; only all-digit entries survive."""
    return [p.strip() for p in raw.split(",") if p.strip().isdigit()]


class JsApi:
    def __init__(self, engine_loop, player, cfg, save_cfg) -> None:
        self._loop = engine_loop
        self._player = player
        self._cfg = cfg
        self._save = save_cfg
        self.history = History()
        self._windows: list = []  # main.py appends webview windows
        self.state = "starting"  # starting | ready | error
        self.discord_client = None  # set by main.py when a token is configured
        self.discord_status = "no token configured"
        self.discord_links: dict = {}

    # ---- pushes -------------------------------------------------------
    def push(self, evt: dict) -> None:
        js = f"onEvent({json.dumps(evt)})"
        for w in list(self._windows):
            try:
                w.evaluate_js(js)
            except Exception:
                log.debug("evaluate_js failed", exc_info=True)

    def set_state(self, state: str, error: str | None = None) -> None:
        self.state = state
        evt = {"type": "state", "state": state}
        if error:
            evt["error"] = error
        self.push(evt)

    # ---- overridden by main.py ----------------------------------------
    def _rebind_hotkey(self, hotkey: str) -> bool:
        return True

    def show_overlay(self) -> None:
        pass

    def hide_overlay(self) -> None:
        pass

    # ---- called from JS ------------------------------------------------
    async def _speak_job(self, text: str, origin: str = "app") -> None:
        """Synthesize and route to the active sink. Runs on the engine loop;
        also the entry point for Discord-originated speech."""
        err = pipeline.validate_text(text)
        if err:
            raise ValueError(err)
        wav = await pipeline.synthesize(text)
        entry = self.history.add(text, wav, dict(pipeline.LAST_TIMING), origin=origin)
        routed_to_voice = False
        if self._cfg["mode"] == "bot" and self.discord_client is not None:
            routed_to_voice = await self.discord_client.play_voice(wav)
        if not routed_to_voice:
            await self._player.enqueue(wav)
        self.push({"type": "speaking", "entry": entry})
        self.push({"type": "history", "items": self.history.items()})

    def say(self, text: str) -> dict:
        err = pipeline.validate_text(text)
        if err:
            return {"ok": False, "error": err}

        def done(fut):
            exc = fut.exception()
            if exc:
                log.error("say failed", exc_info=exc)
                self.set_state("error", str(exc))

        self._loop.submit(self._speak_job(text)).add_done_callback(done)
        return {"ok": True}

    def set_discord_status(self, status: str) -> None:
        self.discord_status = status
        self.push({"type": "discord", "status": status})

    def get_state(self) -> dict:
        return {
            "ok": True,
            "state": self.state,
            "settings": dict(self._cfg),
            "presets": list(pipeline.VOICE_PRESETS),
            "last_timing": dict(pipeline.LAST_TIMING),
            "discord": {"status": self.discord_status, **self.discord_links},
            "version": self._version(),
        }

    @staticmethod
    def _version() -> str:
        from app import updater

        return updater.current_version()

    def set_setting(self, key: str, value) -> dict:
        if key == "preset":
            if value not in pipeline.VOICE_PRESETS:
                return {"ok": False, "error": f"Unknown voice {value!r}."}
            pipeline.apply_voice_preset(value)
            self._cfg["n_semitones"] = pipeline.SETTINGS["n_semitones"]
        elif key == "speed":
            pipeline.SETTINGS["speed"] = float(value)
        elif key == "n_semitones":
            pipeline.SETTINGS["n_semitones"] = int(value)
        elif key == "device":
            idx = None if value is None else int(value)
            self._player.device = idx
            value = self._device_name(idx)  # persist by name; indices shift
        elif key == "monitor_device":
            idx = None if value is None else int(value)
            self._player.monitor_device = idx
            value = self._device_name(idx)
        elif key == "hotkey":
            if not self._rebind_hotkey(str(value)):
                return {"ok": False, "error": f"Could not bind {value!r} — try a form like ctrl+shift+m."}
        elif key == "mode":
            if value not in ("mic", "bot"):
                return {"ok": False, "error": f"Unknown mode {value!r}."}
        elif key == "allowed_dm_users":
            value = parse_id_list(str(value))
        else:
            return {"ok": False, "error": f"Unknown setting {key!r}."}
        self._cfg[key] = value
        self._save(self._cfg)
        return {"ok": True}

    @staticmethod
    def _device_name(idx: int | None) -> str | None:
        if idx is None:
            return None
        for d in playback.list_output_devices():
            if d["index"] == idx:
                return d["name"]
        return None

    def list_devices(self) -> dict:
        devices = playback.list_output_devices()
        return {
            "ok": True,
            "devices": devices,
            "cable": playback.find_virtual_cable(devices),
        }

    def test_tone(self) -> dict:
        threading.Thread(
            target=playback.test_tone, args=(self._player.device,), daemon=True
        ).start()
        return {"ok": True}

    def get_history(self) -> dict:
        return {"ok": True, "items": self.history.items()}

    def replay(self, entry_id: int) -> dict:
        entry = self.history.get(int(entry_id))
        if not entry:
            return {"ok": False, "error": "That message's audio is gone."}
        self._loop.submit(self._player.enqueue(entry["wav"]))
        return {"ok": True}

    def install_cable(self) -> dict:
        def run():
            try:
                from app import cable_install

                self.push({"type": "cable", "status": "downloading"})
                cable_install.download_and_install()
                # No in-process rescan: re-initializing PortAudio while the
                # player exists corrupts its state. A restart picks it up.
                self.push({"type": "cable", "status": "restart_needed"})
            except Exception as exc:
                log.exception("VB-Cable install failed")
                self.push({"type": "cable", "status": "failed", "error": str(exc)})

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def check_update(self) -> dict:
        from app import updater

        try:
            return {"ok": True, **updater.check()}
        except Exception as exc:
            log.exception("update check failed")
            return {"ok": False, "error": f"Update check failed: {type(exc).__name__}"}

    def apply_update(self) -> dict:
        def run():
            from app import updater

            try:
                self.push({"type": "update", "status": "updating"})
                updater.apply()
                self.push({"type": "update", "status": "restarting"})
                updater.spawn_new_instance()
                self.quit_app()
            except Exception as exc:
                log.exception("update failed")
                self.push({"type": "update", "status": "failed", "error": str(exc)})

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def quit_app(self) -> None:  # replaced by main.py with a full shutdown
        pass

    def open_cable_page(self) -> dict:
        import webbrowser

        webbrowser.open("https://vb-audio.com/Cable/")
        return {"ok": True}

    def open_discord_link(self, kind: str) -> dict:
        import webbrowser

        link = self.discord_links.get(f"{kind}_link")
        if not link:
            return {"ok": False, "error": "No Discord token configured."}
        webbrowser.open(link)
        return {"ok": True}

    def get_telemetry(self) -> dict:
        return {
            "ok": True,
            "gpu": telemetry.gpu_stats(),
            "last_timing": dict(pipeline.LAST_TIMING),
        }
