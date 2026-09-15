# natural-japanese 検査ランタイムの実装記録

## 結論

`jlangbase.japanese_checks` に、同梱した lint・outline・terms を専用仮想環境で実行するアダプターを追加した。通常の検査に必要な依存は `SudachiPy==0.6.11` と `SudachiDict-core==20260723` に固定した。どちらも 2026-09-15 に PyPI の公開版として確認した。

## 採用した仕様

- `run_check(name, args)` は元スクリプトへ引数をそのまま渡し、標準出力・標準エラー・終了コードを保つ。
- `analyze_text(text)` は UTF-8 の一時ファイルに本文を書き、lint・outline・terms の `--json` 出力を辞書として返す。いずれかが失敗した場合や JSON を読めない場合は `ValueError` にする。
- キャッシュ先は `JLANGBASE_CHECKS_CACHE` を優先し、未指定時は `~/.cache/jlangbase/natural-japanese-checks` を使う。環境作成中はロックファイルで排他する。
- 仮想環境が残っていても依存の import 確認に失敗すれば準備済みと扱わない。途中で壊れた Python 実行ファイルや pip がない環境は `venv --upgrade` で復旧を試みる。導入失敗後も準備済みの印を残さないため、次回呼び出しで再試行する。
- 準備済みの判定では import だけでなく、配布メタデータの版も照合する。手動で別版へ置き換えられていても、固定版の導入をやり直す。
- ロックは非ブロッキングで取得し、180秒で失敗する。ネットワーク待ち・検査実行にもそれぞれ上限を設けた。子プロセスは UTF-8 で入出力する。
- `--help` と `-h` は依存導入を行わない。初回の通常実行時だけ、標準エラーへ導入中であることを出す。実行不能・準備失敗・検査失敗は呼び出し側の既存契約に合わせて `ValueError` にする。
- `semantic` は通常環境と別の `semantic/` 仮想環境を明示呼び出し時だけ作る。`sentence-transformers==3.4.1` と `numpy==2.2.6` はその環境にだけ導入するため、通常検査から重量級依存やモデル取得は起きない。

## 見送った案

- システム Python へ依存を導入する案は、既存環境を変えるため見送った。
- 正常終了だけを準備済みの印にする案は、中断・失敗した導入を次回に誤認するため見送った。
- semantic の依存を通常依存へ加える案は、lint・outline・terms の初回実行で不要な大容量取得を招くため見送った。

## 検証

`.venv/bin/pytest -q tests/test_japanese_checks.py` を実行し、10件すべて成功した。失敗した導入の再試行、壊れた仮想環境の未準備判定、固定版の準備判定、引数と終了コードの保持、標準出力・標準エラーの転送、help 時の未準備、semantic の分離、JSON の解析と失敗、別プロセスからの import を確認した。

実依存を取得して同梱スクリプトを実行する検証は、この担当では行っていない。専用キャッシュを用いる統合検証は親担当が実施する。

依存の公開版は PyPI で確認した。[SudachiPy の公開履歴](https://pypi.org/project/SudachiPy/) と [SudachiDict-core の公開履歴](https://pypi.org/project/SudachiDict-core/) を 2026-09-15 に `python3 -m pip index versions` で照会し、採用版が存在することを確認した。semantic の任意依存も [numpy](https://pypi.org/project/numpy/) と [sentence-transformers](https://pypi.org/project/sentence-transformers/) で同じ方法により確認した。
