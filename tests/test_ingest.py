import json
from jlangbase import db
from jlangbase.ingest import ingest, read_corpus


def test_bom_duplicate_empty_and_bad_lines(tmp_path):
    (tmp_path / "文章.txt").write_text("\ufeff雨が降る。", encoding="utf-8")
    (tmp_path / "同文.md").write_text("雨が降る。", encoding="utf-8")
    (tmp_path / "empty.txt").write_text("  ", encoding="utf-8")
    (tmp_path / "more.jsonl").write_text('\n{bad}\n' + json.dumps({"text": "晴れた。", "custom": 1}) + '\n{"text": 42}\n', encoding="utf-8")
    (tmp_path / "bad.txt").write_bytes(b"\xff")
    with db.connect(":memory:") as conn:
        dry = ingest(conn, tmp_path, dry_run=True)
        assert dry["added"] == 2 and dry["duplicates"] == 1 and dry["failed"] == 3
        assert not db.documents(conn)
        stats = ingest(conn, tmp_path)
        assert stats == dry
        again = ingest(conn, tmp_path)
        assert again["added"] == 0 and again["duplicates"] == 3
        assert any(d["metadata"].get("custom") == 1 for d in db.documents(conn))


def test_metadata_validation_and_date(tmp_path):
    path = tmp_path / "input.jsonl"
    records = [{"text": "一", "published_at": "2026-09-01T09:00:00+09:00"},
               {"text": "二", "published_at": "bad"}, {"text": "三", "source_type": []},
               {"text": "四", "edited": "yes"}, ["invalid"]]
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    docs, stats = read_corpus(path)
    assert stats["failed"] == 4
    assert docs[0]["published_at"] == "2026-09-01T00:00:00+00:00"
