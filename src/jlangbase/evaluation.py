"""Bounded distances with explicit, configurable weights and missing metrics."""
from collections import Counter
import json
import math
from pathlib import Path
from .report import write_json

DEFAULT_WEIGHTS = {"sentence_length": 1, "char_types": 1, "transitions": 1, "endings": 1,
                   "ngrams": 1, "paragraph_length": 1, "sentences_per_paragraph": 1, "document_structure": 1}


def load_weights(path=None):
    weights = DEFAULT_WEIGHTS.copy()
    if path:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("評価設定はJSONオブジェクトで指定してください")
        if value.keys() - weights.keys():
            raise ValueError("不明な評価指標: " + ", ".join(sorted(value.keys() - weights.keys())))
        weights.update(value)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in weights.values()) or not sum(weights.values()):
        raise ValueError("評価重みは有限の非負数で指定し、少なくとも1つを正にしてください")
    return weights


def tv_distance(a, b):
    total_a, total_b = sum(a.values()), sum(b.values())
    if not total_a and not total_b:
        return 0.0
    if not total_a or not total_b:
        return 1.0
    return min(1.0, sum(abs(a.get(k, 0) / total_a - b.get(k, 0) / total_b) for k in a.keys() | b.keys()) / 2)


def bucket(histogram, width):
    result = Counter()
    for size, count in histogram.items():
        result[int(size) // width] += count
    return result


def expression_distribution(result, kind):
    return {(r["expression"], r["token_length"]): r["count"] for r in result["expressions"] if r["kind"] == kind}


def relative_difference(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1)


def distances(reference, candidate):
    available = reference["analyzer"]["morphology_available"] and candidate["analyzer"]["morphology_available"]
    if available and reference["analyzer"] != candidate["analyzer"]:
        raise ValueError("評価には同じ解析器・辞書バージョンが必要です")
    a, b = reference["structure_metrics"], candidate["structure_metrics"]
    metrics = {
        "sentence_length": tv_distance(bucket(reference["sentence_metrics"]["length_distribution"], 10), bucket(candidate["sentence_metrics"]["length_distribution"], 10)),
        "char_types": tv_distance(reference["char_type_ratios"], candidate["char_type_ratios"]),
        "paragraph_length": tv_distance(bucket(a["paragraph_length_distribution"], 50), bucket(b["paragraph_length_distribution"], 50)),
        "sentences_per_paragraph": tv_distance(a["sentences_per_paragraph_distribution"], b["sentences_per_paragraph_distribution"]),
        "document_structure": sum(relative_difference(a[k], b[k]) for k in ("mean_paragraph_count", "mean_first_paragraph_share", "mean_last_paragraph_share", "mean_paragraph_length_cv")) / 4,
    }
    for metric, kind in (("transitions", "transition"), ("endings", "ending"), ("ngrams", "ngram")):
        if available:
            x, y = expression_distribution(reference, kind), expression_distribution(candidate, kind)
            distribution = tv_distance(x, y)
            # Transition rate is measured separately from its relative distribution.
            if metric == "transitions":
                rate_x = sum(x.values()) / (reference["token_count"] or 1)
                rate_y = sum(y.values()) / (candidate["token_count"] or 1)
                distribution = (distribution + relative_difference(rate_x, rate_y)) / 2
            metrics[metric] = distribution
        else:
            metrics[metric] = None
    return metrics


def evaluate(reference, candidate, weights=None):
    weights = load_weights() if weights is None else weights
    # Validate programmatic configuration too.
    if weights.keys() != DEFAULT_WEIGHTS.keys() or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in weights.values()):
        raise ValueError("評価重みのキーまたは値が不正です")
    detail = distances(reference, candidate)
    total = sum(weights[k] for k, v in detail.items() if v is not None)
    if not total:
        raise ValueError("利用可能な指標に正の重みがありません")
    return {"distance": sum(v * weights[k] for k, v in detail.items() if v is not None) / total,
            "metrics": detail, "weights": weights,
            "effective_weights": {k: weights[k] / total if v is not None else 0 for k, v in detail.items()},
            "missing_metrics": {k: "形態素解析未実施" for k, v in detail.items() if v is None}}


def evaluate_versions(reference, before, after, weights=None):
    a, b = evaluate(reference, before, weights), evaluate(reference, after, weights)
    return {"schema_version": 1, "before": a, "after": b,
            "distance_reduction": a["distance"] - b["distance"],
            "reference_document_count": reference["document_count"],
            "reference_author_types": reference["author_types"],
            "notes": ["距離は0〜1で、0ほど観測分布が近いことを示します。文章の良さや事実の正しさを測る値ではありません。",
                      "文長は10文字幅、段落長は50文字幅の分布を比較します。構成距離は段落数と冒頭・末尾の比率、段落長の変動を比較します。",
                      "段落の論理的な役割は別途、本文の根拠と確信度を添えて記録してください。"]}


def write_evaluation(out, result):
    out = Path(out)
    write_json(out / "evaluation.json", result)
    lines = ["# 改稿前後の距離", "", f"初稿: {result['before']['distance']:.6f} / 改稿: {result['after']['distance']:.6f}",
             f"距離の減少: {result['distance_reduction']:.6f}（負なら増加）", "",
             "| 指標 | 初稿 | 改稿 |", "| --- | ---: | ---: |"]
    for key, value in result["before"]["metrics"].items():
        after = result["after"]["metrics"][key]
        lines.append(f"| {key} | {value if value is not None else '未計測'} | {after if after is not None else '未計測'} |")
    lines += [""] + [f"- {note}" for note in result["notes"]]
    (out / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
