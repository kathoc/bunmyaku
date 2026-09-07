import json
import pytest
from jlangbase.craft import reading_map, knowledge, load_policy, write_brief, write_map
from jlangbase.db import text_hash
from jlangbase.paragraphs import paragraphs

TEXT = "# 題\n\n彼は勝ったので困っていた。\n\n勝者が片付ける約束だった。\n\n私はその約束だけ覚えている。"


def review():
    return {"text_hash": text_hash(TEXT), "reviewer": "test", "reviewer_kind": "model", "nodes": [], "frictions": [{
        "id": "delay", "kind": "delayed_explanation", "anchor": {"paragraph": 1, "quote": "勝ったので困っていた"},
        "foothold": {"paragraph": 1, "quote": "彼は勝った"}, "reader_question": "なぜ困るか", "benefit": "予想を持てる", "risk": "唐突さ", "decision": "test", "decision_reason": "読者比較で確かめる", "necessity": "optional", "resolution": "later", "payoff": {"paragraph": 2, "quote": "勝者が片付ける約束"}, "confidence": .8}]}


def test_blocks_preserve_locations_and_ignore_code():
    text = "---\ntitle: test\n---\n# 見出し\n\n本文。\n続く。\n\n````py\n```\n# コード\n````\n\n> 引用。"
    blocks = paragraphs(text)
    assert len(blocks) == 2
    assert blocks[0]["line"] == 6 and blocks[0]["end_line"] == 7
    assert blocks[1]["kind"] == "quote"


def test_order_sensitive_map_not_average_score():
    a = reading_map("短い。\n\n" + "長い文を続けて書く" * 4 + "。")
    b = reading_map("長い文を続けて書く" * 4 + "。\n\n短い。")
    assert a["transitions"][0]["mean_sentence_length_delta"] == -b["transitions"][0]["mean_sentence_length_delta"]
    assert a["quality_score"] is None


def test_delayed_optional_and_open_voice_are_not_failures(tmp_path):
    value = review()
    result = reading_map(TEXT, review=value)
    assert not any(f["code"] == "missing_prerequisite" for f in result["findings"])
    f = value["frictions"][0]
    f.update(kind="voice", resolution="open", payoff=None, decision="keep")
    result = reading_map(TEXT, review=value)
    assert not result["findings"]
    write_map(tmp_path, result)
    assert (tmp_path / "reading-map.md").exists()


def test_core_missing_information_is_distinct():
    value = review()
    value["frictions"][0].update(necessity="core", resolution="open", payoff=None)
    assert any(f["code"] == "missing_prerequisite" for f in reading_map(TEXT, review=value)["findings"])
    value["frictions"][0].update(resolution="later", payoff={"paragraph": 2, "quote": "勝者が片付ける約束"}, required_at=1)
    assert any(f["code"] == "missing_prerequisite" for f in reading_map(TEXT, review=value)["findings"])


@pytest.mark.parametrize("change", ["hash", "quote", "paragraph", "confidence", "payoff", "kind"])
def test_invalid_review_rejected(change):
    value = review()
    if change == "hash":
        value["text_hash"] = "stale"
    elif change == "quote":
        value["frictions"][0]["anchor"]["quote"] = "不存在"
    elif change == "paragraph":
        value["frictions"][0]["anchor"]["paragraph"] = 99
    elif change == "confidence":
        value["frictions"][0]["confidence"] = float("nan")
    elif change == "payoff":
        value["frictions"][0]["payoff"] = {"paragraph": 1, "quote": "彼は勝った"}
    else:
        value["frictions"][0]["kind"] = "magic"
    with pytest.raises(ValueError):
        reading_map(TEXT, review=value)


def test_genre_does_not_force_hooks_or_ban_parallel_steps(tmp_path):
    text = "まず、蓋を開ける。\n\n次に、水を入れる。\n\n最後に、蓋を閉める。"
    assert any(f["code"] == "parallel_openings" for f in reading_map(text, "essay")["findings"])
    assert not any(f["code"] == "parallel_openings" for f in reading_map(text, "guide")["findings"])
    result = write_brief(tmp_path, "手順", "初めて使う人", "操作できる", "guide")
    assert "productive_friction" not in [p["id"] for p in result["principles"]]
    assert len(knowledge()["sources"]) == 5


def test_policy_and_no_body(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text('{"uniform_cv": NaN}')
    with pytest.raises(ValueError):
        load_policy(path)
    with pytest.raises(ValueError):
        reading_map("# 題だけ")
