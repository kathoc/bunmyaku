import json
from jlangbase import db
from jlangbase.analysis import Analyzer
from jlangbase.profiles import analyze_corpus, build_profile, run_analysis
from jlangbase.report import write_profile


def test_weighted_aggregation_and_compact(tmp_path):
    docs = [dict(id=i, text=t, text_hash=db.text_hash(t), collected_at="2026-09-01", author_type="llm") for i, t in enumerate(["漢あ", "ア" * 8])]
    _, result = analyze_corpus(docs, "magazine", Analyzer("basic"))
    assert result["char_type_ratios"]["kanji"] == .1
    assert result["token_count"] is None
    profile = build_profile(result, compact=True)
    assert len(json.dumps(profile, ensure_ascii=False).encode()) < 8000
    write_profile(tmp_path, profile)
    assert json.loads((tmp_path / "profile.json").read_text())["schema_version"] == 1
    assert "未計測" in (tmp_path / "report.md").read_text()


def test_run_snapshots_do_not_double_aggregate():
    with db.connect(":memory:") as conn:
        db.insert_document(conn, dict(text="猫が走る。", source_type="magazine", collected_at="2026-09-01"))
        first, a = run_analysis(conn, "magazine", "basic")
        second, b = run_analysis(conn, "magazine", "basic")
        assert first != second and a == b
        assert db.latest_run(conn, "magazine")["result"] == json.loads(db.encode(b))
        db.save_profile(conn, second, build_profile(b))
