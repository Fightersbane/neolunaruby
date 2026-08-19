"""Download and install the VB-Cable virtual audio driver from VB-Audio.

The zip comes straight from VB-Audio's official server (not redistributed by
us); the silent install (-i -h) still triggers one Windows UAC prompt.
"""

import logging
import subprocess
import tempfile
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

CABLE_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"


def download_and_install() -> None:
    import requests

    tmp = Path(tempfile.mkdtemp(prefix="vbcable_"))
    zip_path = tmp / "vbcable.zip"
    with requests.get(CABLE_URL, timeout=120) as r:
        r.raise_for_status()
        zip_path.write_bytes(r.content)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    exe = next(tmp.glob("**/VBCABLE_Setup_x64.exe"), None)
    if exe is None:
        raise FileNotFoundError("VBCABLE_Setup_x64.exe not found in the downloaded package")
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process -FilePath '{exe}' -ArgumentList '-i','-h' -Verb RunAs -Wait",
        ],
        check=True,
        timeout=300,
    )


def rescan_devices() -> None:
    """Make PortAudio pick up a device installed after startup."""
    import sounddevice as sd

    sd._terminate()
    sd._initialize()
