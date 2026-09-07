"""Append-only experiment snapshots, including text and structural annotations."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4
from . import db
from .analysis import Analyzer
from .evaluation import evaluate, load_weights
from .ingest import timestamp, unique_documents
from .profiles import analyze_corpus, build_profile
from .report import safe, write_json, write_profile
from .structure import structure_metrics
from .craft import reading_map, write_map


def local_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("実験ファイルは実験ディレクトリ内に置いてください")
    return path


def record_experiment(case, backend="auto", weights_path=None):
    case = Path(case).resolve()
    manifest = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("versions"), list) or not manifest["versions"]:
        raise ValueError("manifestにversionsの配列が必要です")
    analyzer, weights = Analyzer(backend), load_weights(weights_path)
    refs = unique_documents(local_path(case, manifest["reference"]), "reference")
    _, reference = analyze_corpus(refs, "reference", analyzer)
    versions, ids = [], set()
    for version in manifest["versions"]:
        identifier = version["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier) or identifier in ids:
            raise ValueError("版のidは重複のない英数字・ハイフン・アンダースコアで指定してください")
        ids.add(identifier)
        text = local_path(case, version["path"]).read_text(encoding="utf-8-sig")
        if not text.strip():
            raise ValueError(f"空の版です: {identifier}")
        for note in version.get("annotations", []):
            confidence = note.get("confidence")
            if not isinstance(confidence, (float, int)) or isinstance(confidence, bool) or not 0 <= confidence <= 1 or not note.get("evidence") or note["evidence"] not in text:
                raise ValueError(f"注釈には本文内の根拠と0〜1のconfidenceが必要です: {identifier}")
        doc = dict(id=1, text=text, text_hash=db.text_hash(text),
                   collected_at=timestamp(manifest["created_at"]), source_type="experiment",
                   author_type=manifest.get("author_type", "unknown"), source_ref=version["path"])
        _, result = analyze_corpus([doc], "experiment", analyzer)
        review = json.loads(local_path(case, version["review"]).read_text(encoding="utf-8")) if version.get("review") else None
        result["reading_map"] = reading_map(text, manifest.get("genre", "essay"), review, rhythm_backend=backend)
        versions.append((version, doc, result, evaluate(reference, result, weights)))
    # Validate all inputs before creating a new snapshot. Older runs are never overwritten.
    run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    out = case / "records" / run_name
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "manifest.json", manifest)
    write_json(out / "reference_documents.json", refs)
    write_json(out / "reference_analysis.json", reference)
    write_profile(out / "reference", build_profile(reference, top=10))
    summary = {"schema_version": 1, "recorded_at": db.now(), "title": manifest["title"],
               "provenance": manifest.get("provenance", "未指定"), "analyzer": analyzer.info,
               "reference_author_types": reference["author_types"], "weights": weights, "versions": []}
    lines = [f"# {safe(manifest['title'])} 改稿記録", "", summary["provenance"], "",
             "各版は同じ作業内で作成した比較用の文章です。実測値は機械集計、構成の注釈は生成者による解釈です。", "",
             "## 表現と構造の変化", "", "| 版 | 文字数 | 平均文長 | 段落数 | 平均段落長 | 基準との距離 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for version, doc, result, evaluation in versions:
        folder = out / version["id"]
        write_profile(folder, build_profile(result, top=10))
        (folder / "text.md").write_text(doc["text"], encoding="utf-8")
        write_json(folder / "analysis.json", result)
        write_json(folder / "evaluation.json", evaluation)
        write_json(folder / "structure.json", structure_metrics(doc["text"]))
        write_map(folder / "craft", result["reading_map"])
        entry = {"id": version["id"], "text_hash": doc["text_hash"], "intent": version["intent"],
                 "changes": version.get("changes", []), "annotations": version.get("annotations", []),
                 "char_count": result["char_count"], "sentence_metrics": result["sentence_metrics"],
                 "structure_metrics": result["structure_metrics"], "evaluation": evaluation}
        summary["versions"].append(entry)
        lines.append(f"| [{version['id']}]({version['id']}/text.md) | {result['char_count']} | {result['sentence_metrics']['mean']:.2f} | {result['structure_metrics']['paragraph_count']} | {result['structure_metrics']['mean_paragraph_length']:.2f} | {evaluation['distance']:.6f} |")
    lines += ["", "距離が小さいほど、この合成基準文の分布に近いことを示します。自然さや論理の良さ、人間らしさの得点ではありません。", "",
              "文長・文字数の集計にはMarkdownの見出しも含みます。構造の段落集計は見出しを除きます。", "",
              "## 指標ごとの距離", "", "| 指標 | " + " | ".join(v["id"] for v in manifest["versions"]) + " |",
              "| --- | " + " | ".join("---:" for _ in versions) + " |"]
    for metric in weights:
        values = [v[3]["metrics"][metric] for v in versions]
        lines.append(f"| {metric} | " + " | ".join("未計測" if x is None else f"{x:.6f}" for x in values) + " |")
    for entry in summary["versions"]:
        lines += ["", f"## {entry['id']}: 変更意図と構成の読み", "", entry["intent"], ""]
        lines += [f"- {change}" for change in entry["changes"]]
        for note in entry["annotations"]:
            lines += ["", f"{note['aspect']}: {note['observation']}（解釈のconfidence={note['confidence']}）", "", f"> {note['evidence']}"]
    lines += ["", "## 次回も同じ条件で記録する", "", "新しい本文をversionsへ追加し、manifest.jsonに版と変更意図を追記してrecord-experimentを実行します。既存の記録は保持され、新しい記録フォルダが作られます。", ""]
    write_json(out / "trajectory.json", summary)
    (out / "trajectory.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(case / "records" / "latest.json", {"path": run_name, "recorded_at": summary["recorded_at"]})
    return out
