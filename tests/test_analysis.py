import pytest
from jlangbase.analysis import Analyzer, metrics, split_sentences


@pytest.mark.parametrize("text,expected", [
    ("雨が降る。明日は晴れ！", 2), ("「本当？！」\nはい。", 2),
    ("Version 3.14です。OK?\n次", 3), ("", 0), ("……（えっ！？）\n続く", 2),
    ("https://example.com/a?b=1 を見る。次。", 2),
])
def test_sentences(text, expected):
    assert len(split_sentences(text)) == expected


def test_known_character_ratios():
    result = metrics("漢あアA")
    assert result["char_count"] == 4
    assert result["char_type_ratios"] == dict(kanji=.25, hiragana=.25, katakana=.25, ascii=.25, other=0)
    assert metrics("")["mean_sentence_length"] == 0
    assert metrics("…...！?\n")["punctuation_counts"]["ellipsis"] == 2


def test_basic_explicitly_has_no_tokens():
    analyzer = Analyzer("basic")
    result = analyzer.analyze({"text": "猫が走る。"})
    assert result["sentences"][0]["tokens"] == []
    assert not analyzer.info["morphology_available"]


def test_sudachi_real_morphology():
    pytest.importorskip("sudachipy")
    pytest.importorskip("sudachidict_core")
    analyzer = Analyzer("sudachi")
    tokens = analyzer.tokens("魚を食べた。")
    assert any(t["lemma"] == "食べる" and t["surface"] == "食べ" for t in tokens)
    assert all(t["pos"] and t["normalized_form"] for t in tokens)
