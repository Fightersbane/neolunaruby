import asyncio

from engine import playback

RAW = [
    {"name": "Microphone (Realtek)", "max_output_channels": 0, "index": 0},
    {"name": "Speakers (Realtek)", "max_output_channels": 2, "index": 1},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2, "index": 2},
]

# Windows exposes the same physical device once per host API; only the
# WASAPI entries should survive when any exist.
RAW_MULTI_API = [
    {"name": "Speakers (Realtek(R) Au", "max_output_channels": 2, "index": 1, "hostapi_name": "MME"},
    {"name": "Speakers (Realtek(R) Audio)", "max_output_channels": 2, "index": 5, "hostapi_name": "Windows DirectSound"},
    {"name": "Speakers (Realtek(R) Audio)", "max_output_channels": 2, "index": 9, "hostapi_name": "Windows WASAPI"},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2, "index": 10, "hostapi_name": "Windows WASAPI"},
]


class TestNormalizeDevices:
    def test_keeps_only_output_devices(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["index"] for d in devs] == [1, 2]

    def test_marks_default(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert [d["is_default"] for d in devs] == [True, False]

    def test_prefers_wasapi_entries_when_present(self):
        devs = playback._normalize_devices(RAW_MULTI_API, default_index=9)
        assert [d["index"] for d in devs] == [9, 10]
        assert devs[0]["is_default"] is True

    def test_keeps_all_when_no_wasapi(self):
        devs = playback._normalize_devices(RAW_MULTI_API[:2], default_index=1)
        assert [d["index"] for d in devs] == [1, 5]


class TestFindVirtualCable:
    def test_finds_cable_input(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert playback.find_virtual_cable(devs) == 2

    def test_none_when_absent(self):
        devs = playback._normalize_devices(RAW[:2], default_index=1)
        assert playback.find_virtual_cable(devs) is None


class TestDeviceIndexByName:
    def test_finds_index(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert playback.device_index_by_name("Speakers (Realtek)", devs) == 1

    def test_missing_returns_none(self):
        devs = playback._normalize_devices(RAW, default_index=1)
        assert playback.device_index_by_name("Gone (Unplugged)", devs) is None


class TestMonitorPlayback:
    def _wav(self, tmp_path):
        import numpy as np
        import soundfile as sf

        wav = tmp_path / "x.wav"
        sf.write(str(wav), np.zeros(100, dtype="float32"), 48000)
        return wav

    def test_monitor_plays_on_both_devices(self, monkeypatch, tmp_path):
        played = []
        player = playback.AudioPlayer(device=5)
        player.monitor_device = 7
        monkeypatch.setattr(player, "_play_to", lambda dev, data, sr: played.append(dev))
        player._play_blocking(self._wav(tmp_path))
        assert sorted(played) == [5, 7]

    def test_without_monitor_plays_once(self, monkeypatch, tmp_path):
        played = []
        player = playback.AudioPlayer(device=5)
        monkeypatch.setattr(player, "_play_to", lambda dev, data, sr: played.append(dev))
        player._play_blocking(self._wav(tmp_path))
        assert played == [5]

    def test_monitor_same_as_primary_not_duplicated(self, monkeypatch, tmp_path):
        played = []
        player = playback.AudioPlayer(device=5)
        player.monitor_device = 5
        monkeypatch.setattr(player, "_play_to", lambda dev, data, sr: played.append(dev))
        player._play_blocking(self._wav(tmp_path))
        assert played == [5]


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
