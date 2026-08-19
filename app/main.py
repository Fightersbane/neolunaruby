"""neolunamiku desktop app entry point: window + overlay + hotkey + tray."""

import logging
import threading
from pathlib import Path

import webview

from engine import pipeline, playback

from app import config
from app.bridge import JsApi
from app.engineloop import EngineLoop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE.parent / "config.json"


async def _start_player(player) -> None:
    player.start()


def _tray_icon_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(57, 197, 187, 255))  # Miku teal
    return img


def main() -> None:
    cfg = config.load(CONFIG_PATH)
    pipeline.apply_voice_preset(cfg["preset"])
    pipeline.SETTINGS["speed"] = cfg["speed"]
    pipeline.SETTINGS["n_semitones"] = cfg["n_semitones"]
    pipeline.purge_outputs()

    loop = EngineLoop()
    loop.start()
    devices = playback.list_output_devices()

    def _resolve(name):
        return playback.device_index_by_name(name, devices) if name else None

    player = playback.AudioPlayer(
        device=_resolve(cfg["device"]),
        monitor_device=_resolve(cfg["monitor_device"]),
    )
    loop.submit(_start_player(player)).result(timeout=10)

    api = JsApi(loop, player, cfg, lambda c: config.save(CONFIG_PATH, c))

    window = webview.create_window(
        "neolunamiku",
        url=str(BASE / "ui" / "index.html"),
        js_api=api,
        width=560,
        height=720,
        min_size=(480, 560),
        background_color="#0e1416",
    )
    overlay = webview.create_window(
        "miku-overlay",
        url=str(BASE / "ui" / "overlay.html"),
        js_api=api,
        width=440,
        height=58,
        frameless=True,
        on_top=True,
        hidden=True,
        background_color="#0e1416",
    )
    api._windows.extend([window, overlay])

    # ---- overlay + hotkey ------------------------------------------------
    def _force_foreground(title: str) -> None:
        """Steal foreground focus for our window. Windows only grants
        SetForegroundWindow to the active process; a synthetic Alt press is the
        long-standing sanctioned nudge that lifts that restriction."""
        import ctypes
        import time as _time

        u32 = ctypes.windll.user32
        hwnd = 0
        for _ in range(10):
            hwnd = u32.FindWindowW(None, title)
            if hwnd:
                break
            _time.sleep(0.05)
        if not hwnd:
            return
        keyboard.press_and_release("alt")
        u32.ShowWindow(hwnd, 9)  # SW_RESTORE
        u32.SetForegroundWindow(hwnd)

    def show_overlay():
        overlay.show()
        try:
            _force_foreground("miku-overlay")
            overlay.evaluate_js("focusInput()")
        except Exception:
            log.debug("overlay focus failed", exc_info=True)

    def hide_overlay():
        overlay.hide()

    api.show_overlay = show_overlay
    api.hide_overlay = hide_overlay

    import keyboard

    hotkey_state = {"handle": None}

    def bind_hotkey(hk: str) -> bool:
        try:
            new_handle = keyboard.add_hotkey(hk, show_overlay)
        except (ValueError, KeyError):
            return False
        if hotkey_state["handle"] is not None:
            try:
                keyboard.remove_hotkey(hotkey_state["handle"])
            except (KeyError, ValueError):
                pass
        hotkey_state["handle"] = new_handle
        return True

    api._rebind_hotkey = bind_hotkey
    if not bind_hotkey(cfg["hotkey"]):
        log.error("Could not bind hotkey %r", cfg["hotkey"])

    # ---- system tray -------------------------------------------------------
    import pystray

    def tray_show(icon, item):
        window.show()

    def tray_quit(icon, item):
        icon.stop()
        for w in (overlay, window):
            try:
                w.destroy()
            except Exception:
                pass

    tray = pystray.Icon(
        "neolunamiku",
        _tray_icon_image(),
        "neolunamiku",
        menu=pystray.Menu(
            pystray.MenuItem("Show", tray_show, default=True),
            pystray.MenuItem("Quit", tray_quit),
        ),
    )
    tray.run_detached()

    def on_closing():
        window.hide()
        return False  # cancel close; keep running in the tray

    window.events.closing += on_closing

    # ---- warmup (async so the window appears immediately) -----------------
    def warm():
        try:
            loop.submit(pipeline.warmup()).result(timeout=300)
            api.set_state("ready")
        except Exception as exc:
            log.exception("warmup failed")
            api.set_state("error", f"Voice engine failed to start: {exc}")

    threading.Thread(target=warm, daemon=True).start()

    try:
        webview.start()
    finally:
        tray.stop()
        keyboard.unhook_all()
        loop.stop()


if __name__ == "__main__":
    main()
