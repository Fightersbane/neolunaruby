"""pywebview js_api: the GUI's only door into the engine."""

import json
import logging
import threading

from engine import pipeline, playback

from app import telemetry
from app.history import History

log = logging.getLogger(__name__)


class JsApi:
    def __init__(self, engine_loop, player, cfg, save_cfg) -> None:
        self._loop = engine_loop
        self._player = player
        self._cfg = cfg
        self._save = save_cfg
        self.history = History()
        self._windows: list = []  # main.py appends webview windows
        self.state = "starting"  # starting | ready | error

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
    def say(self, text: str) -> dict:
        err = pipeline.validate_text(text)
        if err:
            return {"ok": False, "error": err}

        async def job():
            wav = await pipeline.synthesize(text)
            entry = self.history.add(text, wav, dict(pipeline.LAST_TIMING))
            await self._player.enqueue(wav)
            self.push({"type": "speaking", "entry": entry})
            self.push({"type": "history", "items": self.history.items()})

        def done(fut):
            exc = fut.exception()
            if exc:
                log.error("say failed", exc_info=exc)
                self.set_state("error", str(exc))

        self._loop.submit(job()).add_done_callback(done)
        return {"ok": True}

    def get_state(self) -> dict:
        return {
            "ok": True,
            "state": self.state,
            "settings": dict(self._cfg),
            "presets": list(pipeline.VOICE_PRESETS),
            "last_timing": dict(pipeline.LAST_TIMING),
        }

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
            self._player.device = None if value is None else int(value)
        elif key == "hotkey":
            if not self._rebind_hotkey(str(value)):
                return {"ok": False, "error": f"Could not bind {value!r} — try a form like ctrl+shift+m."}
        else:
            return {"ok": False, "error": f"Unknown setting {key!r}."}
        self._cfg[key] = value
        self._save(self._cfg)
        return {"ok": True}

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
                self.push({"type": "cable", "status": "rescanning"})
                cable_install.rescan_devices()
                devices = playback.list_output_devices()
                cable = playback.find_virtual_cable(devices)
                status = "done" if cable is not None else "restart_needed"
                self.push({"type": "cable", "status": status, "cable": cable})
            except Exception as exc:
                log.exception("VB-Cable install failed")
                self.push({"type": "cable", "status": "failed", "error": str(exc)})

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def open_cable_page(self) -> dict:
        import webbrowser

        webbrowser.open("https://vb-audio.com/Cable/")
        return {"ok": True}

    def get_telemetry(self) -> dict:
        return {
            "ok": True,
            "gpu": telemetry.gpu_stats(),
            "last_timing": dict(pipeline.LAST_TIMING),
        }
