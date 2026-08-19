"""Headless driver: synthesize typed text and play it to an output device."""

import argparse
import asyncio
import sys

from engine import pipeline, playback


def _resolve_device(arg: str | None) -> int | None:
    if arg is None:
        return None
    devices = playback.list_output_devices()
    if arg == "cable":
        cable = playback.find_virtual_cable(devices)
        if cable is None:
            sys.exit("No VB-Audio Cable found. Install it from https://vb-audio.com/Cable/")
        return cable
    return int(arg)


async def _speak_loop(device: int | None, one_shot: str | None) -> None:
    if not pipeline.model_available():
        sys.exit(f"No Miku model in {pipeline.MIKU_DIR}")
    player = playback.AudioPlayer(device=device)
    player.start()
    await pipeline.warmup()
    print("ready")

    async def say(text: str) -> None:
        err = pipeline.validate_text(text)
        if err:
            print(err, file=sys.stderr)
            return
        wav = await pipeline.synthesize(text)
        await player.enqueue(wav)

    if one_shot is not None:
        await say(one_shot)
    else:
        while True:
            # read stdin off-thread: a blocking read would stall the playback task
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line or not line.strip():
                break
            await say(line.strip())
    await player.wait_idle()
    await player.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="engine", description="Miku voice engine (headless)")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device", help="output device index, or 'cable'")
    parser.add_argument("text", nargs="?", help="speak this and exit; omit for stdin REPL")
    args = parser.parse_args()

    if args.list_devices:
        for d in playback.list_output_devices():
            marker = "*" if d["is_default"] else " "
            print(f"{marker} {d['index']:>3}  {d['name']}")
        return
    asyncio.run(_speak_loop(_resolve_device(args.device), args.text))


if __name__ == "__main__":
    main()
