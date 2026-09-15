# natural-japanese 単体配布レビュー

レビュー日: 2026-09-15
対象: `docs/natural-japanese-integration-spec.md` と現在の差分
範囲: 同梱資料、検査ランタイム、配布・wheel、執筆代理 reviewer、記憶保持

## 結論

**PASS（現行実装）**。前回の指摘だった `__pycache__` は `destination_files()` の列挙から除外され、通常検査後の `vendor_natural_japanese.py --check` は `{"different": []}`（exit 0）となった。vendorテストも一時ディレクトリ内で完結する形に更新され、実homeの上流ソースや本物のDESTを変更しない。

## 確認結果

- Python 3.12環境で同梱 lint・outline・terms を実原稿に実行し、3種の JSON を取得できた。reviewer への結果経路は `agent_writing.task()` の `natural_japanese_checks` にあり、既存のレビュー合否スキーマを自動変更しない。
- `uv build --wheel` で `jlangbase-0.1.0-py3-none-any.whl` を作成し、natural-japanese の SKILL、references/doctypes、assets、scripts、`LICENSE.md`、`provenance.json` を確認した。ネスト資料の現行ツリーはwheelに入っている。
- MITライセンス、上流commit、ファイルSHA256は provenance と LICENSE.md にある。vendor の dirty source 拒否、同梱ファイルの外部変更拒否も実装されている。
- 検査ランタイムは専用venv、固定依存、依存導入・検査・ロックの時間上限、準備失敗後の再試行、semantic環境の分離を備える。`--help` は依存準備を開始しない。
- `.venv/bin/python -m pytest -q tests/test_natural_japanese_vendor.py tests/test_japanese_integration.py tests/test_japanese_checks.py` は **19 passed**。vendorテストはtmp_path内のsource・destinationで実行され、Windowsのsymlink不可環境はskipする。

## 修正要求

未解消の修正要求はない。vendor本体は同期先の列挙で `__pycache__` を除外し、テストも生成物を含む実行順に依存しない。

wheel 同梱、ライセンス、固定版の資料、reviewer実検査結果、既存記憶の新規作成・索引追記については、今回の対象範囲で追加の重大欠落を確認しなかった。
