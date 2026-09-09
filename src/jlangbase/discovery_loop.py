"""Paragraph generation followed by reflection, with immutable world facts."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


def fingerprint(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             allow_nan=False).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def objects(value, fields):
    require(isinstance(value, list), "一覧はarrayで指定してください")
    for item in value:
        require(isinstance(item, dict), "一覧の要素はobjectです")
        require(all(nonempty(item.get(k)) for k in fields), "必須の文字列がありません: " + ", ".join(fields))


def questions(value):
    objects(value, ("id", "question"))
    require(len({q["id"] for q in value}) == len(value), "問いIDが重複しています")
    require(all(type(q.get("required")) is bool and type(q.get("resolved")) is bool for q in value),
            "問いにはrequired/resolvedのbooleanが必要です")
    require(all(not q["resolved"] or nonempty(q.get("resolution")) for q in value), "解決にはresolutionが必要です")


def narrator(value):
    require(isinstance(value, dict) and nonempty(value.get("view")), "暫定的な見方viewが必要です")
    require(isinstance(value.get("alternatives"), list) and
            all(nonempty(v) for v in value["alternatives"]), "対立する見方alternativesは文字列の一覧です")


def plan(value):
    require(isinstance(value, list) and all(nonempty(v) for v in value), "未執筆計画は文字列の一覧です")


def start(seed):
    require(isinstance(seed, dict), "seedはobjectです")
    require(nonempty(seed.get("question")) and nonempty(seed.get("destination")), "問いと遠い目的地が必要です")
    world = seed.get("WORLD_STATE")
    objects(world, ("id", "statement", "source"))
    require(len({f["id"] for f in world}) == len(world), "事実IDが重複しています")
    narrator(seed.get("NARRATOR_STATE"))
    questions(seed.get("open_questions"))
    plan(seed.get("remaining_plan"))
    from .reader_loop import initial_reader
    title = seed.get("title", seed["question"])
    require(nonempty(title), "titleは空でない文字列です")
    return {"schema_version": 2, "question": seed["question"], "destination": seed["destination"],
            "title": title, "READER_STATE": initial_reader(seed), "reading_history": [],
            "reader_review_version": 2,
            "WORLD_STATE": deepcopy(world), "world_hash": fingerprint(world),
            "NARRATOR_STATE": deepcopy(seed["NARRATOR_STATE"]),
            "open_questions": deepcopy(seed["open_questions"]),
            "remaining_plan": deepcopy(seed["remaining_plan"]), "paragraphs": [], "history": [],
            "status": "active", "quality_improved": None}


def check_state(state):
    require(isinstance(state, dict) and state.get("schema_version") in {1, 2}, "未対応のstateです")
    require(fingerprint(state.get("WORLD_STATE")) == state.get("world_hash"), "WORLD_STATEが変更されています")
    require(state.get("status") == "active", "停止済みstateは継続できません。履歴を残して別セッションを開始してください")
    require(isinstance(state.get("paragraphs"), list) and isinstance(state.get("history"), list), "不正な履歴です")
    narrator(state.get("NARRATOR_STATE"))
    questions(state.get("open_questions"))
    plan(state.get("remaining_plan"))
    if state["schema_version"] == 2:
        from .reader_loop import validate_reader
        require(type(state.get("reader_review_version", 1)) is int and
                state.get("reader_review_version", 1) in {1, 2}, "未対応の読解判断バージョンです")
        require(nonempty(state.get("title")), "titleが必要です")
        require(isinstance(state.get("reading_history"), list) and
                len(state["reading_history"]) == len(state["paragraphs"]), "読解判断の履歴が不正です")
        validate_reader(state.get("READER_STATE"), state["paragraphs"])


def next_request(state):
    check_state(state)
    from .purpose import context
    return {"state_hash": fingerprint(state), "stage": "write_one_paragraph",
            "project_purpose": context(),
            **({"title": state["title"], "READER_STATE": deepcopy(state["READER_STATE"]),
                "reader_review_version": state.get("reader_review_version", 1),
                "reader_instruction": "説明済みは理解済みではない。現在の疑問と未説明の前提を見て、次の段落の役割を選ぶ。"}
               if state["schema_version"] == 2 else {}),
            "question": state["question"], "destination": state["destination"],
            "WORLD_STATE": deepcopy(state["WORLD_STATE"]),
            "NARRATOR_STATE": deepcopy(state["NARRATOR_STATE"]),
            "open_questions": deepcopy(state["open_questions"]),
            "remaining_plan": deepcopy(state["remaining_plan"]),
            "written_paragraphs": list(state["paragraphs"]),
            "instructions": [
                "次の本文を1段落だけ書く。全文の結論や感情曲線は先に完成させない。",
                "WORLD_STATEを変更せず、語り手の認識と確認済みの事実を区別する。",
                "毎段落に発見や逆転を強制しない。必要なら具体的な場面や間を書く。",
                "本文のみを返す。発見の抽出と再計画は、この本文を書いた後の別工程で行う。"]}


def reflection_request(state, paragraph, reading_review=None):
    request = next_request(state)
    if state["schema_version"] == 2:
        from .reader_loop import validate_review
        require(validate_review(state, reading_review) == paragraph,
                "採用された本文から発見を抽出してください")
    request.update(stage="reflect_after_writing", paragraph=paragraph)
    request["instructions"] = [
        "いま書かれた段落から発見を抽出する。最初の計画への適合ではなく、見方がどう揺さぶられたかを見る。",
        "新しい発見には本文の短いquoteを付ける。言い換えだけならkind=restatementとする。",
        "NARRATOR_STATEに相当するnarratorと未執筆のremaining_planを更新する。既出本文と事実台帳は変更しない。",
        "対立する見方を消して早合点しない。更新しないなら同じnarratorを返してよい。",
        "事実の疑義はfact_reviewへ。新しい確認が必要ならdecision=needs_evidence。",
        "新しい発見も必要な準備も残らなければstalled。到達したならfinishとarrivalを示し、任意の問いは残す。"]
    request["response_contract"] = {
        "state_hash": request["state_hash"], "paragraph": paragraph, "fact_ids": [],
        "fact_review": {"reviewer": "担当者またはモデル識別子", "status": "consistent|conflict|uncertain", "issues": []},
        "discoveries": [{"id": "新しいID", "quote": "本文の引用", "observation": "発見", "kind": "reframe|counterexample|question|deepen|restatement"}],
        "narrator": {"view": "暫定見解", "alternatives": ["残る対立"]},
        "update_reason": "変更理由", "update_discovery_ids": [],
        "open_questions": deepcopy(state["open_questions"]), "remaining_plan": [],
        "decision": "continue|finish|stalled|needs_evidence", "reason": "判断理由",
        "preparation": "発見なしで進む場合の必要性", "arrival": "終了時の到達内容"}
    if state["schema_version"] == 2:
        request["reading_review"] = deepcopy(reading_review)
        request["response_contract"]["reading_review"] = deepcopy(reading_review)
        request["instructions"].append("reading_reviewは変更せず返す。残る読者の疑問も考慮して続きを再計画する。")
    return request


def advance(state, response):
    check_state(state)
    require(isinstance(response, dict), "応答はobjectです")
    require(response.get("state_hash") == fingerprint(state), "古い状態に対する応答です")
    require(not any(k in response for k in ("WORLD_STATE", "world_hash", "paragraphs", "history", "destination", "question")),
            "固定情報と既出本文は応答で変更できません")
    paragraph = response.get("paragraph")
    require(nonempty(paragraph) and "\n" not in paragraph.strip() and "\r" not in paragraph.strip(), "本文は改行を含まない1段落です")
    if state["schema_version"] == 2:
        from .reader_loop import validate_review
        require(validate_review(state, response.get("reading_review")) == paragraph,
                "本文と読解判断の採用案が一致しません")
    decision = response.get("decision")
    require(decision in {"continue", "finish", "stalled", "needs_evidence"}, "不正なdecisionです")
    require(nonempty(response.get("reason")), "判断理由が必要です")
    refs = response.get("fact_ids")
    require(isinstance(refs, list) and all(isinstance(v, str) for v in refs), "fact_idsは文字列の一覧です")
    require(set(refs) <= {f["id"] for f in state["WORLD_STATE"]}, "未登録の事実です")
    review = response.get("fact_review")
    require(isinstance(review, dict) and nonempty(review.get("reviewer")), "事実レビュー担当の識別子が必要です")
    require(review.get("status") in {"consistent", "conflict", "uncertain"}, "事実レビュー状態が不正です")
    require(isinstance(review.get("issues"), list) and all(nonempty(v) for v in review["issues"]), "issuesは文字列の一覧です")
    require(review["status"] != "consistent" or not review["issues"], "疑義があるレビューをconsistentにはできません")
    # Block publication of an uncertain paragraph, but retain the proposal for audit.
    if review["status"] != "consistent" or decision == "needs_evidence":
        result = deepcopy(state)
        result["status"] = "fact_conflict" if review["status"] == "conflict" else "needs_evidence"
        result["history"].append({"accepted": False, "response": deepcopy(response)})
        return result
    discoveries = response.get("discoveries")
    objects(discoveries, ("id", "quote", "observation", "kind"))
    known = {d["id"] for h in state["history"] if h.get("accepted") for d in h["response"]["discoveries"]}
    ids = [d["id"] for d in discoveries]
    require(len(set(ids)) == len(ids) and not known.intersection(ids), "発見IDが重複しています")
    for d in discoveries:
        require(d["quote"] in paragraph, "発見の引用が段落にありません")
        require(d["kind"] in {"reframe", "counterexample", "question", "deepen", "restatement"}, "不正な発見種別です")
    updated = response.get("narrator")
    narrator(updated)
    meaningful = {d["id"] for d in discoveries if d["kind"] != "restatement"}
    if updated != state["NARRATOR_STATE"]:
        links = response.get("update_discovery_ids")
        require(isinstance(links, list) and all(isinstance(v, str) for v in links) and links and set(links) <= meaningful,
                "認識の更新には今回の新しい発見IDが必要です")
        require(nonempty(response.get("update_reason")), "認識の更新理由が必要です")
    pending = response.get("open_questions")
    questions(pending)
    previous = {q["id"]: q for q in state["open_questions"]}
    current = {q["id"]: q for q in pending}
    require(previous.keys() <= current.keys(), "既存の問いを削除せず、解決や残存を記録してください")
    for key, old in previous.items():
        require(current[key]["question"] == old["question"] and current[key]["required"] == old["required"],
                "既存の問いの内容・必須性は変更できません。派生する問いを追加してください")
    resolved = any(q["resolved"] and not previous.get(key, {}).get("resolved", True) for key, q in current.items())
    remainder = response.get("remaining_plan")
    plan(remainder)
    if decision == "finish":
        require(nonempty(response.get("arrival")), "終了には到達内容arrivalが必要です")
        require(not any(q["required"] and not q["resolved"] for q in pending), "解決必須の問いが残っています")
        require(not remainder, "完了時に未執筆計画は残せません")
    if decision == "continue":
        require(bool(remainder), "継続には次の計画が必要です")
        if not meaningful and not resolved and not nonempty(response.get("preparation")):
            decision = "stalled"
    result = deepcopy(state)
    result.update(NARRATOR_STATE=deepcopy(updated), open_questions=deepcopy(pending),
                  remaining_plan=list(remainder), status={"continue": "active", "finish": "complete"}.get(decision, decision))
    result["paragraphs"].append(paragraph.strip())
    if state["schema_version"] == 2:
        from .reader_loop import update_reader
        result["READER_STATE"] = update_reader(state, response["reading_review"])
        result["reading_history"].append(deepcopy(response["reading_review"]))
    result["history"].append({"accepted": True, "response": deepcopy(response),
                              "effective_decision": decision, "narrator_before": deepcopy(state["NARRATOR_STATE"])})
    return result


def run_loop(state, writer, reflector, max_steps, reviewer=None, function_reviewer=None):
    """Callbacks perform generation; budget exhaustion never means completion."""
    require(type(max_steps) is int and max_steps > 0, "安全上限max_stepsは正の整数です")
    current = deepcopy(state)
    if current.get("schema_version") == 2:
        require(callable(reviewer), "v2には読解判断を返すreviewerが必要です")
        if current.get("reader_review_version", 1) == 2:
            require(callable(function_reviewer), "読解版2には修正前の文の働きを読むfunction_reviewerが必要です")
    for _ in range(max_steps):
        if current.get("status") != "active":
            return current
        paragraph = writer(next_request(current))
        require(nonempty(paragraph), "writerは本文の文字列を返してください")
        reading_review = None
        if current["schema_version"] == 2:
            from .reader_loop import reading_request, validate_review
            draft = paragraph
            function_review = None
            if current.get("reader_review_version", 1) == 2:
                from .reader_loop import function_request
                function_review = function_reviewer(function_request(current, draft))
            reading_review = reviewer(reading_request(current, draft, function_review))
            paragraph = validate_review(current, reading_review)
            if current.get("reader_review_version", 1) == 2:
                require(reading_review.get("function_review") == function_review, "reviewerは修正前の働きの記録を変更できません")
            require(reading_review["draft"] == draft, "reviewerは元の草案を改変できません")
        response = reflector(reflection_request(current, paragraph, reading_review))
        if current["schema_version"] == 2:
            require(isinstance(response, dict) and response.get("reading_review") == reading_review,
                    "reflectorは読解判断を改変できません")
        require(isinstance(response, dict) and response.get("paragraph") == paragraph,
                "reflectorは生成された段落を改変できません")
        current = advance(current, response)
    if current["status"] == "active":
        current["status"] = "budget_exhausted"
    return current


def save_new(path, value):
    """Exclusive creation prevents an old checkpoint from being overwritten."""
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(payload)
