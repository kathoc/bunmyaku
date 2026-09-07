"""Expression counts and document coverage are separate measurements."""
from collections import Counter

KINDS = ("ngram", "ending", "opening", "transition", "formula")
TRANSITIONS = ("しかし", "そして", "また", "ただし", "一方", "つまり", "例えば", "そのため", "そこで", "ところが", "それでも")
PARTICLES = set("はがをにへとでのもやかねよぞさ")


def usable(expression, token_length, filter_noise=True):
    if not filter_noise:
        return True
    return (any(c.isalpha() for c in expression)
            and not (token_length == 1 and expression in PARTICLES)
            and "http" not in expression.lower() and "www." not in expression.lower()
            and not expression.isnumeric())


def extract(item, filter_noise=True):
    counts = Counter()

    def add(kind, tokens):
        expr = "".join(t["surface"] for t in tokens)
        if usable(expr, len(tokens), filter_noise):
            counts[kind, expr, len(tokens)] += 1

    for sentence in item["sentences"]:
        tokens = sentence["tokens"]
        if not tokens:
            continue
        # Keep punctuation in internal n-grams, trim it only at sentence edges.
        start, end = 0, len(tokens)
        while start < end and not any(c.isalnum() for c in tokens[start]["surface"]):
            start += 1
        while end > start and not any(c.isalnum() for c in tokens[end - 1]["surface"]):
            end -= 1
        lexical = tokens[start:end]
        for n in range(1, 6):
            for i in range(len(tokens) - n + 1):
                segment = tokens[i:i + n]
                add("ngram", segment)
                if n >= 2 and any(t["pos"].startswith(("助詞", "助動詞")) for t in segment):
                    add("formula", segment)
        for n in range(2, 7):
            if len(lexical) >= n:
                add("ending", lexical[-n:])
        for n in range(2, 6):
            if len(lexical) >= n:
                add("opening", lexical[:n])
        for n in range(1, min(5, len(lexical)) + 1):
            prefix = lexical[:n]
            if "".join(t["surface"] for t in prefix) in TRANSITIONS or (n == 1 and prefix[0]["pos"].startswith("接続詞")):
                add("transition", prefix)
    return [dict(kind=k, expression=e, token_length=n, count=count)
            for (k, e, n), count in sorted(counts.items())]


def aggregate(analyzed, source_type, period, filter_noise=True):
    counts, coverage = Counter(), Counter()
    token_count = sum(len(s["tokens"]) for item in analyzed for s in item["sentences"])
    for item in analyzed:
        item["expressions"] = extract(item, filter_noise)
        for expr in item["expressions"]:
            key = expr["kind"], expr["expression"], expr["token_length"]
            counts[key] += expr["count"]
            coverage[key] += 1
    return [dict(kind=k, expression=e, token_length=n, count=count,
                 documents_count=coverage[k, e, n],
                 per_10k_tokens=count * 10000 / token_count if token_count else 0,
                 source_type=source_type, period=period)
            for (k, e, n), count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))]
