"""Exercise GitHub ZIP entrypoints; only the network download is replaced."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
OLD_RELEASE = "227c024"


@pytest.fixture
def archive(tmp_path):
    archive_path = tmp_path / "current.zip"
    paths = [ROOT / "install.py", *(ROOT / "src/jlangbase").rglob("*")]
    with zipfile.ZipFile(archive_path, "w") as output:
        for path in paths:
            if path.is_file() and "__pycache__" not in path.parts:
                output.write(path, "bunmyaku-main/" + path.relative_to(ROOT).as_posix())
        output.writestr("bunmyaku-main/unneeded.txt", "not needed for installation")
    return archive_path


def run_entrypoint(tmp_path, archive, home, update=False):
    env = dict(os.environ, BUNMYAKU_TEST_ZIP=str(archive), PYTHONUTF8="1")
    # pytest may be invoked directly from a venv without activating its PATH.
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    if os.name == "nt":
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        assert powershell, "PowerShell is required on Windows"
        env["BUNMYAKU_TEST_INSTALLER"] = str(ROOT / "install.ps1")
        env["BUNMYAKU_TEST_HOME"] = str(home)
        script = (
            "function Invoke-WebRequest { param([switch]$UseBasicParsing, $Uri, $OutFile, $TimeoutSec) "
            "Copy-Item -LiteralPath $env:BUNMYAKU_TEST_ZIP -Destination $OutFile }; "
            "try { & $env:BUNMYAKU_TEST_INSTALLER -Tools 'codex,claude,ollama' "
            "-InstallHome $env:BUNMYAKU_TEST_HOME " + ("-Update" if update else "") +
            " } catch { [Console]::Error.WriteLine($_); exit 1 }"
        )
        command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
    else:
        bin_dir = tmp_path / "network-stub"
        bin_dir.mkdir(exist_ok=True)
        curl = bin_dir / "curl"
        curl.write_text(
            '#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n'
            '  if [ "$1" = "--output" ]; then cp "$BUNMYAKU_TEST_ZIP" "$2"; exit; fi\n'
            '  shift\ndone\nexit 2\n', encoding="utf-8",
        )
        curl.chmod(0o755)
        env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
        command = ["sh", str(ROOT / "install.sh"), "--tools", "codex,claude,ollama", "--home", str(home)]
        if update:
            command.append("--update")
    return subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90)


def invoke(home, *args):
    result = subprocess.run(
        [sys.executable, str(home / ".local/share/jlangbase/run.py"), *map(str, args)],
        env=dict(os.environ, PYTHONUTF8="1"), capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def assert_agent_installation(home, tmp_path):
    context = json.loads(invoke(home, "context").stdout)
    assert (Path(context["resources"]) / "agent-writing.md").is_file()
    for host, folder in (("codex", ".agents"), ("claude", ".claude")):
        skill = (home / folder / "skills/japanese-discovery-writing/SKILL.md").read_text(encoding="utf-8")
        assert f"--host {host}" in skill
        assert "__HOST" not in skill
    memory = home / ".agents/memory/jlangbase"
    assert "agent-writing-memory.md" in (memory / "INDEX.md").read_text(encoding="utf-8")
    assert (memory / "agent-writing-memory.md").is_file()
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({
        "request": "机の片付けについて書いて", "title": "机の片付け", "audience": "一般",
        "purpose": "方法を提案する", "style": "です・ます", "sources": [], "constraints": [],
    }, ensure_ascii=False), encoding="utf-8")
    for host in ("codex", "claude", "ollama"):
        session = tmp_path / f"session-{host}"
        invoke(home, "writing-start", brief, "--session", session, "--host", host)
        request = tmp_path / f"request-{host}.json"
        invoke(home, "writing-task", session, "--out", request)
        assert json.loads(request.read_text(encoding="utf-8"))["host"] == host


def test_github_zip_fresh_install_and_explicit_update(tmp_path, archive):
    home = tmp_path / "new home 日本語"
    result = run_entrypoint(tmp_path, archive, home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert_agent_installation(home, tmp_path)
    manifest = home / ".local/share/jlangbase/installation.json"
    before = manifest.read_bytes()
    result = run_entrypoint(tmp_path, archive, home)
    assert result.returncode != 0
    assert "--update" in result.stdout + result.stderr
    assert manifest.read_bytes() == before
    result = run_entrypoint(tmp_path, archive, home, update=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_github_zip_updates_pre_agent_release_and_preserves_records(tmp_path, archive):
    old_zip = tmp_path / "old.zip"
    subprocess.run([
        "git", "archive", "--format=zip", "--output", str(old_zip), OLD_RELEASE,
        "install.py", "src/jlangbase",
    ], cwd=ROOT, check=True, capture_output=True)
    source = tmp_path / "old source"
    with zipfile.ZipFile(old_zip) as archive_file:
        archive_file.extractall(source)
    if os.name == "nt":
        # The historical release could not install on Windows because resource
        # keys used backslashes. Normalize only that fixture's keys to prepare
        # its pre-agent state; the current installer is exercised unmodified.
        old_distribution = source / "src/jlangbase/distribution.py"
        old_code = old_distribution.read_text(encoding="utf-8")
        assert old_code.count("str(p.relative_to(source))") == 1
        old_distribution.write_text(
            old_code.replace("str(p.relative_to(source))", "p.relative_to(source).as_posix()"),
            encoding="utf-8",
        )
    home = tmp_path / "existing home 日本語"
    result = subprocess.run([
        sys.executable, str(source / "install.py"), "--home", str(home), "--tools", "codex,claude,ollama",
    ], env=dict(os.environ, PYTHONUTF8="1"), capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    memory = home / ".agents/memory/jlangbase"
    preserved = {
        memory / "writing-memory.md": "利用者が追記した執筆メモ。\n",
        memory / "sessions/personal.md": "公開しない原稿。\n",
        memory / "corrections/personal.json": '{"reason":"個人の訂正"}\n',
    }
    for path, content in preserved.items():
        path.write_text(content, encoding="utf-8")
    old_manifest = (home / ".local/share/jlangbase/installation.json").read_bytes()
    result = run_entrypoint(tmp_path, archive, home, update=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert_agent_installation(home, tmp_path)
    for path, content in preserved.items():
        assert path.read_text(encoding="utf-8") == content
    history = home / ".local/share/jlangbase/history"
    assert any(path.read_bytes() == old_manifest for path in history.glob("*.json"))
