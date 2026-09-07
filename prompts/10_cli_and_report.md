CLIを整理し、1コマンドで試せる統合処理を作ってください。

例:
`python -m jlangbase analyze samples/ --profile magazine --out output/`

内部で:
1. ingest
2. text analysis
3. expression extraction
4. profile build
5. markdown report

まで実行する。

`output/report.md` には:
- コーパス件数
- 文字数・token数
- 文長
- 文字種比率
- 頻出表現
- 文末表現
- 接続候補
- 注意事項

を載せる。

ログは過剰に冗長にしない。
