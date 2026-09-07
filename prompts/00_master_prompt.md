あなたはこのリポジトリの主任実装者です。以下の目的を満たす「Japanese Language Baseline」実験基盤を構築してください。

目的:
- 現代日本語の実文をジャンル別に保存する。
- 単語頻度、連語、文長、文字種比率、句読点、文末、接続表現などを定量化する。
- ジャンル別の style profile をJSONで生成する。
- 将来的には時系列差分を取り、「増えている表現」「減っている表現」「LLMが人間より過剰使用している表現」を検出できるようにする。
- Codex/Claude等が文章生成時に参照できる軽量JSONプロファイルを出力する。

重要な設計原則:
1. 生データ、機械集計、LLMによる意味分類を明確に分離する。
2. LLMの推測を事実として保存しない。必ず confidence と evidence を持たせる。
3. 最初からWebスクレイピングに依存しない。ローカルのtxt/md/jsonl投入で全パイプラインを動かす。
4. 可能な限りPython標準ライブラリを使い、必要最小限の依存にする。
5. 日本語形態素解析は SudachiPy を第一候補とし、未導入時のフォールバックも考える。
6. SQLiteを標準DBにする。
7. CLI中心で、GUIは作らない。
8. 再現性を優先し、各処理は同じ入力から同じ出力を返す。
9. 設計判断と失敗した試行を `docs/decisions.md` に追記する。
10. 不明点は勝手に複雑化せず、まず最小実装を完成させる。

最終的なCLI例:
- `python -m jlangbase ingest samples/ --source-type magazine`
- `python -m jlangbase analyze --source-type magazine`
- `python -m jlangbase build-profile --source-type magazine`
- `python -m jlangbase diff --from 2026-09-01 --to 2026-10-01`
- `python -m jlangbase compare-human-llm human.jsonl llm.jsonl`

まず現状を確認し、必要なファイル構成を提案したうえで実装してください。各段階でテストを追加してください。
