# Japanese Language Baseline — Codex Prompt Pack

目的: 2026年時点の日本語を観測・定量化し、Codex/Claudeなどの文章生成品質を改善するためのローカル実験基盤を作る。

## 推奨実行順
1. `00_master_prompt.md`
2. `01_scaffold.md`
3. `02_data_model.md`
4. `03_ingest_local_corpus.md`
5. `04_text_analysis.md`
6. `05_expression_extraction.md`
7. `06_style_profiles.md`
8. `07_llm_baseline_comparison.md`
9. `08_evaluation.md`
10. `09_daily_diff.md`
11. `10_cli_and_report.md`
12. `11_quality_and_tests.md`
13. `12_future_connectors.md`

## 方針
- 最初は合法かつ再現可能なローカル文書を入力対象にする。
- WebスクレイピングやSNS API連携は後段に分離する。
- LLMには流行を“判定”させず、機械集計した差分の意味分類に使う。
- 生データ、統計、推定、評価結果を混同しない。
- 日本語の自然さを「禁止語リスト」で管理せず、ジャンル別の相対頻度と差分で扱う。

## 最初の完成条件
`python -m jlangbase analyze samples/ --profile magazine` で解析し、`output/profile.json` と `output/report.md` が生成されること。
