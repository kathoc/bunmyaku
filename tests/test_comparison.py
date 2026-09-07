from copy import deepcopy
import json
from jlangbase.analysis import Analyzer
from jlangbase.profiles import analyze_corpus
from jlangbase.comparison import compare, contrast_rows, write_comparison
from jlangbase import db


def corpus(text):
    doc = dict(id=1, text=text, text_hash=db.text_hash(text), collected_at="2026-09-01")
    return analyze_corpus([doc], "test", Analyzer("basic"))[1]


def test_zero_baseline_and_coverage(tmp_path):
    a = corpus("あ。")
    a["analyzer"] = dict(morphology_available=True, name="test")
    b = deepcopy(a)
    b["expressions"] = [dict(kind="ngram", expression="猫", token_length=1, count=2, documents_count=1, per_10k_tokens=5000)]
    row = contrast_rows(a, b)[0]
    assert row["ratio"] is None and row["coverage_diff"] == 1
    result = compare(a, b)
    assert result["overrepresented_in_llm"][0]["absolute_diff"] == 5000
    assert not result["underrepresented_in_llm"]
    write_comparison(tmp_path, result)
    assert json.loads((tmp_path / "comparison.json").read_text())["schema_version"] == 1


def test_basic_comparison_reports_unavailable():
    result = compare(corpus("あ。"), corpus("あいうえお。"))
    assert result["metric_differences"]["mean_sentence_length"] == 4
    assert result["overrepresented_in_llm"] == []
    assert "利用不能" in result["notes"][-1]
