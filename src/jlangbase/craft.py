"""Self-contained editorial maps. Signals are not quality scores."""
from collections import Counter
from importlib.resources import files
import json
import math
from pathlib import Path
import re
import statistics
from .db import text_hash
from .paragraphs import paragraphs
from .report import safe, write_json
from .rhythm import rhythm_map

ROLES = {"scene", "question", "claim", "explanation", "evidence", "turn", "qualification", "payoff", "action", "aside"}
DEFAULT_POLICY = {"min_parallel_openings": 3, "long_sentence_chars": 100, "same_ending_run": 5, "uniform_window": 4, "uniform_cv": .15}


def knowledge():
    return json.loads(files("jlangbase").joinpath("resources/craft.json").read_text(encoding="utf-8"))


def load_policy(path=None):
    result = DEFAULT_POLICY.copy()
    if path:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.keys() - result.keys():
            raise ValueError("reading-mapの設定キーが不正です")
        result.update(value)
    for key, value in result.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"設定{key}は有限の正数で指定してください")
        if key != "uniform_cv" and (type(value) is not int or value < 2):
            raise ValueError(f"設定{key}は2以上の整数で指定してください")
    return result


def span(value, blocks):
    if not isinstance(value, dict) or type(value.get("paragraph")) is not int or not 1 <= value["paragraph"] <= len(blocks):
        raise ValueError("根拠のparagraphが不正です")
    quote = value.get("quote")
    block = blocks[value["paragraph"] - 1]
    if not isinstance(quote, str) or not quote.strip() or quote not in block["text"]:
        raise ValueError("根拠のquoteが指定段落にありません")
    return block


def validate_review(review, text, blocks):
    if not isinstance(review, dict) or review.get("text_hash") != text_hash(text):
        raise ValueError("reviewの本文ハッシュが一致しません。改稿後の注釈を作成してください")
    if review.get("reviewer_kind") not in {"human", "model"} or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("reviewerとreviewer_kind(human/model)が必要です")
    nodes, frictions = review.get("nodes", []), review.get("frictions", [])
    if not isinstance(nodes, list) or not isinstance(frictions, list):
        raise ValueError("nodesとfrictionsは配列で指定してください")
    seen = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("nodesの要素はオブジェクトで指定してください")
        block = span(node.get("evidence"), blocks)
        if node.get("role") not in ROLES or block["id"] in seen or not isinstance(node.get("reader_gain"), str) or not node["reader_gain"].strip():
            raise ValueError("各段落のroleとreader_gainを重複なく指定してください")
        seen.add(block["id"])
        deps = node.get("depends_on", [])
        if not isinstance(deps, list) or any(type(p) is not int or not 1 <= p < block["id"] for p in deps):
            raise ValueError("depends_onは先行する段落番号の配列にしてください")
    ids = set()
    for friction in frictions:
        if not isinstance(friction, dict):
            raise ValueError("frictionsの要素はオブジェクトで指定してください")
        anchor = span(friction.get("anchor"), blocks)
        if not isinstance(friction.get("id"), str) or not friction["id"] or friction["id"] in ids:
            raise ValueError("ひっかかりには一意のidが必要です")
        ids.add(friction["id"])
        if friction.get("kind") not in {"delayed_explanation", "omission", "voice", "disproportion", "ambiguity", "rhythm", "register_shift", "scale_jump"} or friction.get("resolution") not in {"local", "later", "open"} or friction.get("necessity") not in {"core", "optional"}:
            raise ValueError("ひっかかりのkind/resolution/necessityが不正です")
        for key in ("reader_question", "benefit", "risk", "decision_reason"):
            if not isinstance(friction.get(key), str) or not friction[key].strip():
                raise ValueError(f"ひっかかりの{key}を記録してください")
        if friction.get("decision") not in {"keep", "revise", "remove", "test"}:
            raise ValueError("decisionはkeep/revise/remove/testで指定してください")
        foothold = span(friction.get("foothold"), blocks)
        if foothold["id"] > anchor["id"]:
            raise ValueError("footholdはひっかかり以前の説明を指定してください")
        payoff = friction.get("payoff")
        if friction["resolution"] == "open":
            if payoff is not None:
                raise ValueError("openにはpayoffを指定できません")
        else:
            target = span(payoff, blocks)
            if target["id"] < anchor["id"] or (friction["resolution"] == "later" and target["id"] == anchor["id"]):
                raise ValueError("回収先はlocalなら同段落以降、laterなら後続段落を指定してください")
        required_at = friction.get("required_at")
        if required_at is not None and (type(required_at) is not int or not anchor["id"] <= required_at <= len(blocks)):
            raise ValueError("required_atはひっかかり以降の段落番号で指定してください")
        if friction.get("claim_status", "not_applicable") not in {"not_applicable", "illustrative", "unverified", "supported"}:
            raise ValueError("claim_statusが不正です")
        if friction.get("claim_status") == "supported" and not friction.get("claim_source"):
            raise ValueError("裏付け済みの主張にはclaim_sourceが必要です")
    for item in nodes + frictions:
        confidence = item.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("解釈には0〜1のconfidenceが必要です")
    return review


