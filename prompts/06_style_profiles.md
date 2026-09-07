ジャンル別 style profile 生成機能を作ってください。

例:
`python -m jlangbase build-profile --source-type magazine --out output/magazine.json`

JSONには最低限:
- generated_at
- corpus_period
- source_type
- document_count
- token_count
- sentence_metrics
- char_type_ratios
- punctuation_metrics
- common_ngrams
- sentence_endings
- sentence_openings
- transition_candidates
- notes

を持たせる。

重要:
- profileはLLMに渡しやすいように巨大化させない。
- 上位項目数をCLIで制限可能にする。
- 生の頻度と、LLM向けの要約を分ける。
- `notes` に断定的な流行判定を入れない。

さらに `--compact` で数KB程度の軽量版を生成できるようにする。
