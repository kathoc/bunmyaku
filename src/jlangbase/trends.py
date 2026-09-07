"""Equal-length, half-open time windows with auditable threshold rules."""
from datetime import datetime
import json
import math
from pathlib import Path
from .comparison import contrast_rows
from .ingest import timestamp
from .profiles import analyze_corpus
from .report import safe, write_json

DEFAULT_THRESHOLDS = {"min_count": 3, "min_documents": 2, "rising_ratio": 1.5, "declining_ratio": 0.6666666667}


def load_thresholds(path=None):
    result = DEFAULT_THRESHOLDS.copy()
    if path:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.keys() - result.keys():
            raise ValueError("差分の設定キーが不正です")
        result.update(value)
    for key in ("min_count", "min_documents"):
        if type(result[key]) is not int or result[key] < 1:
            raise ValueError(f"{key}は1以上の整数で指定してください")
    for key in ("rising_ratio", "declining_ratio"):
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key}は有限の数値で指定してください")
    if not 0 < result["declining_ratio"] < 1 < result["rising_ratio"]:
        raise ValueError("比率は declining < 1 < rising を満たす正の数で指定してください")
    return result


def classify(row, thresholds):
    strong_before = row["before_count"] >= thresholds["min_count"] and row["before_documents_count"] >= thresholds["min_documents"]
    strong_after = row["after_count"] >= thresholds["min_count"] and row["after_documents_count"] >= thresholds["min_documents"]
    if not strong_before and not strong_after:
        return "sparse"
    if row["before_count"] == 0 and strong_after:
        return "emerging"
    if not strong_before:
        return "sparse"
    if row["after_count"] == 0:
        return "declining"
    if not strong_after:
        return "sparse"
    if row["ratio"] >= thresholds["rising_ratio"]:
        return "rising"
    if row["ratio"] <= thresholds["declining_ratio"]:
        return "declining"
    return "stable"


def time_diff(documents, source_type, date_from, date_to, analyzer, thresholds=None):
    thresholds = thresholds or load_thresholds()
    middle, end = datetime.fromisoformat(timestamp(date_from)), datetime.fromisoformat(timestamp(date_to))
    if middle >= end:
        raise ValueError("--fromは--toより前の日時で指定してください")
    start = middle - (end - middle)
    before, after = [], []
    for doc in documents:
        date = datetime.fromisoformat(timestamp(doc.get("published_at") or doc["collected_at"]))
        if start <= date < middle:
            before.append(doc)
        elif middle <= date < end:
            after.append(doc)
    if not before or not after:
        raise ValueError("比較する両期間に文書が必要です。期間と公開日時・収集日時を確認してください")
    _, a = analyze_corpus(before, source_type, analyzer)
    _, b = analyze_corpus(after, source_type, analyzer)
    rows = [row | {"status": classify(row, thresholds), "absolute_delta": abs(row["delta"])} for row in contrast_rows(a, b)]
    return {"schema_version": 1, "source_type": source_type,
            "windows": {"before": [start.isoformat(), middle.isoformat()], "after": [middle.isoformat(), end.isoformat()]},
            "before_document_count": len(before), "after_document_count": len(after), "thresholds": thresholds,
            "analyzer": analyzer.info, "expressions": sorted(rows, key=lambda r: (-abs(r["delta"]), r["expression"])),
            "notes": ["期間は開始を含み終了を含みません。公開日時がない文書は収集日時を使用します。",
                      "状態は出現数・文書数・頻度比の閾値による分類です。流行語の判定ではありません。",
                      "両側の標本が閾値を満たす場合に増減を判定します。片側0の出現・消失は、もう片側が閾値を満たす場合に分類します。"] +
                     ([] if analyzer.info["morphology_available"] else ["形態素解析未実施のため表現差分は利用不能です。"])}


def write_diff(out, result):
    out = Path(out)
    write_json(out / "diff.json", result)
    lines = ["# 期間ごとの表現差分", "", f"比較期間: {result['windows']}", "",
             "| 表現 | 状態 | 前期間/1万token | 後期間/1万token | 差 | カバレッジ差 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    lines += [f"| {safe(r['expression'])} | {r['status']} | {r['before_per_10k']:.2f} | {r['after_per_10k']:.2f} | {r['delta']:.2f} | {r['coverage_diff']:.3f} |" for r in result["expressions"][:100]]
    lines += [""] + [f"- {n}" for n in result["notes"]]
    (out / "diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
