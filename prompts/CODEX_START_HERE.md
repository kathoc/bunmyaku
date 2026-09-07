以下をCodexに最初に渡してください。

---

このリポジトリで、日本語の時代変化とAI文章との差分を定量化する実験基盤を作りたい。
まず `00_master_prompt.md` と `README.md` を読んで全体像を理解し、その後 `01_scaffold.md` から順番に実装してください。

ルール:
- 各プロンプトを一度に全部実装せず、1ファイルずつ進める。
- 各段階でpytestを実行する。
- 設計変更が必要なら `docs/decisions.md` に理由を書く。
- 不要なフレームワークやWeb UIを追加しない。
- 動作確認できない機能を「完成」と扱わない。
- 推測で外部仕様を決めない。外部APIやライブラリの現行仕様が必要なら公式資料を確認する。
- まずローカルコーパスだけでエンドツーエンドに動かす。

最初の完了条件は、`samples/` の自作文を対象に `python -m jlangbase analyze samples/ --profile magazine --out output/` が成功し、profile JSONとMarkdownレポートが生成されること。
---
