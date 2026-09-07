"""UTF-8 machine and human outputs."""
import json
from pathlib import Path


def write_json(path, value, compact=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                               indent=None if compact else 2) + "\n", encoding="utf-8")


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")


def profile_markdown(profile):
    sentence = profile["sentence_metrics"]
    lines = ["# コーパスの解析結果", "", f"ジャンル: {safe(profile['source_type'])}", "",
             f"文書数: {profile['document_count']} / 文字数: {profile['char_count']} / token数: {profile['token_count'] if profile['token_count'] is not None else '未計測'}",
             f"文数: {sentence['count']} / 平均文長: {sentence['mean']:.2f} / 中央値: {sentence['median']:.2f}", "",
             "## 文字種比率", "", "| 文字種 | 比率 |", "| --- | ---: |"]
    lines += [f"| {k} | {v:.2%} |" for k, v in profile["char_type_ratios"].items()]
    lines += ["", "## 句読点と記号", "", "| 種類 | 出現数 | 1万文字あたり |", "| --- | ---: | ---: |"]
    lines += [f"| {k} | {v['count']} | {v['per_10k_chars']:.2f} |" for k, v in profile["punctuation_metrics"].items()]
    for title, key in (("頻出表現", "common_ngrams"), ("文末表現", "sentence_endings"), ("文頭表現", "sentence_openings"), ("接続候補", "transition_candidates")):
        lines += ["", f"## {title}", "", "| 表現 | 出現数 | 文書数 | 1万tokenあたり |", "| --- | ---: | ---: | ---: |"]
        lines += [f"| {safe(r['expression'])} | {r['count']} | {r['documents_count']} | {r['per_10k_tokens']:.2f} |" for r in profile[key]]
    structure = profile["structure_metrics"]
    lines += ["", "## 段落と見出しの構造", "",
              f"段落数: {structure['paragraph_count']} / 見出し数: {structure['heading_count']} / 見出し階層の飛び: {structure['heading_level_jumps']}",
              f"平均段落長: {structure['mean_paragraph_length']:.2f} / 文書あたり平均段落数: {structure['mean_paragraph_count']:.2f}", ""]
    lines += [f"- {note}" for note in structure["notes"]]
    lines += ["", "## 注意事項", ""] + [f"- {note}" for note in profile["notes"]]
    lines += ["", "著者区分: " + safe(profile["author_types"]), ""]
    return "\n".join(lines)


def write_profile(out, profile, compact=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "profile.json", profile, compact)
    (out / "report.md").write_text(profile_markdown(profile), encoding="utf-8")
