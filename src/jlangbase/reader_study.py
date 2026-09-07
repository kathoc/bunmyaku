"""Counterbalanced blinded reading packets; no fabricated reader outcomes."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics
from .db import text_hash
from .report import write_json
from .paragraphs import paragraphs

RATINGS = ("curiosity", "self_reported_understanding", "felt_effort")


def prepare_study(paths, out):
    if not 2 <= len(paths) <= 6:
        raise ValueError("比較する本文を2〜6本指定してください")
    sources = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8-sig")
        if not text.strip():
            raise ValueError("空の本文は比較できません")
        sources.append({"path": str(Path(path).resolve()), "text": text, "text_hash": text_hash(text)})
    if len({s["text_hash"] for s in sources}) != len(sources):
        raise ValueError("同一本文の重複を除いてください")
    out = Path(out)
    if out.exists():
        raise ValueError("過去の読者評価を保持するため、新しい出力ディレクトリを指定してください")
    random.SystemRandom().shuffle(sources)
    labels = [chr(65 + i) for i in range(len(sources))]
    mapping = dict(zip(labels, sources))
    public = out / "public"
    public.mkdir(parents=True)
    # The private key contains authorship/version names and must not go to readers.
    write_json(out / "private/key.json", {k: {field: v[field] for field in ("path", "text_hash")} for k, v in mapping.items()})
    packets = []
    for i in range(len(labels)):
        order = labels[i:] + labels[:i]
        packet_id = f"packet-{i + 1:02d}"
        packets.append({"id": packet_id, "order": order})
        opening_lines = ["# 導入だけの比較", "", "この資料だけを読んでopening_curiosityとfirst_attention_quoteを記録し、その後に全文を開いてください。", ""]
        for label in order:
            blocks = paragraphs(mapping[label]["text"])
            opening_lines += [f"## 本文 {label}", "", blocks[0]["text"] if blocks else mapping[label]["text"], ""]
        (public / f"{packet_id}-opening.md").write_text("\n".join(opening_lines), encoding="utf-8")
        lines = ["# 文章の比較", "", "版名や作者は伏せています。この順序で読み、各本文を閉じてから回答してください。", "",
                 "まず各本文の最初の段落だけを読み、続きを読みたいかをopening_curiosityへ記録してください。その後、全文を読みます。",
                 "続きが気になったか、何を理解したか、読み返した箇所、残った言葉を別々に記録してください。", ""]
        for label in order:
            lines += [f"## 本文 {label}", "", mapping[label]["text"], ""]
        (public / f"{packet_id}.md").write_text("\n".join(lines), encoding="utf-8")
        write_json(public / f"{packet_id}-response.json", {
            "packet": packet_id, "reader_id": "", "reviewer_kind": "human", "preference": None,
            "responses": [{"label": label, "opening_curiosity": None, "first_attention_quote": "", "curiosity": None, "self_reported_understanding": None, "felt_effort": None,
                           "comprehension_answer": "", "recall": "", "friction_quote": "", "friction_effect": "", "reason": ""} for label in order]})
    write_json(out / "study.json", {"schema_version": 1, "labels": labels, "packets": packets,
                                  "rating_range": [1, 5], "status": "awaiting_readers",
                                  "design": "全版を読む順序を循環させる。反復による持ち越し効果は分離できない。",
                                  "rating_notes": "理解度の評点は自己申告。comprehension_answerとrecallを別に評価する。felt_effortの低さだけを良さとしない。"})
    return out


def summarize_study(study_path, responses_path):
    study_path = Path(study_path)
    study = json.loads((study_path / "study.json").read_text(encoding="utf-8"))
    records = []
    path = Path(responses_path)
    text = path.read_text(encoding="utf-8-sig")
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"回答JSONLの{number}行目が不正です") from exc
        records.append(value)
    labels = set(study["labels"])
    packet_ids = {p["id"] for p in study["packets"]}
    seen, grouped, preferences = set(), defaultdict(lambda: defaultdict(list)), defaultdict(Counter)
    for row in records:
        if not isinstance(row, dict) or row.get("reviewer_kind") not in {"human", "model"} or not isinstance(row.get("reader_id"), str) or not row["reader_id"].strip() or row.get("packet") not in packet_ids:
            raise ValueError("回答にreader_id、reviewer_kind、正しいpacketが必要です")
        key = row["reviewer_kind"], row["reader_id"]
        if key in seen:
            raise ValueError("同じ読者の重複回答があります")
        seen.add(key)
        preference = row.get("preference")
        if preference not in labels | {"tie", None}:
            raise ValueError("preferenceが不正です")
        values = row.get("responses")
        if not isinstance(values, list) or len(values) != len(labels) or {v.get("label") for v in values if isinstance(v, dict)} != labels:
            raise ValueError("各ラベルの回答を重複なく指定してください")
        for value in values:
            if value.get("opening_curiosity") is not None and (type(value["opening_curiosity"]) is not int or not 1 <= value["opening_curiosity"] <= 5):
                raise ValueError("opening_curiosityは1〜5の整数かnullで指定してください")
            if not isinstance(value.get("first_attention_quote", ""), str):
                raise ValueError("first_attention_quoteは文字列で指定してください")
            for metric in RATINGS:
                if type(value.get(metric)) is not int or not 1 <= value[metric] <= 5:
                    raise ValueError(f"{metric}は1〜5の整数で回答してください")
            for field in ("comprehension_answer", "recall", "friction_quote", "friction_effect", "reason"):
                if not isinstance(value.get(field), str):
                    raise ValueError(f"{field}は文字列で指定してください")
            if not value["reason"].strip():
                raise ValueError("評点だけでなくreasonを記録してください")
            grouped[key[0]][value["label"]].append(value)
        if preference:
            preferences[key[0]][preference] += 1
    result = {"schema_version": 1, "reader_count": len(seen), "groups": {}, "quality_improved": None,
              "notes": ["理解度の数値は自己申告です。理解回答と想起内容を確認してください。", "人間とモデルの評価を混ぜません。未回答を低評価や改善成功に変換しません。", "小標本の記述統計であり、一般的な因果効果の推定ではありません。"]}
    for kind in ("human", "model"):
        count = sum(k[0] == kind for k in seen)
        group = {"reader_count": count, "status": "observed" if count else "not_measured", "preferences": dict(preferences[kind]), "versions": {}}
        for label in sorted(labels):
            rows = grouped[kind][label]
            opening = [r["opening_curiosity"] for r in rows if r.get("opening_curiosity") is not None]
            group["versions"][label] = {"n": len(rows), "mean": {m: statistics.mean(r[m] for r in rows) if rows else None for m in RATINGS},
                                       "opening_curiosity": {"n": len(opening), "mean": statistics.mean(opening) if opening else None},
                                       "observations": [{k: r.get(k, "") for k in ("first_attention_quote", "comprehension_answer", "recall", "friction_quote", "friction_effect", "reason")} for r in rows]}
        result["groups"][kind] = group
    return result
