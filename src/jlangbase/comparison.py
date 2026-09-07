"""Descriptive corpus contrasts; never an authorship detector."""
from pathlib import Path
from .report import safe, write_json


def expression_map(result):
    return {(r["kind"], r["expression"], r["token_length"]): r for r in result["expressions"]}


def contrast_rows(before, after):
    if not before["analyzer"]["morphology_available"] or not after["analyzer"]["morphology_available"]:
        return []
    if before["analyzer"] != after["analyzer"]:
        raise ValueError("表現比較には同じ解析器・辞書バージョンが必要です")
    a, b = expression_map(before), expression_map(after)
    rows = []
    for key in sorted(a.keys() | b.keys()):
        left, right = a.get(key, {}), b.get(key, {})
        x, y = left.get("per_10k_tokens", 0), right.get("per_10k_tokens", 0)
        c1 = left.get("documents_count", 0) / before["document_count"] if before["document_count"] else 0
        c2 = right.get("documents_count", 0) / after["document_count"] if after["document_count"] else 0
        rows.append(dict(kind=key[0], expression=key[1], token_length=key[2],
                         before_per_10k=x, after_per_10k=y,
                         ratio=y / x if x else (1.0 if not y else None),
                         ratio_reason="baseline_zero" if not x and y else None,
                         delta=y - x, coverage_diff=c2 - c1,
                         before_count=left.get("count", 0), after_count=right.get("count", 0),
                         before_documents_count=left.get("documents_count", 0), after_documents_count=right.get("documents_count", 0)))
    return rows


def metric_differences(a, b):
    return {
        "mean_sentence_length": b["sentence_metrics"]["mean"] - a["sentence_metrics"]["mean"],
        "median_sentence_length": b["sentence_metrics"]["median"] - a["sentence_metrics"]["median"],
        "char_type_ratios": {k: b["char_type_ratios"][k] - v for k, v in a["char_type_ratios"].items()},
        "punctuation_per_10k_chars": {k: b["punctuation_metrics"][k]["per_10k_chars"] - v["per_10k_chars"] for k, v in a["punctuation_metrics"].items()},
    }


def compare(human, llm):
    rows = []
    for row in contrast_rows(human, llm):
        rows.append(row | {"human_per_10k": row["before_per_10k"], "llm_per_10k": row["after_per_10k"],
                           "absolute_diff": abs(row["delta"])})
    return {"schema_version": 1, "human_document_count": human["document_count"], "llm_document_count": llm["document_count"],
            "human_author_types": human["author_types"], "llm_author_types": llm["author_types"],
            "analyzer": human["analyzer"], "metric_differences": metric_differences(human, llm),
            "overrepresented_in_llm": sorted([r for r in rows if r["delta"] > 0], key=lambda r: (-r["delta"], r["expression"])),
            "underrepresented_in_llm": sorted([r for r in rows if r["delta"] < 0], key=lambda r: (r["delta"], r["expression"])),
            "notes": ["入力のhuman/llm区分は利用者の指定です。著者の判定結果ではありません。",
                      "基準頻度が0で比較側が正の場合、ratioはnullです。頻度差と件数を確認してください。"] +
                     ([] if human["analyzer"]["morphology_available"] and llm["analyzer"]["morphology_available"] else ["形態素解析未実施のため表現比較は利用不能です。"])}


def write_comparison(out, result):
    out = Path(out)
    write_json(out / "comparison.json", result)
    lines = ["# コーパス間の差分", "", f"基準文書数: {result['human_document_count']} / 比較文書数: {result['llm_document_count']}", "",
             "## 文と文字の差（比較側 − 基準側）", "", f"平均文長差: {result['metric_differences']['mean_sentence_length']:.3f}", ""]
    for section in ("overrepresented_in_llm", "underrepresented_in_llm"):
        lines += [f"## {section}", "", "| 種類 | 表現 | 基準/1万token | 比較/1万token | 比率 | カバレッジ差 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
        lines += [f"| {r['kind']} | {safe(r['expression'])} | {r['human_per_10k']:.2f} | {r['llm_per_10k']:.2f} | {r['ratio'] if r['ratio'] is not None else '基準0'} | {r['coverage_diff']:.3f} |" for r in result[section][:50]]
        lines += [""]
    lines += ["## 注意事項", ""] + [f"- {n}" for n in result["notes"]]
    (out / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
