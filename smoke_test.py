"""Headless pipeline check: text -> Miku wav, no Discord involved.

Usage: python smoke_test.py "Hello, this is a test"

Synthesizes twice to show cold vs. warm latency (warm must be well under 2s
for live conversation) and prints the output path so you can listen and judge
how Miku it sounds. Tune pipeline.SETTINGS from what you hear.
"""

import asyncio
import sys
import time

from engine import pipeline


async def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello! This is Miku's smoke test."

    if not pipeline.model_available():
        sys.exit(
            "No Miku model found. Download a community 'Hatsune Miku RVC v2' model and put "
            f"the .pth and .index files in {pipeline.MIKU_DIR}"
        )

    print(f"Synthesizing (cold): {text!r}")
    start = time.monotonic()
    wav = await pipeline.synthesize(text)
    cold = time.monotonic() - start
    size = wav.stat().st_size
    assert size > 1000, f"Output wav suspiciously small ({size} bytes): {wav}"
    print(f"  cold: {cold:.1f}s -> {wav} ({size / 1024:.0f} KiB)")

    # A typical short conversational message; ~1.3s of the budget is the
    # edge-tts cloud round-trip, the rest is RVC on the GPU.
    warm_text = "hey guys, what are we playing tonight?"
    print(f"Synthesizing (warm): {warm_text!r}")
    start = time.monotonic()
    wav2 = await pipeline.synthesize(warm_text)
    warm = time.monotonic() - start
    print(f"  warm: {warm:.1f}s -> {wav2}")

    print()
    print("Listen to the wavs above and tune SETTINGS (n_semitones, index_rate, tts_voice).")
    if warm >= 2.5:
        sys.exit(f"Warm latency TOO SLOW ({warm:.1f}s, target < 2.5s)")
    print(f"Warm latency OK ({warm:.1f}s, target < 2.5s)")


if __name__ == "__main__":
    asyncio.run(main())
