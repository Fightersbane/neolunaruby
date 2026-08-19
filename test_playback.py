import asyncio

from engine import playback

RAW = [
    {"name": "Microphone (Realtek)", "max_output_channels": 0, "index": 0},
    {"name": "Speakers (Realtek)", "max_output_channels": 2, "index": 1},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2, "index": 2},
]


class TestNormalizeDevices:
    def test_keeps_only_output_devices(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["index"] for d in devs] == [1, 2]

    def test_marks_default(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["is_default"] for d in devs] == [True, False]


class TestFindVirtualCable:
    def test_finds_cable_input(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert playback.find_virtual_cable(devs) == 2

    def test_none_when_absent(self):
        devs = playback._normalize_devices(RAW[:2], default_index=1)
        assert playback.find_virtual_cable(devs) is None


class TestAudioPlayer:
    def _player_with_recorder(self, monkeypatch, played, delay=0.0):
        player = playback.AudioPlayer(device=None)

        def fake_play(path):
            import time

            time.sleep(delay)
            played.append(path)

        monkeypatch.setattr(player, "_play_blocking", fake_play)
        return player

    def test_plays_in_order(self, monkeypatch):
        async def run():
            played = []
            player = self._player_with_recorder(monkeypatch, played, delay=0.01)
            player.start()
            await player.enqueue("a.wav")
            await player.enqueue("b.wav")
            await player.enqueue("c.wav")
            await player.wait_idle()
            await player.stop()
            return played

        assert asyncio.run(run()) == ["a.wav", "b.wav", "c.wav"]

    def test_drain_discards_pending(self, monkeypatch):
        async def run():
            played = []
            player = self._player_with_recorder(monkeypatch, played, delay=0.05)
            player.start()
            await player.enqueue("a.wav")
            await player.enqueue("b.wav")
            await asyncio.sleep(0.01)  # a.wav is mid-play
            player.drain()
            await player.wait_idle()
            await player.stop()
            return played

        assert asyncio.run(run()) == ["a.wav"]