def friction_locations(review, blocks):
    locations = []
    total = sum(len(b["text"]) for b in blocks)
    for f in (review or {}).get("frictions", []):
        block = blocks[f["anchor"]["paragraph"] - 1]
        offset = block["text"].index(f["anchor"]["quote"])
        preceding = sum(len(b["text"]) for b in blocks[:block["id"] - 1])
        locations.append({"id": f["id"], "paragraph": block["id"], "first_paragraph": block["id"] == 1,
                          "offset_in_paragraph": offset, "preceding_characters": preceding + offset,
                          "fraction_of_supplied_body": (preceding + offset) / total if total else 0,
                          "claim_status": f.get("claim_status", "not_applicable"),
                          "document_scope": (review or {}).get("document_scope", "unspecified"),
                          "note": "指定原稿内の位置です。冒頭断片の割合を記事全体の割合とはみなしません。早いほど良いという得点ではありません。"})
    return locations


def reading_map(text, genre="essay", review=None, policy=None, rhythm_backend="auto"):
    if genre not in knowledge()["genres"]:
        raise ValueError(f"未対応のgenreです: {genre}")
    policy = load_policy() if policy is None else policy
    blocks = paragraphs(text)
    if not blocks:
        raise ValueError("解析できる本文段落がありません")
    findings = []

    def finding(code, ids, observation, question, basis="measurement", severity="consider"):
        findings.append(dict(code=code, paragraphs=ids, observation=observation, editorial_question=question, basis=basis, severity=severity))

    openings, endings = [], []
    for block in blocks:
        lengths = block["sentence_lengths"]
        block["mean_sentence_length"] = statistics.mean(lengths) if lengths else 0
        block["sentence_length_cv"] = statistics.pstdev(lengths) / statistics.mean(lengths) if lengths and sum(lengths) else 0
        block["quoted_spans"] = len(re.findall(r"「[^」]*」|『[^』]*』", block["text"]))
        block["question_marks"] = sum(block["text"].count(c) for c in "?？")
        block["parentheticals"] = len(re.findall(r"（[^）]*）|\([^)]*\)", block["text"]))
        block["numeric_cues"] = re.findall(r"[0-9０-９]+(?:[.,．][0-9０-９]+)*(?:万|億|兆)?(?:回|日|年|円|人|倍|時間)?(?:ほど|くらい)?", block["text"])
        block["first_sentence"] = block["sentences"][0] if lengths else ""
        if re.match(r"^(まず|次に|さらに|また|一方で|最後に)[、,]", block["text"]):
            openings.append(block["id"])
        for sentence in block["sentences"]:
            clean = sentence.rstrip('。！？!?」』）)\" ')
            ending = re.search(r"(である|だった|でした|ません|ます|です|だ)$", clean)
            endings.append((ending[1] if ending else None, block["id"]))
            if len(sentence) > policy["long_sentence_chars"]:
                finding("long_sentence", [block["id"]], f"{len(sentence)}文字の文", "主述関係や列挙を確認する。文が長いという理由だけで分割しない。")
    if len(openings) >= policy["min_parallel_openings"] and genre != "guide":
        finding("parallel_openings", openings, f"並列を示す段落頭が{len(openings)}箇所", "各段落で読み手の理解が進むか。それとも同じ主張の例が並ぶだけか。")
    run = []
    for ending, pid in endings + [(None, None)]:
        if not run or ending is None or ending != run[-1][0]:
            if len(run) >= policy["same_ending_run"]:
                finding("ending_run", sorted({p for _, p in run}), f"同じ終止形が{len(run)}文連続", "語尾だけを変えず、説明・場面・判断の役割が単調かを本文で確認する。")
            run = []
        if ending is not None:
            run.append((ending, pid))
    window = policy["uniform_window"]
    for start in range(len(blocks) - window + 1):
        group = blocks[start:start + window]
        lengths = [len(b["text"]) for b in group]
        if statistics.pstdev(lengths) / statistics.mean(lengths) < policy["uniform_cv"]:
            finding("uniform_local_shape", [b["id"] for b in group], f"連続{window}段落の長さが近い", "段落ごとの役割や重要度まで均一になっていないか。形が近いだけなら残す。")
    transitions = [dict(before=a["id"], after=b["id"], mean_sentence_length_delta=b["mean_sentence_length"] - a["mean_sentence_length"],
                        quotation_delta=b["quoted_spans"] - a["quoted_spans"], question_delta=b["question_marks"] - a["question_marks"])
                   for a, b in zip(blocks, blocks[1:])]
    if review is not None:
        validate_review(review, text, blocks)
        for f in review.get("frictions", []):
            anchor = f["anchor"]["paragraph"]
            late = f.get("required_at") is not None and (f["resolution"] == "open" or f["payoff"]["paragraph"] > f["required_at"])
            if f["necessity"] == "core" and (f["resolution"] == "open" or late or genre == "guide" and f["resolution"] == "later"):
                finding("missing_prerequisite", [anchor], "注釈で必須とされた情報が必要な時点で未提示", "好奇心のために待たせる情報と、理解・操作に必須の情報を分ける。", "review_annotation", "revise")
        ordered = sorted(review.get("nodes", []), key=lambda n: n["evidence"]["paragraph"])
        for a, b in zip(ordered, ordered[1:]):
            if a["reader_gain"].strip() == b["reader_gain"].strip():
                finding("repeated_reader_gain", [a["evidence"]["paragraph"], b["evidence"]["paragraph"]], "注釈上の新情報が同じ", "繰り返す必要があるか、統合できるかを確認する。", "review_annotation")
    return {"schema_version": 1, "engine": "jlangbase-reading-map-1", "text_hash": text_hash(text), "genre": genre,
            "policy": policy, "paragraphs": blocks, "transitions": transitions, "findings": findings, "review": review,
            "rhythm": rhythm_map(blocks, rhythm_backend), "friction_locations": friction_locations(review, blocks),
            "quality_score": None, "reader_outcomes": "not_measured",
            "notes": ["検出値は表面上の手がかりです。感情の強弱・面白さ・理解度の判定ではありません。",
                      "注釈の根拠と本文の一致は検査しますが、その解釈が正しいと保証するものではありません。",
                      "疑問符や未回収の数を増やすことを目標にしません。必要のない段落は滑らかなままで構いません。"]}


