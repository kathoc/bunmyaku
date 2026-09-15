"""Bundled guidance and real analysis reach the reviewer without changing acceptance."""
import json
from pathlib import Path

import pytest

from jlangbase import agent_writing


def begin(tmp_path):
    session = tmp_path / "session"
    agent_writing.start({
        "request": "短い記事を書いて", "title": "試行", "audience": "一般読者",
        "purpose": "説明する", "style": "です・ます", "sources": [], "constraints": [],
    }, session, "codex")
    return session


def test_review_gets_analysis_of_exact_manuscript(tmp_path, monkeypatch):
    from jlangbase import japanese_checks
    calls = []
    result = {"lint": {"findings": [{"category": "sample"}]}, "outline": {}, "terms": {}}
    def analyze(text):
        calls.append(text)
        return result
    monkeypatch.setattr(japanese_checks, "analyze_text", analyze)
    session = begin(tmp_path)
    writing = agent_writing.task(session)
    assert "natural-japanese-workflow.md" in writing["rules"]
    assert not calls
    manuscript = "共有プリンターに資料を送りました。\n別の部屋で見つかりました。"
    agent_writing.submit(session, {"request_id": writing["request_id"],
                                  "manuscript": manuscript, "discoveries": []}, "writer")
    request = agent_writing.task(session)
    assert calls == [manuscript]
    assert request["natural_japanese_checks"] == result
    # Findings do not alter the existing review schema or automatically reject.
    reviews = {k: {"decision": "pass", "quote": "共有プリンターに資料を送りました。",
                   "reason": "指摘はこの文脈では保持する。", "condition": "主体と順序を保つ。"}
               for k in agent_writing.REVIEW_KEYS}
    agent_writing.submit(session, {"request_id": request["request_id"], "reviews": reviews}, "reviewer")
    assert json.loads((session / "state.json").read_text())["phase"] == "edit"


def test_check_failure_does_not_advance_session(tmp_path, monkeypatch):
    from jlangbase import japanese_checks
    session = begin(tmp_path)
    request = agent_writing.task(session)
    agent_writing.submit(session, {"request_id": request["request_id"],
                                  "manuscript": "本文です。", "discoveries": []}, "writer")
    before = (session / "state.json").read_bytes()
    def fail(text):
        raise ValueError("辞書の準備に失敗しました")
    monkeypatch.setattr(japanese_checks, "analyze_text", fail)
    with pytest.raises(ValueError, match="辞書"):
        agent_writing.task(session)
    assert (session / "state.json").read_bytes() == before


def test_context_resource_is_inside_installed_release(tmp_path, capsys):
    from jlangbase.bundle_cli import main
    assert main(["context"]) == 0
    context = json.loads(capsys.readouterr().out)
    root = Path(context["natural_japanese"])
    assert root.parent == Path(context["resources"])
    assert (root / "LICENSE.md").is_file()
    assert (root / "references/doctypes/memo.md").is_file()
