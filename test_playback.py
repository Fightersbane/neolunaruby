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
