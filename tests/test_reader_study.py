import json
import pytest
from jlangbase.reader_study import prepare_study, summarize_study


def setup_study(tmp_path):
    a, b = tmp_path / "initial.md", tmp_path / "revised.md"
    a.write_text("# 題\n\n同じ題材の一つ目の文章。", encoding="utf-8")
    b.write_text("# 題\n\n同じ題材の二つ目の文章。", encoding="utf-8")
    out = prepare_study([a, b], tmp_path / "study")
    return a, b, out


def response(kind="human"):
    return {"packet": "packet-01", "reader_id": "reader-1", "reviewer_kind": kind, "preference": "A",
            "responses": [{"label": label, "curiosity": 3, "self_reported_understanding": 4, "felt_effort": 2,
                           "comprehension_answer": "test answer", "recall": "test recall", "friction_quote": "", "friction_effect": "", "reason": "test reason"} for label in "AB"]}


def test_blinded_balanced_and_immutable(tmp_path):
    a, b, out = setup_study(tmp_path)
    p1 = (out / "public/packet-01.md").read_text()
    p2 = (out / "public/packet-02.md").read_text()
    assert "initial.md" not in p1 and "revised.md" not in p1
    assert p1.index("## 本文 A") < p1.index("## 本文 B")
    assert p2.index("## 本文 B") < p2.index("## 本文 A")
    with pytest.raises(ValueError):
        prepare_study([a, b], out)


def test_empty_and_model_only_do_not_imply_human_improvement(tmp_path):
    _, _, out = setup_study(tmp_path)
    path = tmp_path / "responses.jsonl"
    path.write_text("")
    result = summarize_study(out, path)
    assert result["groups"]["human"]["status"] == "not_measured"
    assert result["groups"]["human"]["versions"]["A"]["mean"]["curiosity"] is None
    path.write_text(json.dumps(response("model")))
    result = summarize_study(out, path)
    assert result["groups"]["human"]["reader_count"] == 0
    assert result["groups"]["model"]["reader_count"] == 1
    assert result["quality_improved"] is None


def test_duplicate_and_incomplete_response_rejected(tmp_path):
    _, _, out = setup_study(tmp_path)
    path = tmp_path / "responses.jsonl"
    row = response()
    path.write_text(json.dumps(row) + "\n" + json.dumps(row))
    with pytest.raises(ValueError, match="重複"):
        summarize_study(out, path)
    row["responses"][0]["curiosity"] = None
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="整数"):
        summarize_study(out, path)


def test_opening_is_separate_and_optional_ratings_are_counted(tmp_path):
    _, _, out = setup_study(tmp_path)
    assert (out / 'public/packet-01-opening.md').exists()
    path = tmp_path / 'answers.jsonl'
    row = response()
    row['responses'][0]['opening_curiosity'] = 4
    row['responses'][0]['first_attention_quote'] = '題材'
    path.write_text(json.dumps(row))
    result = summarize_study(out, path)
    assert result['groups']['human']['versions']['A']['opening_curiosity'] == {'n': 1, 'mean': 4}
    assert result['groups']['human']['versions']['B']['opening_curiosity'] == {'n': 0, 'mean': None}
    assert result['groups']['human']['versions']['A']['observations'][0]['first_attention_quote'] == '題材'
