import pytest
from jlangbase.analysis import Analyzer
from jlangbase.trends import classify, DEFAULT_THRESHOLDS, time_diff
from jlangbase import db


@pytest.mark.parametrize("before,after,ratio,expected", [(0, 4, None, "emerging"), (4, 8, 2, "rising"), (8, 4, .5, "declining"), (4, 4, 1, "stable"), (1, 2, 2, "sparse"), (4, 0, 0, "declining"), (1, 9, 9, "sparse")])
def test_states(before, after, ratio, expected):
    row = dict(before_count=before, after_count=after, before_documents_count=min(before, 2), after_documents_count=min(after, 2), ratio=ratio)
    assert classify(row, DEFAULT_THRESHOLDS) == expected


def test_period_boundaries_and_fallback():
    docs = [dict(id=i, text=str(i), text_hash=db.text_hash(str(i)), collected_at=date) for i, date in enumerate(["2026-08-02", "2026-09-01", "2026-10-01"])]
    result = time_diff(docs, "test", "2026-09-01", "2026-10-01", Analyzer("basic"))
    assert result["before_document_count"] == result["after_document_count"] == 1
    assert result["windows"]["before"][0].startswith("2026-08-02")
    with pytest.raises(ValueError, match="前"):
        time_diff(docs, "test", "2026-10-01", "2026-09-01", Analyzer("basic"))