def write_map(out, result):
    out = Path(out)
    write_json(out / "reading-map.json", result)
    lines = ["# 読者が追う順序と編集上の検討箇所", "", "面白さ・理解度は未計測です。以下は観測値と根拠付きの解釈です。", "",
             "| 段落 | 行 | 文数 | 平均文長 | 冒頭文 |", "| --- | ---: | ---: | ---: | --- |"]
    for b in result["paragraphs"]:
        lines.append(f"| {b['id']} | {b['line']} | {len(b['sentences'])} | {b['mean_sentence_length']:.1f} | {safe(b['first_sentence'])} |")
    lines += ["", "## 検討する箇所", ""]
    for f in result["findings"]:
        lines += [f"- {f['code']} / 段落{f['paragraphs']}: {f['observation']}。{f['editorial_question']}"]
    if not result["findings"]:
        lines += ["この検出器の指摘はありません。文章の品質を保証する結果ではありません。"]
    review = result["review"]
    lines += ["", "## 直前の拍列から変化した箇所", ""]
    for change in result["rhythm"]["local_changes"]:
        lines += [f"- 段落{change['paragraph']}・文{change['sentence']}: {change['baseline_mora']} → {change['current_mora']}。{change['interpretation']}"]
    if not result["rhythm"]["local_changes"]:
        lines += ["比較条件を満たす局所変化は検出されませんでした。抑揚がないという意味ではありません。"]
    lines += [""] + [f"- {n}" for n in result["rhythm"]["notes"]]
    if review:
        lines += ["", f"## 構成の解釈（{safe(review['reviewer_kind'])}: {safe(review['reviewer'])}）", ""]
        for n in sorted(review.get("nodes", []), key=lambda n: n["evidence"]["paragraph"]):
            lines += [f"- 段落{n['evidence']['paragraph']} / {n['role']}: {n['reader_gain']}（confidence={n['confidence']}）"]
        lines += ["", "## ひっかかりを残す・直す判断", ""]
        for f in review.get("frictions", []):
            location = next(p for p in result["friction_locations"] if p["id"] == f["id"])
            lines += [f"### {f['id']}: {f['decision']}", "", f"段落{f['anchor']['paragraph']}: {f['anchor']['quote']}", "",
                      f"本文先頭からの文字数: {location['preceding_characters']} / 対象範囲: {location['document_scope']} / 事実の扱い: {location['claim_status']}",
                      f"読者に残す問い: {f['reader_question']}", f"働きの仮説: {f['benefit']}", f"リスク: {f['risk']}",
                      f"回収: {f['resolution']}" + (f" / 段落{f['payoff']['paragraph']}" if f.get("payoff") else ""),
                      f"判断理由: {f['decision_reason']}（confidence={f['confidence']}）", ""]
    lines += [""] + [f"- {n}" for n in result["notes"]]
    (out / "reading-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_brief(out, topic, reader, purpose, genre="essay"):
    import json
    from importlib.resources import files

    catalog = knowledge()
    if genre not in catalog["genres"]:
        raise ValueError("未対応のgenreです")
    selected = catalog["genres"][genre]
    principles = [p for p in catalog["principles"] if p["id"] in selected["focus"]]
    research = json.loads(files("jlangbase").joinpath("resources/interest-research.json").read_text(encoding="utf-8"))
    lenses = [lens for lens in research["lenses"] if genre in lens["genres"]]
    brief = {"schema_version": 1, "topic": topic, "reader": reader, "purpose": purpose, "genre": genre,
             "principles": principles, "constraint": selected["constraint"], "sources": catalog["sources"],
             "workflow": ["読者の既知・知りたいこと・読み終えた後の変化を一文ずつ置く。", "核となる出来事・対照・判断を選び、段落ごとのreader_gainを設計する。", "説明を保留するなら足場と回収先を指定する。偏りを残すなら必須情報に影響しないか確認する。", "本文を書き、reading-mapで注釈と根拠を照合する。", "読者が推論できる説明は削る案も残し、盲検比較で確かめる。"],
             "limitations": catalog["limitations"]}
    brief["research"] = research
    brief["research_lenses"] = lenses
    brief["workflow"] = [
        "読者と目的を決める。興味・可笑しさ・感動・理解・記憶を同じ達成指標にしない。",
        "結論の型を決める前に、この題材固有の事実を出典付きで集める。事実と筆者の読みを分ける。",
        "読者の予想と、それを維持または変更する材料を並べる。意外な材料がなければ逆説を捏造しない。",
        "読み物では、どこを詳しく見せ、どこを短く通るかを決める。手順では必要な情報を先に示す。",
        "本文と注釈を残す。語り手の態度は事実の捏造で作らず、説明を省く場合も状況理解の足場を残す。",
        "一つの改稿で何を変えたか記録する。複数要因が変わった稿を単一要因実験とは呼ばない。",
        "reading-mapの観測値と読者の評価を分ける。未回答を成功や0点へ変換しない。"
    ]
    out = Path(out)
    write_json(out / "brief.json", brief)
    lines = [f"# {safe(topic)}: 執筆前の設計", "", f"読者: {reader}", f"読後の変化: {purpose}", "", selected["constraint"], ""]
    for p in principles:
        lines += [f"## {p['question']}", "", p["action"], ""]
    lines += ["## 研究から素材と構成を選び直す", "", "以下は転用仮説であり、すべてを盛り込むチェックリストではない。", ""]
    for lens in lenses:
        lines += [f"### {lens['question']}", "", lens["action"], "", "参照ID: " + ", ".join(lens["studies"]), ""]
    lines += ["## 論文台帳: 結果と転用の限界", ""]
    for study in research["studies"]:
        lines += [f"### {study['id']}", "", f"[{study['citation']}]({study['url']})", "",
                  "閲覧範囲: " + study["access_scope"], "", "方法: " + study["design"], "",
                  "結果: " + study["finding"], "", "限界: " + study["limit"], "",
                  "転用仮説: " + study["transfer_hypothesis"], ""]
    lines += ["## 研究の適用範囲", ""] + ["- " + note for note in research["limitations"]] + [""]
    lines += ["## 原文と評価根拠", ""] + [f"- [{s['title']}]({s['url']}): {s['recognition']}（[評価元]({s['recognition_url']})）。対象範囲: {s['scope']}" for s in catalog["sources"]]
    lines += ["", "## 実行する順序", ""] + [f"{i}. {step}" for i, step in enumerate(brief["workflow"], 1)]
    (out / "brief.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return brief
