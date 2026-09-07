import pytest
from jlangbase import db


def doc(text="本文"):
    return dict(text=text, collected_at=db.now(), source_type="magazine")


def test_dedup_and_roundtrip(tmp_path):
    path = tmp_path / "日本語" / "db.sqlite3"
    with db.connect(path) as conn:
        assert db.insert_document(conn, doc())
        assert not db.insert_document(conn, doc())
        assert db.documents(conn)[0]["text"] == "本文"
        assert len(db.hashes(conn)) == 1
    with db.connect(path) as conn:
        assert len(db.documents(conn, "magazine")) == 1
        assert db.documents(conn, "social") == []


def test_failed_transaction_does_not_break_next_insert():
    with db.connect(":memory:") as conn:
        with pytest.raises(Exception):
            db.insert_document(conn, {"text": "不完全"})
        assert db.insert_document(conn, doc("正常"))
        assert len(db.documents(conn)) == 1


def test_future_schema_rejected():
    with db.connect(":memory:") as conn:
        conn.execute("PRAGMA user_version = 99")
        with pytest.raises(ValueError, match="バージョン"):
            db.migrate(conn)
