"""Installed host routing and preservation of personal records."""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace
import subprocess
import sys

import pytest

from jlangbase.distribution import install, package_files


def invoke(home, *args):
    return subprocess.run(
        [sys.executable, str(home / ".local/share/jlangbase/run.py"), *map(str, args)],
        capture_output=True, text=True, check=False,
    )


def test_host_routes_and_shared_rules_survive_update(tmp_path):
    home = tmp_path / "home with spaces"
    install(home, "codex,claude,ollama")
    for host, folder in (("codex", ".agents"), ("claude", ".claude")):
        root = home / folder / "skills/japanese-discovery-writing"
        skill = (root / "SKILL.md").read_text()
        assert f"--host {host}" in skill
        assert "__HOST" not in skill and "__RULES__" not in skill
        assert str(home / ".agents/references/jlangbase-agent-writing.md") in skill
        assert "writing-start" in (root / "INSTALLATION.md").read_text()
    memory = home / ".agents/memory/jlangbase"
    record = memory / "agent-writing-memory.md"
    record.write_text("利用者の追記を保持する。", encoding="utf-8")
    install(home, "codex", update=True)
    assert record.read_text(encoding="utf-8") == "利用者の追記を保持する。"
    assert (memory / "INDEX.md").read_text().count("agent-writing-memory.md") == 1
    assert (home / ".agents/references/jlangbase-agent-writing.md").is_file()
    result = invoke(home, "context")
    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)
    assert (Path(context["resources"]) / "agent-writing.md").is_file()


def test_existing_shared_rule_conflict_has_no_partial_install(tmp_path):
    home = tmp_path / "home"
    rules = home / ".agents/references/jlangbase-agent-writing.md"
    rules.parent.mkdir(parents=True)
    rules.write_text("利用者独自のルール", encoding="utf-8")
    with pytest.raises(ValueError, match="競合"):
        install(home, "codex,claude")
    assert rules.read_text(encoding="utf-8") == "利用者独自のルール"
    assert not (home / ".local/share/jlangbase/run.py").exists()


def test_installed_launcher_accepts_only_reviewed_final_manuscript(tmp_path):
    home = tmp_path / "home"
    install(home, "codex,claude,ollama")
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({
        "request": "机の片付けについて書いて", "title": "机の片付け",
        "audience": "一般", "purpose": "方法を提案する", "style": "です・ます",
        "sources": [], "constraints": ["架空の経験を書かない"],
    }, ensure_ascii=False), encoding="utf-8")
    session = tmp_path / "session"
    result = invoke(home, "writing-start", brief, "--session", session, "--host", "codex")
    assert result.returncode == 0, result.stderr
    output = tmp_path / "final.md"
    assert invoke(home, "writing-handoff", session, "--out", output).returncode != 0
    assert not output.exists()
    for step in range(4):
        request_file = tmp_path / f"request-{step}.json"
        result = invoke(home, "writing-task", session, "--out", request_file)
        assert result.returncode == 0, result.stderr
        request = json.loads(request_file.read_text(encoding="utf-8"))
        response = {"request_id": request["request_id"]}
        if request["role"] == "reviewer":
            response["reviews"] = {
                key: {"decision": "pass", "quote": "机の上の紙を一枚片付けてみませんか。",
                      "reason": "資料なしの提案として依頼に答えている。", "condition": "提案の文体を保つ。"}
                for key in ("title", "facts", "reader", "style", "structure")
            }
            actor = "codex-reviewer"
        else:
            response.update(manuscript="机の上の紙を一枚片付けてみませんか。", discoveries=[])
            actor = "codex-writer"
        response_file = tmp_path / f"response-{step}.json"
        response_file.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
        result = invoke(home, "writing-submit", session, response_file, "--agent-id", actor)
        assert result.returncode == 0, result.stderr
    result = invoke(home, "writing-handoff", session, "--out", output)
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8").startswith("# 机の片付け\n")
    before = output.read_bytes()
    assert invoke(home, "writing-handoff", session, "--out", output).returncode != 0
    assert output.read_bytes() == before


@pytest.mark.parametrize("path_type", [PurePosixPath, PureWindowsPath])
def test_package_resource_keys_are_portable(path_type):
    relative = path_type("resources", "writing-workflow.md")
    resource = SimpleNamespace(
        relative_to=lambda source: relative, read_bytes=lambda: b"shared workflow",
        is_file=lambda: True, suffix=".md", parts=relative.parts,
    )
    source = SimpleNamespace(rglob=lambda pattern: [resource])
    assert package_files(source) == {"resources/writing-workflow.md": b"shared workflow"}
