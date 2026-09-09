"""Explanation decisions and attributed reader reports, not comprehension scores."""
from .editorial_strategy import fields, need, rows, strings, text, unique


def validate_explanation(composition, response):
    blocks = {b["id"]: b for b in response["paragraphs"]}
    order = {pid: i for i, pid in enumerate(blocks)}

    def reference(value):
        need(isinstance(value, dict), "Explanation reference must be an object")
        fields(value, ("paragraph_id", "quote"), "explanation reference")
        pid = value["paragraph_id"]
        need(pid in blocks and value["quote"] in blocks[pid]["text"], "Explanation quote not found")
        return order[pid], blocks[pid]["text"].index(value["quote"])

    review = response.get("explanation_review")
    need(isinstance(review, dict), "Version 4 needs explanation_review")
    examples = unique(review.get("examples"), "examples")
    if not examples:
        fields(review, ("no_examples_reason",), "No example decision")
    source_ids = {u["id"] for u in composition["selection"]["units"]}
    for item in examples.values():
        fields(item, ("goal", "plain", "candidate", "mapping", "setup_reason",
                      "misreading", "choice_reason"), "example decision")
        refs = strings(item.get("source_ids"), "example source_ids")
        need(bool(refs) and set(refs) <= source_ids, "Example needs known source IDs")
        need(item.get("kind") in {"direct_example", "analogy", "expressive_metaphor"}, "Unknown example kind")
        need(item.get("choice") in {"plain", "example", "omit"}, "Unknown example choice")
        familiarity = item.get("familiarity")
        need(isinstance(familiarity, dict), "Explain source familiarity")
        need(familiarity.get("status") in {"known", "unknown", "explained"}, "Unknown familiarity status")
        fields(familiarity, ("basis",), "familiarity")
        if item["choice"] != "omit":
            position = reference(item.get("output"))
            need(bool(set(refs) & set(blocks[item["output"]["paragraph_id"]]["source_ids"])),
                 "Example output must refer to its source")
            if item["choice"] == "example":
                need(reference(item.get("return_to_topic")) >= position,
                     "Return to the topic at or after the example")
                if item["kind"] != "expressive_metaphor":
                    need(familiarity["status"] != "unknown", "Use plain explanation when source knowledge is unknown")
    checks = unique(response.get("reader_checks"), "reader_checks")
    need(bool(checks), "Prepare a reader check without inventing an answer")
    checked = set()
    for item in checks.values():
        fields(item, ("question", "expected_meaning", "misunderstanding"), "reader check")
        reference(item.get("target"))
        refs = strings(item.get("example_ids"), "reader check example_ids")
        need(set(refs) <= set(examples), "Reader check references unknown examples")
        checked.update(refs)
    need({key for key, item in examples.items() if item["choice"] == "example"} <= checked,
         "Every selected example needs a reader check")


def reader_feedback(candidate, report):
    from .editorial import digest
    need(isinstance(candidate, dict) and candidate.get("status") == "editorial_candidate",
         "Reader feedback needs an editorial candidate")
    need(text(candidate.get("markdown")), "Candidate needs markdown")
    need(isinstance(report, dict), "Reader report must be an object")
    article_hash = digest(candidate["markdown"])
    need(report.get("article_hash") == article_hash, "Reader report belongs to another article version")
    need(report.get("origin") in {"reader", "model"}, "Report origin must be reader or model")
    fields(report, ("observation_source",), "reader report")
    response = candidate.get("response")
    need(isinstance(response, dict), "Candidate needs response")
    checks = unique(response.get("reader_checks"), "reader_checks")
    need(bool(checks), "Candidate has no reader checks")
    answers = rows(report.get("answers"), "answers")
    need(bool(answers), "Do not record an unanswered check as reader feedback")
    seen = set()
    for item in answers:
        fields(item, ("check_id", "answer"), "reader answer")
        cid = item["check_id"]
        need(cid in checks and cid not in seen, "Unknown or duplicate reader check")
        seen.add(cid)
    return {"status": "reader_reported" if report["origin"] == "reader" else "model_simulation",
            "article_hash": article_hash, "composition_hash": candidate.get("composition_hash"),
            "origin": report["origin"], "observation_source": report["observation_source"],
            "checks": list(checks.values()), "answers": answers,
            "unanswered_check_ids": [cid for cid in checks if cid not in seen],
            "quality_improved": None, "limits": [
                "Origin is supplied by the recorder, not independently authenticated.",
                "Answers are observations, not an automatic comprehension or improvement score."]}
