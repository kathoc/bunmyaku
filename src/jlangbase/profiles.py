"""Full corpus statistics and bounded, LLM-readable profiles."""
from collections import Counter
import statistics
from . import db
from .analysis import Analyzer, CHAR_TYPES, PUNCTUATION
from .expressions import aggregate
from .structure import structure_metrics, aggregate_structure

NOTES = [
    "観測したコーパス内の統計です。日本語全体や流行の判定には使えません。",
    "文字比率の分母は空白・記号を含む本文のUnicode文字数です。文長は前後の空白を除き、句読点を含みます。",
    "token頻度の分母には句読点tokenを含み、URLと空白は除きます。表現は表層形で集計します。",
    "文頭・文末は周辺の記号を除いて抽出します。接続候補は文頭の固定候補と接続詞品詞による機械抽出です。",
]


def analyze_corpus(documents, source_type, analyzer=None, filter_noise=True):
    if not documents:
        raise ValueError(f"解析対象の文書がありません: {source_type}")
    analyzer = analyzer or Analyzer()
    analyzed = [analyzer.analyze(doc) for doc in sorted(documents, key=lambda d: d["text_hash"])]
    for item in analyzed:
        item["structure"] = structure_metrics(item["document"]["text"])
        item["metrics"]["structure"] = item["structure"]
    dates = [d.get("published_at") or d["collected_at"] for d in documents]
    period = {"from": min(dates), "to": max(dates)}
    lengths = [n for item in analyzed for n in item["metrics"]["sentence_lengths"]]
    char_count = sum(item["metrics"]["char_count"] for item in analyzed)
    char_counts = {k: sum(item["metrics"]["char_type_counts"][k] for item in analyzed) for k in CHAR_TYPES}
    punctuation = {k: sum(item["metrics"]["punctuation_counts"][k] for item in analyzed) for k in PUNCTUATION}
    token_count = sum(len(s["tokens"]) for item in analyzed for s in item["sentences"])
    expressions = aggregate(analyzed, source_type, period, filter_noise)
    result = {
        "schema_version": 1, "source_type": source_type, "corpus_period": period,
        "document_count": len(documents), "char_count": char_count,
        "token_count": token_count if analyzer.info["morphology_available"] else None,
        "analyzer": analyzer.info, "filter_noise": filter_noise,
        "sentence_metrics": {"count": len(lengths), "mean": statistics.mean(lengths) if lengths else 0,
                             "median": statistics.median(lengths) if lengths else 0,
                             "length_distribution": dict(sorted(Counter(lengths).items()))},
        "char_type_ratios": {k: v / char_count if char_count else 0 for k, v in char_counts.items()},
        "punctuation_metrics": {k: {"count": v, "per_10k_chars": v * 10000 / char_count if char_count else 0} for k, v in punctuation.items()},
        "expressions": expressions,
        "structure_metrics": aggregate_structure(analyzed),
        "author_types": dict(sorted(Counter(d.get("author_type") or "unknown" for d in documents).items())),
        "notes": NOTES + ([] if analyzer.info["morphology_available"] else ["形態素解析は未実施です。token数と表現統計は利用できません。"]),
    }
    return analyzed, result


def run_analysis(conn, source_type, backend="auto", filter_noise=True):
    analyzed, result = analyze_corpus(db.documents(conn, source_type), source_type, Analyzer(backend), filter_noise)
    run_id = db.save_run(conn, source_type, result["analyzer"], analyzed, result)
    return run_id, result


def build_profile(result, top=20, compact=False, generated_at=None):
    if top < 1:
        raise ValueError("topは1以上で指定してください")
    top = min(top, 3) if compact else top
    keys = ("schema_version", "source_type", "corpus_period", "document_count", "char_count", "token_count",
            "analyzer", "sentence_metrics", "char_type_ratios", "punctuation_metrics", "author_types", "notes", "structure_metrics")
    profile = {k: result[k] for k in keys}
    profile["generated_at"] = generated_at or db.now()
    profile["structure_metrics"] = {k: v for k, v in result["structure_metrics"].items() if not k.endswith("_distribution")}
    profile["sentence_metrics"] = {k: v for k, v in result["sentence_metrics"].items() if k != "length_distribution"}
    for name, kind in (("common_ngrams", "ngram"), ("sentence_endings", "ending"),
                       ("sentence_openings", "opening"), ("transition_candidates", "transition"), ("formula_candidates", "formula")):
        rows = [r for r in result["expressions"] if r["kind"] == kind and (not compact or len(r["expression"]) <= 60)][:top]
        fields = ("expression", "token_length", "count", "documents_count", "per_10k_tokens")
        profile[name] = [{k: r[k] for k in fields} for r in rows]
    profile["llm_summary"] = {
        "observed_mean_sentence_length": profile["sentence_metrics"]["mean"],
        "guidance": "このジャンルの観測値を参考にし、内容に必要な表現を優先する。頻出表現の挿入を義務にしない。",
    }
    if compact:
        profile["notes"] = ["観測コーパス内の参考値です。流行や文章品質の判定ではありません。"] + ([] if result["token_count"] is not None else ["形態素解析未実施。表現統計は利用不能です。"])
    return profile
