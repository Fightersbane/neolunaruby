import os
import time

from engine import pipeline


class TestValidateText:
    def test_rejects_empty(self):
        assert pipeline.validate_text("") is not None

    def test_rejects_whitespace_only(self):
        assert pipeline.validate_text("   \n\t ") is not None

    def test_rejects_over_max_length(self):
        err = pipeline.validate_text("a" * (pipeline.MAX_TEXT_LEN + 1))
        assert err is not None
        assert str(pipeline.MAX_TEXT_LEN) in err

    def test_accepts_normal_text(self):
        assert pipeline.validate_text("hello everyone!") is None

    def test_accepts_exactly_max_length(self):
        assert pipeline.validate_text("a" * pipeline.MAX_TEXT_LEN) is None


class TestModelAvailable:
    def test_false_when_dir_missing(self, tmp_path):
        assert pipeline.model_available(tmp_path / "nope") is False

    def test_false_when_no_pth(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not a model")
        assert pipeline.model_available(tmp_path) is False

    def test_true_when_pth_present(self, tmp_path):
        (tmp_path / "miku.pth").write_bytes(b"\x00")
        assert pipeline.model_available(tmp_path) is True


class TestEdgeRate:
    def test_faster(self):
        assert pipeline.edge_rate(1.1) == "+10%"

    def test_neutral(self):
        assert pipeline.edge_rate(1.0) == "+0%"

    def test_slower(self):
        assert pipeline.edge_rate(0.85) == "-15%"

    def test_rounds_fractional_percent(self):
        assert pipeline.edge_rate(1.333) == "+33%"


class TestApplyVoicePreset:
    def test_applies_engine_voice_and_transpose(self):
        saved = dict(pipeline.SETTINGS)
        try:
            pipeline.apply_voice_preset("Miku (cloud backup)")
            assert pipeline.SETTINGS["engine"] == "edge"
            assert pipeline.SETTINGS["voice"] == "en-US-AnaNeural"
            assert pipeline.SETTINGS["n_semitones"] == 2
            pipeline.apply_voice_preset("Miku")
            assert pipeline.SETTINGS["engine"] == "kokoro"
            assert pipeline.SETTINGS["voice"] == "af_heart"
        finally:
            pipeline.SETTINGS.clear()
            pipeline.SETTINGS.update(saved)

    def test_all_presets_are_miku_labelled(self):
        assert all(name.startswith("Miku") for name in pipeline.VOICE_PRESETS)

    def test_preserves_speed_and_quality_settings(self):
        saved = dict(pipeline.SETTINGS)
        try:
            pipeline.SETTINGS["speed"] = 1.25
            pipeline.apply_voice_preset("Miku (cloud backup 2)")
            assert pipeline.SETTINGS["speed"] == 1.25
            assert pipeline.SETTINGS["index_rate"] == saved["index_rate"]
        finally:
            pipeline.SETTINGS.clear()
            pipeline.SETTINGS.update(saved)


class TestPurgeOldOutputs:
    def test_removes_old_keeps_recent(self, tmp_path):
        old = tmp_path / "old.wav"
        recent = tmp_path / "recent.wav"
        old.write_bytes(b"\x00")
        recent.write_bytes(b"\x00")
        stale = time.time() - 2 * 24 * 3600
        os.utime(old, (stale, stale))

        pipeline.purge_old_outputs(tmp_path, max_age_hours=24)

        assert not old.exists()
        assert recent.exists()

    def test_missing_dir_is_noop(self, tmp_path):
        pipeline.purge_old_outputs(tmp_path / "nope", max_age_hours=24)
