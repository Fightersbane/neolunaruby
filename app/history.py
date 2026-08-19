"""Session message history: what was said, its wav, and how long it took."""

import time
from collections import deque
from pathlib import Path


class History:
    def __init__(self, cap: int = 100) -> None:
        self._entries: deque = deque(maxlen=cap)
        self._next_id = 1

    def add(self, text: str, wav_path, latency_ms: dict) -> dict:
        entry = {
            "id": self._next_id,
            "text": text,
            "wav": str(wav_path),
            "latency_ms": latency_ms,
            "ts": time.time(),
        }
        self._next_id += 1
        self._entries.append(entry)
        return entry

    def items(self) -> list[dict]:
        live = [e for e in self._entries if Path(e["wav"]).exists()]
        return list(reversed(live))

    def get(self, entry_id: int):
        for e in self.items():
            if e["id"] == entry_id:
                return e
        return None
