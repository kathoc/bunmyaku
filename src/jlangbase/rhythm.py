"""Local cadence changes. Written mora estimates are not performed prosody."""
from collections import Counter
import re
import statistics
import unicodedata
from .analysis import Analyzer

SMALL = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")
PUNCT = set("「」『』（）()[]【】〈〉《》\"'“”‘’…⋯・—ー") - {"ー"}


def mora_count(reading):
    count, previous_kana = 0, False
    for char in unicodedata.normalize("NFKC", reading):
        if char.isspace() or char in PUNCT or unicodedata.category(char).startswith("P"):
            previous_kana = False
            continue
        if char in SMALL:
            if not previous_kana:
                return None
            continue
        if "\u3041" <= char <= "\u3096" or "\u30a1" <= char <= "\u30fa" or char == "ー":
            count += 1
            previous_kana = True
        else:
            return None
    return count


def phrase_reading(text, analyzer):
    direct = mora_count(text)
    if direct is not None:
        return {"mora": direct, "method": "kana", "unknown": []}
    if analyzer.tokenizer is None:
        return {"mora": None, "method": "unavailable", "unknown": [text]}
    total, unknown = 0, []
    for token in analyzer.tokenizer.tokenize(text):
        surface = token.surface()
        if not surface.strip() or all(unicodedata.category(c).startswith(("P", "S")) for c in surface):
            continue
        count = mora_count(token.reading_form())
        if count is None:
            unknown.append(surface)
        else:
            total += count
    return {"mora": None if unknown else total, "method": "sudachi_reading", "unknown": unknown}


def rhythm_map(blocks, backend="auto", history_size=3, relative_change=.5):
    analyzer = Analyzer(backend)
    cadences, changes = [], []
    for block in blocks:
        for index, sentence in enumerate(block["sentences"], 1):
            body = sentence.strip().rstrip("。！？!?\r\n")
            phrases = [p.strip() for p in re.split(r"[、，,；;]+", body) if p.strip()]
            if not phrases:
                continue
            values = [phrase_reading(p, analyzer) for p in phrases]
            cadence = {"paragraph": block["id"], "sentence": index, "phrases": phrases,
                       "characters": [len(p) for p in phrases], "mora": [v["mora"] for v in values],
                       "methods": [v["method"] for v in values], "unknown": [x for v in values for x in v["unknown"]]}
            history = cadences[-history_size:]
            if len(history) == history_size and all(len(h["mora"]) == len(values) and all(v is not None for v in h["mora"]) for h in history) and all(v["mora"] is not None for v in values):
                baseline = [statistics.median(h["mora"][i] for h in history) for i in range(len(values))]
                delta = [value["mora"] - base for value, base in zip(values, baseline)]
                magnitude = sum(abs(d) for d in delta) / max(sum(baseline), 1)
                if magnitude >= relative_change:
                    changes.append({"paragraph": block["id"], "sentence": index, "baseline_mora": baseline,
                                    "current_mora": cadence["mora"], "delta": delta, "relative_change": magnitude,
                                    "history_locations": [{"paragraph": h["paragraph"], "sentence": h["sentence"]} for h in history],
                                    "interpretation": "直前の句列からの変化。抑揚・面白さ・記憶への効果は未判定。"})
            cadences.append(cadence)
    return {"schema_version": 1, "analyzer": analyzer.info, "history_size": history_size,
            "relative_change_threshold": relative_change, "cadences": cadences, "local_changes": changes,
            "mora_coverage": sum(all(v is not None for v in c["mora"]) for c in cadences) / len(cadences) if cadences else 0,
            "notes": ["句読点で区切った推定拍列です。アクセント・間・声の高さは計測していません。",
                      "直前3文の同じ句数の並びとの比較です。文全体が短長でも、比較可能な局所窓がなければ判定しません。",
                      "漢字の読みには辞書依存と曖昧さがあります。読めない箇所はnullで、文字数で補いません。"]}
