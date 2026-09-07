"""Observable document structure, without inferring rhetorical intent."""
from collections import Counter
import re
import statistics
from .analysis import split_sentences


def structure_metrics(text):
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if b.strip()]
    headings, paragraphs, lists = [], [], 0
    in_fence = False
    for block in blocks:
        prose = []
        for line in block.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            heading = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if heading:
                headings.append({"level": len(heading[1]), "text": heading[2]})
            else:
                if re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s)", line):
                    lists += 1
                prose.append(line)
        if "\n".join(prose).strip():
            paragraphs.append("\n".join(prose).strip())
    lengths = [len(p) for p in paragraphs]
    sentence_counts = [len(split_sentences(p)) for p in paragraphs]
    total = sum(lengths)
    return {
        "paragraph_count": len(paragraphs), "heading_count": len(headings), "headings": headings,
        "heading_level_counts": dict(sorted(Counter(h["level"] for h in headings).items())),
        "heading_level_jumps": sum(b["level"] > a["level"] + 1 for a, b in zip(headings, headings[1:])),
        "list_item_count": lists, "paragraph_lengths": lengths,
        "sentences_per_paragraph": sentence_counts,
        "mean_paragraph_length": statistics.mean(lengths) if lengths else 0,
        "paragraph_length_cv": statistics.pstdev(lengths) / statistics.mean(lengths) if lengths and total else 0,
        "first_paragraph_share": lengths[0] / total if total else 0,
        "last_paragraph_share": lengths[-1] / total if total else 0,
    }


def aggregate_structure(items):
    rows = [item["structure"] for item in items]
    lengths = [v for row in rows for v in row["paragraph_lengths"]]
    counts = [v for row in rows for v in row["sentences_per_paragraph"]]
    return {
        "document_count": len(rows),
        "paragraph_count": sum(r["paragraph_count"] for r in rows),
        "heading_count": sum(r["heading_count"] for r in rows),
        "heading_level_jumps": sum(r["heading_level_jumps"] for r in rows),
        "list_item_count": sum(r["list_item_count"] for r in rows),
        "mean_paragraph_count": statistics.mean(r["paragraph_count"] for r in rows) if rows else 0,
        "mean_paragraph_length": statistics.mean(lengths) if lengths else 0,
        "paragraph_length_distribution": dict(sorted(Counter(lengths).items())),
        "sentences_per_paragraph_distribution": dict(sorted(Counter(counts).items())),
        "mean_first_paragraph_share": statistics.mean(r["first_paragraph_share"] for r in rows) if rows else 0,
        "mean_last_paragraph_share": statistics.mean(r["last_paragraph_share"] for r in rows) if rows else 0,
        "mean_paragraph_length_cv": statistics.mean(r["paragraph_length_cv"] for r in rows) if rows else 0,
        "notes": ["段落は空行で区切ります。MarkdownのATX見出しと箇条書きを検出し、コードフェンス内は段落集計から除きます。",
                  "段落の役割、論旨、主張と根拠の妥当性は機械判定していません。構成の良否は本文と合わせて確認してください。"],
    }
