import json
import pytest
from jlangbase.evaluation import evaluate, evaluate_versions, load_weights, tv_distance
from jlangbase.structure import structure_metrics
from test_comparison import corpus


def test_structure_and_headings():
    result = structure_metrics("# 題\n\n一文。二文。\n\n### 小見出し\n\n短文。\n\n- 一\n- 二")
    assert result["paragraph_count"] == 3
    assert result["heading_count"] == 2 and result["heading_level_jumps"] == 1
    assert result["sentences_per_paragraph"] == [2, 1, 2]
    assert result["list_item_count"] == 2
    assert structure_metrics("```python\n# not heading\n\nx = 1\n```\n\n本文。")["paragraph_count"] == 1


def test_identical_zero_and_bounded_distances():
    ref = corpus("短い文。\n\n次の文。")
    changed = corpus("あ" * 150 + "。")
    assert evaluate(ref, ref)["distance"] == 0
    report = evaluate_versions(ref, changed, ref)
    assert report["distance_reduction"] > 0
    assert all(v is None or 0 <= v <= 1 for v in report["before"]["metrics"].values())
    assert report["after"]["missing_metrics"]["ngrams"]
    assert tv_distance({}, {}) == 0 and tv_distance({}, {"a": 1}) == 1


@pytest.mark.parametrize("value", [{"sentence_length": -1}, {"wrong": 1}, {"sentence_length": float("nan")}, []])
def test_invalid_weights(tmp_path, value):
    path = tmp_path / "weights.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        load_weights(path)
