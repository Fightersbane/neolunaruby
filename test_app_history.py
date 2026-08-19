from app.history import History


def _add(h, tmp_path, name):
    wav = tmp_path / name
    wav.write_bytes(b"\x00")
    return h.add(name, wav, {"total": 1000})


class TestHistory:
    def test_newest_first(self, tmp_path):
        h = History()
        _add(h, tmp_path, "a.wav")
        _add(h, tmp_path, "b.wav")
        assert [e["text"] for e in h.items()] == ["b.wav", "a.wav"]

    def test_cap_evicts_oldest(self, tmp_path):
        h = History(cap=2)
        for n in ("a.wav", "b.wav", "c.wav"):
            _add(h, tmp_path, n)
        assert [e["text"] for e in h.items()] == ["c.wav", "b.wav"]

    def test_items_drops_deleted_wavs(self, tmp_path):
        h = History()
        e = _add(h, tmp_path, "a.wav")
        _add(h, tmp_path, "b.wav")
        (tmp_path / "a.wav").unlink()
        assert [x["text"] for x in h.items()] == ["b.wav"]
        assert h.get(e["id"]) is None

    def test_get_by_id(self, tmp_path):
        h = History()
        e = _add(h, tmp_path, "a.wav")
        assert h.get(e["id"])["text"] == "a.wav"
