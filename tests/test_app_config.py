import json

from app import config


class TestLoad:
    def test_missing_file_returns_defaults(self, tmp_path):
        assert config.load(tmp_path / "nope.json") == config.DEFAULTS

    def test_corrupt_file_returns_defaults(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text("{not json")
        assert config.load(p) == config.DEFAULTS

    def test_merges_over_defaults_and_drops_unknown(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"hotkey": "f8", "junk": 1}))
        cfg = config.load(p)
        assert cfg["hotkey"] == "f8"
        assert "junk" not in cfg
        assert cfg["speed"] == config.DEFAULTS["speed"]


class TestSave:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "config.json"
        cfg = dict(config.DEFAULTS, hotkey="f9")
        config.save(p, cfg)
        assert config.load(p) == cfg
