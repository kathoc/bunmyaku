"""Traceable editorial selection and recomposition; no pleasure score."""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import re

from .discovery_loop import save_new
from .paragraphs import paragraphs as parse_paragraphs


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             allow_nan=False).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def indexed(items, label):
    require(isinstance(items, list), label + " must be a list")
    require(all(isinstance(x, dict) and nonempty(x.get("id")) for x in items),
            label + " needs nonempty IDs")
    ids = [x["id"] for x in items]
    require(len(set(ids)) == len(ids), label + " has duplicate IDs")
    return {x["id"]: x for x in items}


def seal(data):
    result = deepcopy(data)
    result["hash"] = digest(data)
    return result


def check(data, stage):
    require(isinstance(data, dict) and data.get("stage") == stage, "Wrong editorial stage")
    require(data.get("hash") == digest({k: v for k, v in data.items() if k != "hash"}),
            "Editorial request changed; prepare it again")


def prepare(text, brief):
    require(nonempty(text), "Empty manuscript")
    require(isinstance(brief, dict), "brief must be an object")
    require(all(nonempty(brief.get(k)) for k in ("title", "reader", "promise")),
            "brief needs title, reader and promise")
    require("\n" not in brief["title"] and "\r" not in brief["title"], "Title must be one line")
    obligations = indexed(brief.get("required_points"), "required_points")
    require(bool(obligations) and all(nonempty(x.get("meaning")) for x in obligations.values()),
            "Explain the meanings that must survive editing")
    units = [{"id": f"u{i:03}", "kind": block["kind"], "text": block["text"],
              "source": f"manuscript lines {block['line']}-{block['end_line']}"}
             for i, block in enumerate(parse_paragraphs(text), 1)]
    # The paragraph parser excludes code fences. Keep these opaque and exact.
    fence, code = None, []
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            code.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                units.append({"id": f"c{len(units):03}", "kind": "code", "text": "\n".join(code),
                              "source": "manuscript code fence"})
                fence, code = None, []
        elif marker:
            fence, code = marker[1], [line]
    require(fence is None, "Close the code fence before editorial selection")
    materials = brief.get("materials", [])
    indexed(materials, "materials")
    for material in materials:
        require(nonempty(material.get("text")) and nonempty(material.get("source")),
                "New material needs text and a source")
        units.append({**material, "kind": "material"})
    indexed(units, "source units")
    require(bool(units), "No editorial material")
    instruction_names = ("editorial-workflow.md", "editorial-meaning.md", "editorial-register.md",
                         "editorial-voice.md", "editorial-sections.md", "editorial-explanation.md",
                         "project-purpose.md")
    instructions = "\n\n".join(files("jlangbase").joinpath("resources", name).read_text(encoding="utf-8")
                                 for name in instruction_names)
    return seal({"stage": "selection", "editorial_version": 4, "source_hash": digest(text), "source_text": text,
                 "brief": brief, "units": units,
                 "instructions": instructions})


def select(request, decisions):
    check(request, "selection")
    strategy = None
    if request.get("editorial_version", 1) >= 2:
        require(isinstance(decisions, dict), "Version 2 expects {strategy, decisions}; see editorial-workflow.md")
        strategy = decisions.get("strategy")
        decisions = decisions.get("decisions")
    require(isinstance(decisions, list), "decisions must be a list")
    require(all(isinstance(d, dict) for d in decisions), "decisions must contain objects")
    ids = [d.get("source_id") for d in decisions]
    known = {u["id"]: u for u in request["units"]}
    require(all(isinstance(i, str) for i in ids), "Missing source_id")
    require(len(ids) == len(set(ids)) and set(ids) == set(known),
            "Decide exactly once for every source unit")
    for d in decisions:
        require(d.get("action") in {"keep", "compress", "move", "drop"}, "Unknown editorial action")
        require(nonempty(d.get("reason")) and nonempty(d.get("loss")), "Record both reason and loss")
        require(known[d["source_id"]]["kind"] != "code" or d["action"] != "compress",
                "Code is opaque: keep, move or explicitly drop it")
    if request.get("editorial_version", 1) >= 2:
        from .editorial_strategy import validate_strategy
        validate_strategy(request, strategy, decisions)
    return seal({"stage": "composition", "selection": request, "decisions": decisions,
                 "strategy": strategy,
                 "response_contract": {
                     "request_hash": "Use this composition object's hash",
                     "paragraphs": [{"id": "v001", "text": "display paragraph", "source_ids": ["u001"],
                                     "role": "purpose here", "reader_gain": "what becomes clear"}],
                     "coverage": [{"requirement_id": "from brief", "paragraph_id": "v001",
                                   "quote": "exact excerpt", "reason": "why the requirement survives"}],
                     "cadence": {"mode": "text_inference", "sequences": [],
                                 "unchanged_reason": "or specify setup/departure/settling references with effect/alternative/choice_reason"},
                     "reader_questions": [],
                     "meaning_coverage": [],
                     "reading_path": [],
                     **({"paragraph_boundaries": [{"paragraph_id": "v001", "role": "purpose here",
                                                    "reason": "why break here"}],
                         "section_layout": [{"heading_id": "heading block ID", "draft_heading": "provisional heading",
                                             "body_ids": ["v001"], "reconsideration": "decision after writing body"}]}
                        if request.get("editorial_version", 1) >= 3 else {}),
                     **({"explanation_review": {"examples": [], "no_examples_reason": "Explain why plain prose suffices, or record candidates using editorial-explanation.md"},
                         "reader_checks": [{"id": "r1", "target": {"paragraph_id": "v001", "quote": "exact excerpt"},
                                            "question": "Ask the reader to explain the main idea",
                                            "expected_meaning": "Meaning supported by the target excerpt",
                                            "misunderstanding": "What must not be inferred", "example_ids": []}]}
                        if request.get("editorial_version", 1) >= 4 else {})}})


