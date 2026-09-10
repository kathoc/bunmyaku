import pytest
import json

from jlangbase.agent_writing import handoff, start, submit, task


def brief():
    return {"request":"記事を書く", "title":"題名", "audience":"読者", "purpose":"目的",
            "style":"です・ます", "sources":[], "constraints":[]}


def review(request_id, quote="本文です。", decision="pass"):
    return {"request_id":request_id, "reviews": {k: {"decision":decision, "quote":quote,
             "reason":"確認", "condition":"維持"} for k in ("title", "facts", "reader", "style", "structure")}}


def test_draft_review_edit_complete_and_handoff(tmp_path):
    session = tmp_path / "session"
    assert start(brief(), session, "claude")["status"] == "active"
    request = task(session)
    submit(session, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "writer")
    request = task(session); submit(session, review(request["request_id"]), "reviewer")
    request = task(session)
    submit(session, {"request_id":request["request_id"], "manuscript":"編集本文です。", "discoveries":[]}, "writer2")
    request = task(session); result = submit(session, review(request["request_id"], "編集本文です。"), "reviewer2")
    assert result["status"] == "complete"
    output = tmp_path / "manuscript.md"
    handoff(session, output)
    assert "編集本文です。" in output.read_text()


def test_self_review_and_stale_request_rejected(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "codex")
    request = task(session)
    submit(session, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "same")
    request = task(session)
    with pytest.raises(ValueError): submit(session, review("old"), "same")


def test_missing_review_is_rejected(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "claude")
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "writer")
    request = task(session)
    with pytest.raises(ValueError): submit(session, {"request_id":request["request_id"], "reviews":{}}, "reviewer")


def test_revision_can_pass_then_second_failure_exhausts_budget(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "claude", max_revisions=1)
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"初稿です。", "discoveries":[]}, "writer")
    request = task(session); submit(session, review(request["request_id"], "初稿です。", "revise"), "reviewer")
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"修正版です。", "discoveries":[]}, "writer")
    request = task(session); result = submit(session, review(request["request_id"], "修正版です。", "pass"), "reviewer")
    assert result["phase"] == "edit"
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"再編集です。", "discoveries":[]}, "writer")
    request = task(session); result = submit(session, review(request["request_id"], "再編集です。", "revise"), "reviewer")
    assert result["status"] == "active"
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"再編集の修正です。", "discoveries":[]}, "writer")
    request = task(session); result = submit(session, review(request["request_id"], "再編集の修正です。", "revise"), "reviewer")
    assert result["status"] == "budget_exhausted"


def test_blocked_writer_is_saved(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "claude")
    request = task(session)
    result = submit(session, {"request_id":request["request_id"], "status":"blocked", "reason":"資料不足"}, "writer")
    assert result["status"] == "blocked"
    assert __import__("json").loads((session / "state.json").read_text())["reason"] == "資料不足"


def test_bad_review_is_rejected_without_state_change(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "claude")
    request = task(session); submit(session, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "writer")
    request = task(session); before = (session / "state.json").read_bytes()
    bad = review(request["request_id"], "架空の引用", "revise")
    with pytest.raises(ValueError): submit(session, bad, "reviewer")
    assert (session / "state.json").read_bytes() == before
    bad = review(request["request_id"], "本文です。", "revise")
    bad["reviews"]["title"]["reason"] = ""
    with pytest.raises(ValueError): submit(session, bad, "reviewer")
    assert (session / "state.json").read_bytes() == before


def test_cross_session_and_same_writer_review_are_rejected(tmp_path):
    first = tmp_path / "first"; second = tmp_path / "second"
    start(brief(), first, "claude"); start(brief(), second, "claude")
    request = task(first); submit(first, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "writer")
    with pytest.raises(ValueError): submit(second, {"request_id":request["request_id"], "manuscript":"本文です。", "discoveries":[]}, "writer")
    request = task(first)
    with pytest.raises(ValueError): submit(first, review(request["request_id"]), "writer")


