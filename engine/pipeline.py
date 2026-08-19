"""Text -> Miku speech pipeline: a base TTS voice converted by an RVC model.

Two TTS engines feed the same RVC stage:
- "kokoro": local kokoro-onnx on the GPU (fast, offline-capable) — default
- "edge":   Microsoft edge-tts cloud voices (fallback; needs internet, ~1.3s RTT)

ultimate_rvc / kokoro are imported lazily inside the synthesis calls: they are
heavy imports (torch/CUDA/onnx) and this module must stay importable for tests
and for bot startup checks even before the models exist.

We call VoiceConverter directly instead of ultimate-rvc's run_pipeline wrapper:
the wrapper builds a fresh converter per call (reloading the embedder and the
Miku model onto the GPU every time), which costs ~15s per message. A held
converter skips those reloads via get_vc/load_hubert's own caching guards.
"""

import asyncio
import functools
import logging
import os
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
VOICE_MODELS_DIR = BASE_DIR / "models" / "voice_models"
MIKU_DIR = VOICE_MODELS_DIR / "Miku"
KOKORO_DIR = BASE_DIR / "models" / "kokoro"
AUDIO_DIR = BASE_DIR / "audio"
OUTPUT_DIR = AUDIO_DIR / "output"
MAX_TEXT_LEN = 500

# ultimate-rvc resolves its model directory from this at import time, so it is
# set here, before any lazy import of the package can happen.
os.environ.setdefault("URVC_VOICE_MODELS_DIR", str(VOICE_MODELS_DIR))

log = logging.getLogger(__name__)

# Mutated at runtime by the /voice, /pitch and /speed commands.
SETTINGS = {
    "model_name": "Miku",
    "engine": "kokoro",
    "voice": "af_heart",
    "speed": 1.1,
    "edge_pitch": "+20Hz",  # edge engine only; kokoro register comes from n_semitones
    "n_semitones": 10,      # RVC transpose up to Miku's register
    "index_rate": 0.5,
    "protect_rate": 0.33,
}

# Every preset is Miku — the entries differ only in the hidden base voice that
# feeds the Miku RVC model (flavors prosody) and the transpose that lands it in
# her register. The cloud backups keep the voice available if the local
# engine ever breaks; they need internet and are ~1s slower.
VOICE_PRESETS = {
    "Miku": {"engine": "kokoro", "voice": "af_heart", "n_semitones": 10},
    "Miku (soft)": {"engine": "kokoro", "voice": "af_bella", "n_semitones": 10},
    "Miku (cloud backup)": {"engine": "edge", "voice": "en-US-AnaNeural", "n_semitones": 2},
    "Miku (cloud backup 2)": {"engine": "edge", "voice": "en-US-JennyNeural", "n_semitones": 6},
}

# One GPU job at a time; discord.py's event loop stays free via to_thread.
_gpu_lock = asyncio.Lock()

_converter = None
_kokoro = None

# Timing split of the most recent synthesize() call, for the app's telemetry.
LAST_TIMING: dict = {}


def validate_text(text: str) -> str | None:
    """Return an error message for unusable input, or None if it is speakable."""
    if not text or not text.strip():
        return "There's nothing to say — the message is empty."
    if len(text) > MAX_TEXT_LEN:
        return f"Message too long ({len(text)}/{MAX_TEXT_LEN} characters)."
    return None


def edge_rate(speed: float) -> str:
    """Convert a speed multiplier to edge-tts's percent rate string."""
    return f"{round((speed - 1) * 100):+d}%"


def apply_voice_preset(name: str) -> None:
    """Switch base voice, engine and matching transpose; other settings persist."""
    SETTINGS.update(VOICE_PRESETS[name])


def model_available(model_dir: Path = MIKU_DIR) -> bool:
    """True if an RVC .pth model file is present in the model directory."""
    return model_dir.is_dir() and any(model_dir.glob("*.pth"))


def kokoro_available() -> bool:
    return (KOKORO_DIR / "kokoro-v1.0.onnx").is_file() and (
        KOKORO_DIR / "voices-v1.0.bin"
    ).is_file()


def purge_old_outputs(directory: Path, max_age_hours: float = 24) -> None:
    """Delete generated wavs older than max_age_hours; the pipeline's
    hash-named outputs accumulate forever otherwise."""
    if not directory.is_dir():
        return
    cutoff = time.time() - max_age_hours * 3600
    for wav in directory.rglob("*.wav"):
        try:
            if wav.stat().st_mtime < cutoff:
                wav.unlink()
        except OSError:
            log.warning("Could not purge %s", wav, exc_info=True)