def accept(composition, response):
    check(composition, "composition")
    request = composition["selection"]
    check(request, "selection")
    require(isinstance(response, dict) and response.get("request_hash") == composition["hash"],
            "Response belongs to a different composition request")
    blocks = response.get("paragraphs")
    by_id = indexed(blocks, "paragraphs")
    require(bool(blocks), "Empty revision")
    actions = {d["source_id"]: d["action"] for d in composition["decisions"]}
    sources = {u["id"]: u for u in request["units"]}
    used = set()
    for block in blocks:
        require(all(nonempty(block.get(k)) for k in ("text", "role", "reader_gain")), "Explain each display block")
        refs = block.get("source_ids")
        require(isinstance(refs, list) and bool(refs) and all(isinstance(r, str) for r in refs),
                "Every display block needs source IDs")
        require(len(set(refs)) == len(refs), "Duplicate source reference")
        require(all(r in actions and actions[r] != "drop" for r in refs), "Unknown or discarded source referenced")
        used.update(refs)
    retained = {k for k, v in actions.items() if v != "drop"}
    require(used == retained, "Retained source omitted without a drop decision")
    for uid in retained:
        if actions[uid] in {"keep", "move"}:
            combined = "\n\n".join(b["text"] for b in blocks if uid in b["source_ids"])
            require(sources[uid]["text"] in combined, "keep/move changed text; use compress with a reason")

    def reference(ref):
        require(isinstance(ref, dict) and ref.get("paragraph_id") in by_id, "Unknown display paragraph")
        require(nonempty(ref.get("quote")) and ref["quote"] in by_id[ref["paragraph_id"]]["text"],
                "Quote must occur in the referenced paragraph")
        return (list(by_id).index(ref["paragraph_id"]),
                by_id[ref["paragraph_id"]]["text"].index(ref["quote"]))

    coverage = response.get("coverage")
    require(isinstance(coverage, list) and all(isinstance(c, dict) for c in coverage), "Need coverage records")
    requirements = {p["id"] for p in request["brief"]["required_points"]}
    covered = [c.get("requirement_id") for c in coverage]
    require(all(isinstance(c, str) for c in covered), "Missing requirement_id")
    require(len(covered) == len(set(covered)) and set(covered) == requirements, "Account for every required meaning")
    for item in coverage:
        reference(item)
        require(nonempty(item.get("reason")), "Explain preservation; a quote alone is not evidence of entailment")
    cadence = response.get("cadence")
    require(isinstance(cadence, dict) and cadence.get("mode") == "text_inference", "Do not claim acoustic measurement")
    sequences = cadence.get("sequences")
    require(isinstance(sequences, list), "cadence.sequences must be a list")
    if not sequences:
        require(nonempty(cadence.get("unchanged_reason")), "Explain why no cadence change is needed")
    for item in sequences:
        require(isinstance(item, dict), "Invalid cadence sequence")
        positions = [reference(item.get(k)) for k in ("setup", "departure", "settling")]
        require(positions[0] < positions[1] < positions[2], "Cadence references must follow reading order")
        require(all(nonempty(item.get(k)) for k in ("effect", "alternative", "choice_reason")),
                "Explain the cadence choice and its alternative")
    questions = response.get("reader_questions")
    require(isinstance(questions, list) and all(nonempty(q) for q in questions), "reader_questions must be strings")
    if request.get("editorial_version", 1) >= 2:
        from .editorial_strategy import validate_reading_path
        validate_reading_path(composition, response)
    if request.get("editorial_version", 1) >= 3:
        from .editorial_sections import validate_layout
        validate_layout(response)
    if request.get("editorial_version", 1) >= 4:
        from .editorial_explanation import validate_explanation
        validate_explanation(composition, response)
    markdown = "# " + request["brief"]["title"] + "\n\n" + "\n\n".join(b["text"] for b in blocks) + "\n"
    prose = parse_paragraphs(markdown)
    return {"status": "editorial_candidate", "quality_improved": None,
            "source_hash": request["source_hash"], "composition_hash": composition["hash"],
            "decisions": composition["decisions"], "strategy": composition.get("strategy"),
            "response": response, "markdown": markdown,
            **({"reader_evaluation": {"status": "pending", "article_hash": digest(markdown),
                                      "answers": None}}
               if request.get("editorial_version", 1) >= 4 else {}),
            "surface_observations": {"paragraph_characters": [len(p["text"]) for p in prose],
                                     "sentence_characters": [p["sentence_lengths"] for p in prose],
                                     "actions": dict(Counter(actions.values()))},
            "limits": ["References and text retention checked; meaning preservation is not independently verified.",
                       "Lengths are not mora counts or pleasure scores. No audio was generated or heard.",
                       "Hashes detect accidental mismatch, not malicious rewriting of the complete request."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Select material, then recompose for the reader")
    sub = parser.add_subparsers(dest="command", required=True)
    for command, option in (("editor-request", "brief"), ("editor-select", "decisions"), ("editor-apply", "response")):
        p = sub.add_parser(command)
        p.add_argument("input", type=Path)
        p.add_argument("--" + option, type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    def read(path):
        return json.loads(path.read_text(encoding="utf-8-sig"))
    if args.command == "editor-request":
        result = prepare(args.input.read_text(encoding="utf-8-sig"), read(args.brief))
    elif args.command == "editor-select":
        result = select(read(args.input), read(args.decisions))
    else:
        result = accept(read(args.input), read(args.response))
    save_new(args.out, result)
    print(json.dumps({"output": str(args.out), "stage": result.get("stage", result.get("status"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