def test_fake_ollama_four_calls_complete_and_guards(tmp_path, monkeypatch):
    import jlangbase.ollama_writer as ow
    import jlangbase.agent_writing as aw
    class Fake:
        def __init__(self, endpoint, model, timeout): self.model = model or "local"; self.endpoint = endpoint
        def chat(self, request, structured=False):
            if request["role"] in {"writer", "editor"}: return {"manuscript":"本文です。", "discoveries":[]}
            return {"reviews": {k: {"decision":"pass", "quote":"本文です。", "reason":"確認", "condition":"維持"} for k in ("title", "facts", "reader", "style", "structure")}}
    monkeypatch.setattr(ow, "Ollama", Fake)
    session = tmp_path / "session"; start(brief(), session, "ollama")
    assert aw.run_ollama(session, max_actions=4)["status"] == "complete"
    codex = tmp_path / "codex"; start(brief(), codex, "codex")
    with pytest.raises(ValueError): aw.run_ollama(codex, max_actions=1)


def test_ollama_limit_and_provider_failure_are_resumable(tmp_path, monkeypatch):
    import jlangbase.ollama_writer as ow
    import jlangbase.agent_writing as aw
    class Fake:
        def __init__(self, endpoint, model, timeout): self.model = model or "local"
        def chat(self, request, structured=False): return {"manuscript":"本文です。", "discoveries":[]}
    monkeypatch.setattr(ow, "Ollama", Fake)
    session = tmp_path / "session"; start(brief(), session, "ollama")
    assert aw.run_ollama(session, max_actions=1)["status"] == "active"
    with pytest.raises(ValueError): aw.run_ollama(session, model="different")
    with pytest.raises(ValueError): aw.run_ollama(session, endpoint="http://127.0.0.1:9999")
    session2 = tmp_path / "failure"; start(brief(), session2, "ollama")
    class Broken(Fake):
        def chat(self, request, structured=False): raise OSError("接続失敗")
    monkeypatch.setattr(ow, "Ollama", Broken)
    assert aw.run_ollama(session2)["status"] == "active"
    assert "接続失敗" in __import__("json").loads((session2 / "state.json").read_text())["last_error"]["message"]
    request_id = task(session2)["request_id"]
    monkeypatch.setattr(ow, "Ollama", Fake)
    assert aw.run_ollama(session2, max_actions=1)["phase"] == "review"
    state = __import__("json").loads((session2 / "state.json").read_text())
    assert "last_error" not in state
    assert state["history"][0]["response"]["request_id"] == request_id


@pytest.mark.parametrize("field,value", [
    ("request", ""), ("title", None), ("audience", []), ("purpose", 3),
    ("style", " "), ("sources", {}), ("constraints", "plain"),
    ("constraints", [False]),
    ("sources", [{"id": "a", "path": "x", "quote": "q"}] * 2),
])
def test_invalid_brief_does_not_create_session(tmp_path, field, value):
    candidate = brief(); candidate[field] = value
    with pytest.raises(ValueError): start(candidate, tmp_path / "session", "codex")
    assert not (tmp_path / "session/state.json").exists()


@pytest.mark.parametrize("limit", [-1, True, 1.5])
def test_invalid_revision_limit(tmp_path, limit):
    with pytest.raises(ValueError): start(brief(), tmp_path / "session", "codex", limit)


def test_empty_quote_can_report_missing_explanation(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "codex")
    submit(session, {"request_id": task(session)["request_id"], "manuscript": "本文です。", "discoveries": []}, "writer")
    result = submit(session, review(task(session)["request_id"], "", "revise"), "reviewer")
    assert result["phase"] == "draft"
    assert task(session)["feedback"]["reader"]["quote"] == ""


def test_request_schema_and_discovery_history_follow_edit(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "codex")
    draft = {"request_id": task(session)["request_id"], "manuscript": "本文です。",
             "discoveries": [{"quote": "本文", "observation": "気づき", "next_action": "残す"}]}
    submit(session, draft, "writer")
    submit(session, review(task(session)["request_id"]), "reviewer")
    request = task(session)
    assert request["role"] == "editor"
    assert "manuscript" in request["response_schema"]
    assert "editorial-workflow.md" in request["rules"]
    submit(session, {"request_id": request["request_id"], "manuscript": "本文です。", "discoveries": []}, "editor")
    assert task(session)["discovery_history"][0] == draft["discoveries"]


