from app.bridge import parse_id_list


class TestParseIdList:
    def test_keeps_digit_entries_only(self):
        assert parse_id_list("123, 456x, 789 ,") == ["123", "789"]

    def test_empty_string(self):
        assert parse_id_list("") == []
