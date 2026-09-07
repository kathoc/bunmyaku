時系列差分機能を実装してください。

CLI例:
`python -m jlangbase diff --source-type social --from 2026-09-01 --to 2026-10-01`

比較:
- 前期間 vs 後期間
- per_10k_tokens
- document coverage
- ratio
- absolute delta

状態候補:
- emerging
- rising
- stable
- declining
- sparse

重要:
これらの状態は閾値ベースで機械的に判定し、設定ファイルに閾値を出す。
「流行語」とは呼ばない。

最低出現数、最低文書数を設け、小標本の暴走を防ぐ。

結果をJSONとMarkdownで出力する。
