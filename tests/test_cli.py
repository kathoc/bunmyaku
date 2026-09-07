import json
import os
from pathlib import Path
import subprocess
import sys
from jlangbase.cli import main


def test_full_cli_and_reingestion(tmp_path):
    data = tmp_path / "入力"
    data.mkdir()
    (data / "文.txt").write_text("今日は晴れた。\n\n駅まで歩こう。", encoding="utf-8")
    database, out = tmp_path / "db.sqlite3", tmp_path / "出力"
    args = ["analyze", str(data), "--db", str(database), "--profile", "magazine", "--backend", "basic", "--out", str(out)]
    assert main(args) == 0
    first = json.loads((out / "profile.json").read_text())
    assert main(args) == 0
    second = json.loads((out / "profile.json").read_text())
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second
    assert main(["build-profile", "--db", str(database), "--out", str(out / "compact.json"), "--compact"]) == 0
    assert (out / "report.md").exists()


def test_dry_run_has_no_db_side_effect(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("本文", encoding="utf-8")
    target = tmp_path / "new" / "db.sqlite3"
    assert main(["ingest", str(src), "--db", str(target), "--dry-run"]) == 0
    assert not target.parent.exists()


def test_errors_are_readable(tmp_path, capsys):
    assert main(["analyze", "--db", str(tmp_path / "empty.db"), "--backend", "basic"]) == 2
    assert "解析対象" in capsys.readouterr().err
    assert main(["analyze", "--top", "0"]) == 2


def test_module_entry_in_separate_process(tmp_path):
    package = Path(__file__).resolve().parents[1] / "src"
    env = dict(os.environ, PYTHONPATH=str(package))
    result = subprocess.run([sys.executable, "-m", "jlangbase", "--help"], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 0 and "compare-human-llm" in result.stdout
