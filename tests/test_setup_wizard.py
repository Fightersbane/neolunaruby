from app import setup_wizard


def _make(base, rel, size=2048):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00" * size)


class TestMissingAssets:
    def test_all_missing_on_empty_dir(self, tmp_path):
        missing = setup_wizard.missing_assets(base=tmp_path)
        assert set(missing) == {a["name"] for a in setup_wizard.ASSETS}

    def test_present_assets_not_reported(self, tmp_path):
        kokoro = next(a for a in setup_wizard.ASSETS if a["name"] == "kokoro model")
        _make(tmp_path, kokoro["dest"], size=kokoro["min_bytes"])
        assert "kokoro model" not in setup_wizard.missing_assets(base=tmp_path)

    def test_truncated_file_counts_as_missing(self, tmp_path):
        kokoro = next(a for a in setup_wizard.ASSETS if a["name"] == "kokoro model")
        _make(tmp_path, kokoro["dest"], size=10)
        assert "kokoro model" in setup_wizard.missing_assets(base=tmp_path)


class TestSetupComplete:
    def test_complete_when_everything_present(self, tmp_path):
        for a in setup_wizard.ASSETS:
            _make(tmp_path, a["dest"], size=a["min_bytes"])
        assert setup_wizard.setup_complete(base=tmp_path) is True

    def test_incomplete_when_anything_missing(self, tmp_path):
        assert setup_wizard.setup_complete(base=tmp_path) is False
