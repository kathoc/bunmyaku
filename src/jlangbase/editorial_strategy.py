"""Meaning-level editorial contracts, not automatic semantic judgements."""


def need(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def rows(value, label):
    need(isinstance(value, list) and all(isinstance(x, dict) for x in value), label + " must be objects")
    return value


def strings(value, label):
    need(isinstance(value, list) and all(text(x) for x in value), label + " must be strings")
    need(len(value) == len(set(value)), label + " has duplicates")
    return value


def fields(row, names, label):
    need(all(text(row.get(k)) for k in names), label + " needs " + ", ".join(names))


def unique(items, label):
    result = {}
    for item in rows(items, label):
        fields(item, ("id",), label)
        need(item["id"] not in result, label + " has duplicate IDs")
        result[item["id"]] = item
    return result


def validate_strategy(request, strategy, decisions):
    need(isinstance(strategy, dict), "Version 2 needs an article-level strategy before rewriting")
    fields(strategy, ("thesis", "reader_destination", "selection_principle"), "strategy")
    sources = {u["id"]: u for u in request["units"]}
    actions = {d["source_id"]: d["action"] for d in decisions}
    sections = unique(strategy.get("sections"), "sections")
    need(bool(sections), "State the article's questions and answers")
    earlier = set()
    for sid, section in sections.items():
        fields(section, ("question", "answer", "contribution"), "section")
        deps = strings(section.get("depends_on"), "section depends_on")
        need(set(deps) <= earlier, "Section dependencies must precede the section")
        earlier.add(sid)
    meanings = unique(strategy.get("meanings"), "meanings")
    need(bool(meanings), "Identify meanings, not only paragraphs")
    represented, active_sections = set(), set()
    for mid, item in meanings.items():
        fields(item, ("source_id", "quote", "meaning", "reason", "loss",
                      "alternative", "why_not_alternative"), "meaning")
        source = item["source_id"]
        need(source in sources and item["quote"] in sources[source]["text"], "Meaning needs an exact source quote")
        need(item.get("role") in {"claim", "evidence", "example", "qualification", "voice", "bridge", "echo"},
             "Unknown meaning role")
        need(item.get("action") in {"retain", "recast", "omit"}, "Unknown meaning action")
        deps = strings(item.get("depends_on"), "meaning depends_on")
        need(mid not in deps and set(deps) <= set(meanings), "Unknown or self-referential meaning dependency")
        if actions[source] == "drop":
            need(item["action"] == "omit", "Dropped material cannot retain a meaning")
        if actions[source] in {"keep", "move"}:
            need(item["action"] == "retain", "Exact retention cannot omit or recast its meaning")
        if item["action"] != "omit":
            need(item.get("section_id") in sections, "Retained meaning needs a section")
            active_sections.add(item["section_id"])
            need(all(meanings[d].get("action") != "omit" for d in deps), "A retained meaning lost its prerequisite")
        represented.add(source)
    need(represented == set(sources), "Every source needs meaning-level selection, including omissions")
    need(active_sections == set(sections), "Every planned section needs retained material")
    for source, action in actions.items():
        if action != "drop":
            need(any(m["source_id"] == source and m["action"] != "omit" for m in meanings.values()),
                 "Use drop if all meanings from a source are omitted")
    # Dependencies must form a DAG, but need not dictate paragraph length or order.
    pending = {mid: set(m["depends_on"]) for mid, m in meanings.items()}
    while pending:
        ready = {mid for mid, deps in pending.items() if not deps}
        need(bool(ready), "Meaning dependencies contain a cycle")
        pending = {mid: deps - ready for mid, deps in pending.items() if mid not in ready}


def validate_reading_path(composition, response):
    strategy = composition["strategy"]
    meanings = {m["id"]: m for m in strategy["meanings"]}
    blocks = response["paragraphs"]
    by_id = {b["id"]: b for b in blocks}
    order = {b["id"]: i for i, b in enumerate(blocks)}

    def ref(value):
        need(isinstance(value, dict), "A reading reference must be an object")
        fields(value, ("paragraph_id", "quote"), "reading reference")
        pid = value["paragraph_id"]
        need(pid in by_id and value["quote"] in by_id[pid]["text"], "Reading reference quote not found")
        return order[pid]

    coverage = rows(response.get("meaning_coverage"), "meaning_coverage")
    retained = {mid for mid, m in meanings.items() if m["action"] != "omit"}
    covered = set()
    for item in coverage:
        fields(item, ("meaning_id", "reason"), "meaning coverage")
        mid = item["meaning_id"]
        need(mid in retained and mid not in covered, "Unknown, omitted or duplicate meaning coverage")
        ref(item)
        need(meanings[mid]["source_id"] in by_id[item["paragraph_id"]]["source_ids"],
             "Meaning coverage must refer to its source material")
        covered.add(mid)
    need(covered == retained, "Every retained meaning needs a destination quote")

    path = rows(response.get("reading_path"), "reading_path")
    ids = [item.get("paragraph_id") for item in path]
    need(ids == [b["id"] for b in blocks], "reading_path must follow every display block in reading order")
    for item in path:
        fields(item, ("focus", "reason"), "reading step")
        pid = item["paragraph_id"]
        mode = item.get("relation")
        need(mode in {"orient", "advance", "unpack", "echo", "bridge", "qualify", "close"},
             "Unknown reading relation")
        carries = rows(item.get("carry_from"), "carry_from")
        for carry in carries:
            need(ref(carry) < order[pid], "Carry meaning from an earlier block")
        if not carries:
            fields(item, ("entry_reason",), "A fresh entry")
        strings(item.get("introduced"), "introduced concepts")
        strings(item.get("settles"), "settled concepts")
        if mode == "echo":
            echo = item.get("echo")
            need(isinstance(echo, dict) and bool(carries), "An echo needs an earlier meaning")
            fields(echo, ("previous_meaning", "current_meaning", "shift", "reader_effect",
                          "claim_delta", "support_reason"), "echo")
            current = echo.get("current")
            ref(current)
            need(current["paragraph_id"] == pid, "Echo quote must belong to this block")
            need(echo.get("entailment") in {"same_claim", "supported_inference"},
                 "An uncertain paraphrase needs evidence before acceptance")
            support = strings(echo.get("support_meaning_ids"), "echo support")
            need(set(support) <= retained, "Echo support must be retained source meanings")
            if echo["entailment"] == "supported_inference":
                need(bool(support), "A change of viewpoint adding a claim needs explicit support")

