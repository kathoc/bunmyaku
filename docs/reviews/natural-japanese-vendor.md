# natural-japanese vendor 実装記録

## 実施内容

監査済みの上流 commit `cecd53e98d58ab8ba7d9f97a9f4558362d643c5a` から、`SKILL.md`、references 全階層、assets、`lint.py`・`outline.py`・`terms.py`・`textcore.py`・`semantic.py` を `src/jlangbase/resources/natural-japanese/` に原文のまま同梱した。ルートの MIT `LICENSE` は `LICENSE.md` として同梱し、`provenance.json` に origin、commit、24ファイルのSHA256、除外理由、取り込み日時、改変なしを記録した。`calibrate.py`、fixtures、`__pycache__`、corpus は除外した。

同期入口は `scripts/vendor_natural_japanese.py`。source リポジトリ引数を必須とし、dirty source は拒否する。`--check` は書き換えず差分を終了コードで返す。同一入力では provenance の取り込み日時を保持して差分を発生させない。destination の予期しないファイル、または既存 provenance と異なる同梱ファイルを検出した場合は削除・上書きせず停止する。

## 検証

- `uv run pytest -q tests/test_natural_japanese_vendor.py`: **3 passed**
- idempotence、provenance の同梱SHA256一致、dirty source拒否、nested resource/LICENSE の `package_files` 収集を確認
- `python3 scripts/vendor_natural_japanese.py /home/sonohoka/.agents/skills/natural-japanese --check`: 差分なし（exit 0）
- 上流とvendor対象24ファイルをバイト比較: mismatches 0

## 親レビュー対応

検査スクリプト実行で生成される `scripts/__pycache__/` は同期対象・配布対象から除外した。初回登録でも、destination に同名ファイルがあればバイト一致時だけ許可し、異なる内容は上書きせず停止する。source と destination のシンボリックリンクは外部パス追従を防ぐため停止する。回帰テストは実同梱先を変更しない tmp_path fixture 方式へ改め、6件が成功した。全体テストは `.venv/bin/python -m pytest -q` で 129 passed。

今回の所有範囲（vendor script、vendor tree、vendor test）以外の実装ファイルは変更していない。
