"""Character/sentence statistics and optional Sudachi morphology."""
from collections import Counter
from importlib import metadata
import re
import statistics
import unicodedata

CHAR_TYPES = ("kanji", "hiragana", "katakana", "ascii", "other")
PUNCTUATION = {
    "period": r"[。.]", "comma": r"[、,]", "exclamation": r"[!！]",
    "question": r"[?？]", "brackets": r"[「」『』（）()［］\[\]【】〈〉《》{}｛｝]",
    "ellipsis": r"[…⋯]+|\.{3,}|・{3,}", "newline": r"\r\n|\r|\n",
}
URL = re.compile(r"https?://[^\s<>「」『』。！？]+")
CLOSERS = '」』）)]】〉》”’"'


def split_sentences(text):
    # Preserve punctuation and closing quotes; protect decimals and URL internals.
    protected = set()
    for match in URL.finditer(text):
        protected.update(range(match.start(), match.end()))
    sentences, buffer = [], []
    i = 0
    while i < len(text):
        char = text[i]
        buffer.append(char)
        decimal = char == "." and i > 0 and i + 1 < len(text) and text[i - 1].isdigit() and text[i + 1].isdigit()
        ellipsis = char == "." and ((i > 0 and text[i - 1] == ".") or (i + 1 < len(text) and text[i + 1] == "."))
        boundary = char in "\r\n" or (char in "。！？!?." and i not in protected and not decimal and not ellipsis)
        if boundary:
            while i + 1 < len(text) and text[i + 1] in "。！？!?\r\n" + CLOSERS:
                i += 1
                buffer.append(text[i])
            sentence = "".join(buffer).strip()
            if sentence:
                sentences.append(sentence)
            buffer = []
        i += 1
    if "".join(buffer).strip():
        sentences.append("".join(buffer).strip())
    return sentences


def char_type(char):
    code = ord(char)
    if "CJK UNIFIED IDEOGRAPH" in unicodedata.name(char, "") or "CJK COMPATIBILITY IDEOGRAPH" in unicodedata.name(char, "") or char == "々":
        return "kanji"
    if 0x3040 <= code <= 0x309F:
        return "hiragana"
    if 0x30A0 <= code <= 0x30FF or 0xFF66 <= code <= 0xFF9F:
        return "katakana"
    return "ascii" if code < 128 else "other"


def metrics(text, sentences=None):
    sentences = split_sentences(text) if sentences is None else sentences
    lengths = [len(s) for s in sentences]
    count = len(text)
    chars = Counter(char_type(c) for c in text)
    punctuation = {k: len(re.findall(pattern, text)) for k, pattern in PUNCTUATION.items()}
    return {
        "char_count": count, "sentence_count": len(lengths), "sentence_lengths": lengths,
        "mean_sentence_length": statistics.mean(lengths) if lengths else 0,
        "median_sentence_length": statistics.median(lengths) if lengths else 0,
        "char_type_counts": {k: chars[k] for k in CHAR_TYPES},
        "char_type_ratios": {k: chars[k] / count if count else 0 for k in CHAR_TYPES},
        "punctuation_counts": punctuation,
        "punctuation_per_10k_chars": {k: v * 10000 / count if count else 0 for k, v in punctuation.items()},
    }


class Analyzer:
    def __init__(self, backend="auto"):
        if backend not in {"auto", "basic", "sudachi"}:
            raise ValueError(f"不明な解析器です: {backend}")
        self.tokenizer = None
        self.info = {"name": "basic", "version": "1", "morphology_available": False}
        if backend == "basic":
            self.info["reason"] = "文字・文のみの解析を指定"
            return
        try:
            from sudachipy import Dictionary, SplitMode
            self.tokenizer = Dictionary(dict="core").create(mode=SplitMode.C)
            self.info = {"name": "sudachi", "version": metadata.version("SudachiPy"),
                         "dictionary_version": metadata.version("SudachiDict-core"),
                         "split_mode": "C", "morphology_available": True}
        except (ImportError, ModuleNotFoundError, metadata.PackageNotFoundError) as exc:
            if backend == "sudachi":
                raise ValueError("SudachiPyとSudachiDict-coreをインストールしてください") from exc
            self.info["reason"] = "SudachiPyまたはcore辞書が未導入"
        except Exception as exc:
            raise ValueError(f"Sudachiの初期化に失敗しました: {exc}") from exc

    def tokens(self, text):
        if self.tokenizer is None:
            return []
        # URLs are excluded before tokenization to avoid fragmented URL expressions.
        text = URL.sub(" ", text)
        return [{"lemma": m.dictionary_form(), "surface": m.surface(),
                 "pos": ",".join(m.part_of_speech()), "normalized_form": m.normalized_form()}
                for m in self.tokenizer.tokenize(text) if m.surface().strip()]

    def analyze(self, doc):
        sentences = split_sentences(doc["text"])
        return {"document": doc, "metrics": metrics(doc["text"], sentences),
                "sentences": [{"text": s, "tokens": self.tokens(s)} for s in sentences]}