def test_session_lock_and_state_edit_are_rejected(tmp_path):
    session = tmp_path / "session"; start(brief(), session, "codex")
    response = {"request_id": task(session)["request_id"], "manuscript": "本文です。", "discoveries": []}
    (session / ".lockdir").mkdir()
    before = (session / "state.json").read_bytes()
    with pytest.raises(ValueError): submit(session, response, "writer")
    assert (session / "state.json").read_bytes() == before
    (session / ".lockdir").rmdir()
    state = json.loads(before); state["host"] = "ollama"
    (session / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError): task(session)


def test_cli_task_does_not_overwrite_and_blocked_exit_is_nonzero(tmp_path, capsys):
    from jlangbase.bundle_cli import main
    session = tmp_path / "session"; start(brief(), session, "codex")
    output = tmp_path / "request.json"
    assert main(["writing-task", str(session), "--out", str(output)]) == 0
    original = output.read_bytes()
    assert main(["writing-task", str(session), "--out", str(output)]) == 2
    assert output.read_bytes() == original
    response = tmp_path / "response.json"
    response.write_text(json.dumps({"request_id": task(session)["request_id"], "status": "blocked", "reason": "資料不足"}))
    assert main(["writing-submit", str(session), str(response), "--agent-id", "writer"]) == 1


def test_ollama_adapter_sends_schema_and_preserves_legacy_format():
    from jlangbase.ollama_writer import Ollama
    from jlangbase.agent_writing import _output_schema
    backend = object.__new__(Ollama)
    backend.model = "local"
    payloads = []
    def capture(path, payload):
        payloads.append(payload)
        return {"message": {"content": "{}"}}
    backend.request = capture
    schema = _output_schema("reviewer")
    backend.chat({"output_schema": schema}, structured=True)
    backend.chat({"task": "legacy"}, structured=True)
    assert payloads[0]["format"] == schema
    assert set(schema["anyOf"][0]["properties"]["reviews"]["required"]) == {"title", "facts", "reader", "style", "structure"}
    assert payloads[1]["format"] == "json"


def test_failed_ollama_response_is_recorded(tmp_path, monkeypatch):
    import jlangbase.ollama_writer as ow
    from jlangbase.agent_writing import run_ollama
    class Invalid:
        def __init__(self, *args): self.model = "local"
        def chat(self, request, structured=False): return {"unexpected": "bad result"}
    monkeypatch.setattr(ow, "Ollama", Invalid)
    session = tmp_path / "session"; start(brief(), session, "ollama")
    assert run_ollama(session)["status"] == "active"
    state = json.loads((session / "state.json").read_text())
    assert state["last_error"]["response"]["unexpected"] == "bad result"
    assert not state["history"]
    assert task(session)["previous_error"] == state["last_error"]["message"]


def test_ollama_context_capacity_is_sent_and_truncation_is_rejected():
    from jlangbase.ollama_writer import Ollama
    backend = object.__new__(Ollama); backend.model = "local"
    payloads = []
    def capture(path, payload):
        payloads.append(payload)
        return {"message": {"content": "{}"}, "prompt_eval_count": 4096, "eval_count": 2}
    backend.request = capture
    with pytest.raises(ValueError, match="文脈容量"):
        backend.chat({"context_length": 4096}, structured=True)
    assert backend.chat({"context_length": 16384}, structured=True) == {}
    assert payloads[1]["options"]["num_ctx"] == 16384
    assert backend.last_usage["prompt_eval_count"] == 4096


def test_ollama_context_cannot_change_during_resume(tmp_path, monkeypatch):
    import jlangbase.ollama_writer as ow
    from jlangbase.agent_writing import run_ollama
    class Fake:
        def __init__(self, *args): self.model = "local"
        def chat(self, request, structured=False):
            assert request["context_length"] == 8192
            return {"manuscript": "本文です。", "discoveries": []}
    monkeypatch.setattr(ow, "Ollama", Fake)
    session = tmp_path / "session"; start(brief(), session, "ollama")
    run_ollama(session, max_actions=1, context_length=8192)
    with pytest.raises(ValueError): run_ollama(session, context_length=16384)
