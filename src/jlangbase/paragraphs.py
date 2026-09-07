"""Line-addressable Markdown blocks for local editorial review."""
import re
from .analysis import split_sentences


def paragraphs(text):
    result, buffer, start = [], [], None
    fence, frontmatter = None, False

    def flush():
        nonlocal buffer, start
        if buffer:
            raw = "\n".join(buffer)
            kind = "quote" if all(s.lstrip().startswith(">") for s in buffer) else "list" if re.match(r"\s*(?:[-*+] |\d+[.)] )", buffer[0]) else "prose"
            content = re.sub(r"(?m)^\s*>\s?", "", raw) if kind == "quote" else raw
            sentences = split_sentences(content)
            result.append(dict(id=len(result) + 1, line=start, end_line=start + len(buffer) - 1,
                               kind=kind, text=raw, sentences=sentences, sentence_lengths=[len(s) for s in sentences]))
            buffer, start = [], None

    for index, line in enumerate(text.splitlines(), 1):
        if index == 1 and line.strip() == "---":
            frontmatter = True
            continue
        if frontmatter:
            if line.strip() in {"---", "..."}:
                frontmatter = False
            continue
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            flush()
            fence = marker[1]
            continue
        if not line.strip() or re.match(r"^\s{0,3}#{1,6}\s", line) or re.fullmatch(r"\s*(?:[-*_]\s*){3,}", line):
            flush()
            continue
        if start is None:
            start = index
        buffer.append(line)
    flush()
    return result
