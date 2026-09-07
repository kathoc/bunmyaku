"""Exercise installed CLI commands in an isolated directory, without pytest."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["basic", "sudachi"], default="basic")
    backend = parser.parse_args().backend
    with TemporaryDirectory(prefix="jlangbase-smoke-") as directory:
        root = Path(directory)
        source = root / "日本語.jsonl"
        docs = [dict(text=text, source_type="social", author_type="llm", published_at=date)
                for text, date in [
                    ("猫は歩く。猫は歩く。朝。", "2026-08-15"),
                    ("猫は歩く。猫は歩く。夜。", "2026-08-20"),
                    ("猫は走る。猫は走る。朝。", "2026-09-10"),
                    ("猫は走る。猫は走る。夜。", "2026-09-20")]]
        source.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in docs), encoding="utf-8")
        database = root / "corpus.sqlite3"
        calls = 0

        def run(*args):
            nonlocal calls
            result = subprocess.run([sys.executable, "-m", "jlangbase", "--db", str(database), *map(str, args)], cwd=root, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"{args}: {result.stderr}")
            calls += 1
            return result.stdout

        run("ingest", source, "--dry-run")
        assert not database.exists()
        run("ingest", source)
        assert json.loads(run("ingest", source))["added"] == 0
        run("analyze", "--source-type", "social", "--backend", backend, "--out", root / "analysis")
        run("build-profile", "--source-type", "social", "--compact", "--out", root / "compact.json")
        run("compare-human-llm", source, "--human-source", "social", "--backend", backend, "--out", root / "comparison")
        run("evaluate", "--reference", source, "--before", source, "--after", source, "--backend", backend, "--out", root / "evaluation")
        run("diff", "--source-type", "social", "--from", "2026-09-01", "--to", "2026-10-01", "--backend", backend, "--out", root / "diff")
        if backend == "sudachi":
            assert json.loads(run("expressions", "--source-type", "social", "--top", 2))
        profile = json.loads((root / "analysis/profile.json").read_text())
        evaluation = json.loads((root / "evaluation/evaluation.json").read_text())
        diff = json.loads((root / "diff/diff.json").read_text())
        comparison = json.loads((root / "comparison/comparison.json").read_text())
        assert profile["document_count"] == 4
        assert evaluation["before"]["distance"] == evaluation["after"]["distance"] == 0
        assert comparison["overrepresented_in_llm"] == comparison["underrepresented_in_llm"] == []
        assert diff["before_document_count"] == diff["after_document_count"] == 2
        if backend == "sudachi":
            assert any(row["status"] == "emerging" for row in diff["expressions"])
        else:
            assert profile["token_count"] is None and diff["expressions"] == []
        assert (root / "compact.json").stat().st_size < 8000
        assert (root / "analysis/report.md").exists()
        print(json.dumps(dict(backend=backend, commands_passed=calls, documents=4, identity_distance=0, status="PASS")))


if __name__ == "__main__":
    main()
