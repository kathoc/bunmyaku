import pytest
from jlangbase.paragraphs import paragraphs
from jlangbase.rhythm import mora_count, rhythm_map


@pytest.mark.parametrize("text,count", [("きゃく", 2), ("がっこう", 4), ("コーヒー", 4), ("しんぶん", 4), ("ｷｬｯﾄ", 3), ("東京", None), ("ゃ", None), ("ABC", None)])
def test_mora_is_not_character_count(text, count):
    assert mora_count(text) == count


def test_local_pattern_break_575_to_1346():
    steady = "あ" * 5 + "、" + "い" * 7 + "、" + "う" * 5 + "。"
    changed = "え" * 13 + "、" + "お" * 4 + "、" + "か" * 6 + "。"
    result = rhythm_map(paragraphs(steady * 3 + changed), "basic")
    assert result["local_changes"][0]["baseline_mora"] == [5, 7, 5]
    assert result["local_changes"][0]["current_mora"] == [13, 4, 6]
    assert result["local_changes"][0]["delta"] == [8, -3, 1]
    assert rhythm_map(paragraphs(steady * 4), "basic")["local_changes"] == []


def test_unknown_readings_are_not_characters():
    result = rhythm_map(paragraphs("東京の朝。"), "basic")
    assert result["cadences"][0]["mora"] == [None]
    assert result["mora_coverage"] == 0


def test_optional_real_dictionary():
    pytest.importorskip("sudachipy")
    pytest.importorskip("sudachidict_core")
    result = rhythm_map(paragraphs("東京。"), "sudachi")
    assert result["cadences"][0]["mora"] == [4]
