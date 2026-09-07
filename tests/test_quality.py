import json
import pytest
from jlangbase import db
from jlangbase.analysis import Analyzer, split_sentences
from jlangbase.ingest import read_corpus
from jlangbase.profiles import run_analysis


def test_ascii_ellipsis_not_three_sentences():
    assert split_sentences("考える...まだ答えはない。") == ["考える...まだ答えはない。"]


def test_falsey_invalid_metadata_is_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"text": "本文", "source_type": []}), encoding="utf-8")
    docs, stats = read_corpus(path)
    assert docs == [] and stats["failed"] == 1


def test_auto_fallback_when_dependency_missing(monkeypatch):
    import builtins
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "sudachipy":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    assert Analyzer("auto").info["name"] == "basic"
    with pytest.raises(ValueError, match="インストール"):
        Analyzer("sudachi")


def test_morphological_persistence_and_run_rollback():
    pytest.importorskip("sudachipy")
    pytest.importorskip("sudachidict_core")
    with db.connect(":memory:") as conn:
        db.insert_document(conn, dict(text="しかし、猫は走る。猫は歩く。", collected_at="2026-09-06", source_type="test"))
        _, result = run_analysis(conn, "test", "sudachi")
        assert result["expressions"]
        # Storage access remains encapsulated in db; result round-trip verifies snapshots.
        assert db.latest_run(conn, "test")["result"]["token_count"] == result["token_count"]
        invalid = [{"document": {"id": 999999, "text_hash": "invalid"}, "metrics": {}, "sentences": []}]
        with pytest.raises(Exception):
            db.save_run(conn, "test", {}, invalid, {})
        assert db.latest_run(conn, "test")["result"]["token_count"] == result["token_count"]
