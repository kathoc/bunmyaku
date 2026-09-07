from jlangbase.expressions import aggregate, extract, usable


def item(words):
    return {"sentences": [{"text": "".join(words), "tokens": [
        dict(surface=w, lemma=w, normalized_form=w, pos="助詞" if w == "は" else "名詞") for w in words]}]}


def test_frequency_is_not_coverage():
    docs = [item(["猫", "猫", "。"]), item(["猫", "は", "走る", "。"])]
    rows = aggregate(docs, "magazine", {"from": None, "to": None})
    cat = next(r for r in rows if r["kind"] == "ngram" and r["expression"] == "猫")
    assert cat["count"] == 3 and cat["documents_count"] == 2
    assert cat["per_10k_tokens"] == 30000 / 7
    assert any(r["kind"] == "formula" and r["expression"] == "猫は" for r in rows)


def test_sentence_edges_and_noise():
    rows = extract(item(["「", "しかし", "猫", "は", "走る", "。", "」"]))
    assert any(r["kind"] == "transition" and r["expression"] == "しかし" for r in rows)
    assert any(r["kind"] == "ending" and r["expression"] == "は走る" for r in rows)
    for expr in ("。", "は", "１２３", "https://example"):
        assert not usable(expr, 1)
    assert usable("は", 1, False)


def test_no_cross_sentence_ngrams():
    data = {"sentences": item(["猫"])["sentences"] + item(["犬"])["sentences"]}
    assert not any(r["expression"] == "猫犬" for r in extract(data))
