import json
import pytest
from jlangbase.experiments import record_experiment


def test_append_only_snapshots_and_evidence(tmp_path):
    (tmp_path / "reference.txt").write_text("あ。\n\nい。", encoding="utf-8")
    (tmp_path / "v1.md").write_text("# 題\n\nあ。\n\nい。", encoding="utf-8")
    manifest = dict(title="題", reference="reference.txt", author_type="llm", created_at="2026-09-06",
                    versions=[dict(id="v1", path="v1.md", intent="初稿", annotations=[dict(aspect="冒頭", observation="短文", evidence="あ。", confidence=.9)])])
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    a = record_experiment(tmp_path, "basic")
    b = record_experiment(tmp_path, "basic")
    assert a != b
    assert (a / "trajectory.md").exists() and (b / "v1" / "text.md").exists()
    assert json.loads((b / "trajectory.json").read_text())["versions"][0]["structure_metrics"]["paragraph_count"] == 2
    manifest["versions"][0]["annotations"][0]["evidence"] = "本文にない"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="根拠"):
        record_experiment(tmp_path, "basic")