def purge_outputs(max_age_hours: float = 24) -> None:
    purge_old_outputs(AUDIO_DIR, max_age_hours)


def _get_converter():
    """Build the voice converter once and keep every model resident on the GPU.

    Also caches two per-call disk loads upstream does on every synthesis:
    the RMVPE f0 predictor (172MB torch.load in get_f0) and the faiss
    speaker index (350MB faiss.read_index in pipeline()).
    """
    global _converter
    if _converter is None:
        from ultimate_rvc.rvc.infer import pipeline as rvc_infer_pipeline
        from ultimate_rvc.rvc.infer.infer import VoiceConverter

        rvc_infer_pipeline.RMVPE = functools.cache(rvc_infer_pipeline.RMVPE)
        rvc_infer_pipeline.faiss.read_index = functools.cache(
            rvc_infer_pipeline.faiss.read_index
        )
        _converter = VoiceConverter()
    return _converter


def _get_kokoro():
    """Load kokoro-onnx once, preferring the CUDA provider.

    onnxruntime-gpu needs torch's bundled CUDA DLLs on the DLL search path;
    without add_dll_directory it silently falls back to CPU (~1s vs ~0.2s).
    """
    global _kokoro
    if _kokoro is None:
        if not kokoro_available():
            raise FileNotFoundError(
                f"Kokoro model files missing from {KOKORO_DIR} — download "
                "kokoro-v1.0.onnx and voices-v1.0.bin from "
                "https://github.com/thewh1teagle/kokoro-onnx/releases"
            )
        import torch

        if torch.cuda.is_available():
            os.add_dll_directory(str(Path(torch.__file__).parent / "lib"))
            os.environ.setdefault("ONNX_PROVIDER", "CUDAExecutionProvider")
        from kokoro_onnx import Kokoro

        _kokoro = Kokoro(
            str(KOKORO_DIR / "kokoro-v1.0.onnx"),
            str(KOKORO_DIR / "voices-v1.0.bin"),
        )
        log.info("Kokoro loaded (providers: %s)", _kokoro.sess.get_providers())
    return _kokoro


def _kokoro_tts_blocking(text: str, out_path: Path) -> None:
    import soundfile as sf

    samples, sr = _get_kokoro().create(
        text, voice=SETTINGS["voice"], speed=SETTINGS["speed"]
    )
    sf.write(str(out_path), samples, sr)


async def _tts(text: str, out_path: Path) -> None:
    if SETTINGS["engine"] == "kokoro":
        await asyncio.to_thread(_kokoro_tts_blocking, text, out_path)
    else:
        import edge_tts

        await edge_tts.Communicate(
            text,
            SETTINGS["voice"],
            rate=edge_rate(SETTINGS["speed"]),
            pitch=SETTINGS["edge_pitch"],
        ).save(str(out_path))


def _convert_blocking(tts_path: Path, out_path: Path) -> None:
    from ultimate_rvc.core.generate.common import _get_rvc_files

    model_pth, model_index = _get_rvc_files(SETTINGS["model_name"])
    _get_converter().convert_audio(
        audio_input_path=str(tts_path),
        audio_output_path=str(out_path),
        model_path=str(model_pth),
        index_path=str(model_index) if model_index else "",
        pitch=SETTINGS["n_semitones"],
        f0_method="rmvpe",
        index_rate=SETTINGS["index_rate"],
        volume_envelope=1.0,
        protect=SETTINGS["protect_rate"],
        export_format="WAV",
    )


async def synthesize(text: str) -> Path:
    """Synthesize text to a wav file path. Serialized: one synthesis at a time."""
    async with _gpu_lock:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stem = uuid.uuid4().hex
        tts_path = OUTPUT_DIR / f"tts_{stem}.wav"
        out_path = OUTPUT_DIR / f"miku_{stem}.wav"
        t0 = time.monotonic()
        await _tts(text, tts_path)
        t1 = time.monotonic()
        try:
            await asyncio.to_thread(_convert_blocking, tts_path, out_path)
        finally:
            tts_path.unlink(missing_ok=True)
        t2 = time.monotonic()
        LAST_TIMING.update(
            tts_ms=round((t1 - t0) * 1000),
            rvc_ms=round((t2 - t1) * 1000),
            total_ms=round((t2 - t0) * 1000),
        )
        return out_path


async def warmup() -> None:
    """Absorb the one-time model loads (5-15s) so the first real /say is fast."""
    start = time.monotonic()
    await synthesize("Miku is online.")
    log.info("Warmup synthesis took %.1fs", time.monotonic() - start)
