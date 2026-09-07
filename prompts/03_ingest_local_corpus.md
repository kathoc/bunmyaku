ローカルコーパス投入機能を作ってください。

対応形式:
- .txt
- .md
- .jsonl

jsonlは1行1documentで、text以外のメタデータを任意に受け付ける。

CLI例:
`python -m jlangbase ingest samples/ --source-type magazine --platform local`

要件:
- UTF-8前提だがBOMを許容。
- 空文書を無視。
- text_hashで重複排除。
- 処理件数、追加件数、重複件数、失敗件数を表示。
- 失敗ファイルで全体停止しない。
- `--dry-run` を用意。
- テストを追加。
