from pathlib import Path

from app import startup
from app.bridge import MAX_PHRASE_LEN, MAX_PHRASES, parse_phrases


class TestParsePhrases:
    def test_splits_lines_and_strips(self):
        assert parse_phrases("yes\n  no  \nbrb") == ["yes", "no", "brb"]

    def test_drops_blank_lines(self):
        assert parse_phrases("yes\n\n\n   \nno") == ["yes", "no"]

    def test_empty_input(self):
        assert parse_phrases("") == []

    def test_caps_phrase_count(self):
        many = "\n".join(f"p{i}" for i in range(50))
        assert len(parse_phrases(many)) == MAX_PHRASES

    def test_truncates_overlong_phrase(self):
        assert len(parse_phrases("x" * 500)[0]) == MAX_PHRASE_LEN


class TestStartupCommand:
    def test_prefers_pythonw_to_avoid_console_window(self, tmp_path):
        (tmp_path / "python.exe").write_bytes(b"\x00")
        (tmp_path / "pythonw.exe").write_bytes(b"\x00")
        cmd = startup.startup_command(Path("C:/app"), tmp_path / "python.exe")
        assert "pythonw.exe" in cmd

    def test_falls_back_to_python(self, tmp_path):
        (tmp_path / "python.exe").write_bytes(b"\x00")
        cmd = startup.startup_command(Path("C:/app"), tmp_path / "python.exe")
        assert "pythonw.exe" not in cmd
        assert "python.exe" in cmd

    def test_includes_base_dir_and_entry_point(self, tmp_path):
        (tmp_path / "python.exe").write_bytes(b"\x00")
        cmd = startup.startup_command(Path("C:/app"), tmp_path / "python.exe")
        assert "C:/app" in cmd or r"C:\app" in cmd
        assert "app.main" in cmd
