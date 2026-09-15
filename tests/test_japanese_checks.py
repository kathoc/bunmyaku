from pathlib import Path
import os
import subprocess
import sys

import pytest

from jlangbase import japanese_checks as checks


def _completed(command, code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([str(part) for part in command], code, stdout, stderr)


def test_prepare_retries_after_failed_install(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JLANGBASE_CHECKS_CACHE", str(tmp_path / "cache"))
    calls = []
    state = {"ready": False, "installs": 0}

    def fake_run(command, *, timeout):
        calls.append((list(command), timeout))
        if "-c" in command:
            return _completed(command, 0 if state["ready"] else 1)
        if command[2:4] == ["pip", "install"]:
            state["installs"] += 1
            if state["installs"] == 1:
                return _completed(command, 1, stderr="network unavailable")
            state["ready"] = True
        if command[2:4] == ["venv", "--upgrade"]:
            created_python = checks._venv_python(Path(command[-1]))
            created_python.parent.mkdir(parents=True, exist_ok=True)
            created_python.touch()
        return _completed(command)

    monkeypatch.setattr(checks, "_run", fake_run)
    with pytest.raises(ValueError, match="network unavailable"):
        checks._prepare_runtime()
    assert not state["ready"]
    checks._prepare_runtime()
    assert state["installs"] == 2
    assert "導入しています" in capsys.readouterr().err
    assert any("venv" in call[0] for call in calls)


def test_run_check_preserves_arguments_and_exit_code(monkeypatch, tmp_path, capsys):
    script = tmp_path / "lint.py"
    script.touch()
    monkeypatch.setattr(checks, "_script_path", lambda name: script)
    runtime = tmp_path / "python"
    monkeypatch.setattr(checks, "_prepare_runtime", lambda: runtime)
    seen = []

    def fake_run(command, *, timeout):
        seen.append(list(command))
        return _completed(command, 7, "standard output\n", "standard error\n")

    monkeypatch.setattr(checks, "_run", fake_run)
    assert checks.run_check("lint", [Path("draft.md"), "--genre", "essay"]) == 7
    assert seen == [[runtime, script, "draft.md", "--genre", "essay"]]
    captured = capsys.readouterr()
    assert captured.out == "standard output\n"
    assert captured.err == "standard error\n"


def test_help_does_not_prepare_dependencies(monkeypatch, tmp_path):
    script = tmp_path / "outline.py"
    script.touch()
    monkeypatch.setattr(checks, "_script_path", lambda name: script)
    monkeypatch.setattr(checks, "_prepare_runtime", lambda: pytest.fail("prepare must not run"))
    seen = []
    monkeypatch.setattr(checks, "_run", lambda command, *, timeout: (seen.append(list(command)) or _completed(command)))
    assert checks.run_check("outline", ["--help"]) == 0
    assert seen[0][0] == checks.sys.executable


def test_semantic_uses_its_separate_optional_runtime(monkeypatch, tmp_path):
    script = tmp_path / "semantic.py"
    script.touch()
    monkeypatch.setattr(checks, "_script_path", lambda name: script)
    monkeypatch.setattr(checks, "_prepare_runtime", lambda: pytest.fail("normal runtime must not run"))
    runtime = tmp_path / "semantic-python"
    monkeypatch.setattr(checks, "_prepare_semantic_runtime", lambda: runtime)
    seen = []
    monkeypatch.setattr(checks, "_run", lambda command, *, timeout: (seen.append(list(command)) or _completed(command)))
    assert checks.run_check("semantic", ["article.md"]) == 0
    assert seen == [[runtime, script, "article.md"]]


def test_analyze_text_parses_each_normal_check(monkeypatch, tmp_path):
    script = tmp_path / "script.py"
    script.touch()
    monkeypatch.setattr(checks, "_script_path", lambda name: script)
    monkeypatch.setattr(checks, "_prepare_runtime", lambda: tmp_path / "python")
    names = iter(("lint", "outline", "terms"))

    def fake_run(command, *, timeout):
        name = next(names)
        source = Path(command[2])
        assert source.read_text(encoding="utf-8") == "本文"
        assert command[-1] == "--json"
        return _completed(command, stdout='{"check": "' + name + '"}')

    monkeypatch.setattr(checks, "_run", fake_run)
    assert checks.analyze_text("本文") == {
        "lint": {"check": "lint"},
        "outline": {"check": "outline"},
        "terms": {"check": "terms"},
    }


def test_analyze_text_raises_for_script_failure(monkeypatch, tmp_path):
    script = tmp_path / "script.py"
    script.touch()
    monkeypatch.setattr(checks, "_script_path", lambda name: script)
    monkeypatch.setattr(checks, "_prepare_runtime", lambda: tmp_path / "python")
    monkeypatch.setattr(checks, "_run", lambda command, *, timeout: _completed(command, 1, stderr="bad input"))
    with pytest.raises(ValueError, match="bad input"):
        checks.analyze_text("本文")


def test_unknown_check_has_readable_error():
    with pytest.raises(ValueError, match="未知の日本語点検"):
        checks.run_check("unknown", [])


def test_readiness_probe_requires_the_pinned_versions(monkeypatch, tmp_path):
    python = tmp_path / "python"
    python.touch()
    seen = []
    monkeypatch.setattr(
        checks,
        "_run",
        lambda command, *, timeout: (seen.append(list(command)) or _completed(command)),
    )
    assert checks._is_ready(python)
    assert "version('SudachiPy') == '0.6.11'" in seen[0][-1]
    assert "version('SudachiDict-core') == '20260723'" in seen[0][-1]


def test_broken_partial_venv_is_not_ready(monkeypatch, tmp_path):
    python = tmp_path / "python"
    python.touch()
    monkeypatch.setattr(checks, "_run", lambda command, *, timeout: (_ for _ in ()).throw(ValueError("broken")))
    assert not checks._is_ready(python)


def test_module_can_be_imported_by_another_python_process():
    source_root = str(Path(__file__).parents[1] / "src")
    environment = os.environ | {"PYTHONPATH": source_root}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from jlangbase.japanese_checks import analyze_text, run_check; print(analyze_text.__name__, run_check.__name__)",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "analyze_text run_check"
