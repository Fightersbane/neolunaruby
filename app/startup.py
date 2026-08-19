"""Optional "start with Windows" support, via the per-user Run registry key.

Uses pythonw so the app comes up at login without a console window, and
injects the repo path so `app.main` imports regardless of the working
directory Windows hands us.
"""

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "neolunaruby"
BASE = Path(__file__).resolve().parents[1]


def startup_command(base: Path = BASE, python: Path | None = None) -> str:
    python = Path(python or sys.executable)
    pythonw = python.with_name("pythonw.exe")
    exe = pythonw if pythonw.is_file() else python
    return (
        f'"{exe}" -c "import sys;sys.path.insert(0,r\'{base}\');'
        'from app.main import main;main()"'
    )


def is_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
