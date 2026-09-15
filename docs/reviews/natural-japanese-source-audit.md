# natural-japanese 配布元監査

監査日: 2026-09-15
対象: `/home/sonohoka/.agents/skills/natural-japanese`
対象コミット: `cecd53e98d58ab8ba7d9f97a9f4558362d643c5a`（`docs: READMEの文体憲法初出箇所にファイルリンクを追加`、2026-09-04）
作業ツリー: clean（`git status --porcelain=v1` 出力なし）

## 結論

bunmyaku の単体配布へ取り込む最小十分な範囲は、スキル本体一式と、既定の3検査を動かす共有基盤である。具体的には次を vendor 対象とする。

- `skills/natural-japanese/SKILL.md`
- `skills/natural-japanese/references/` 以下16個の Markdown（SKILL.md から相互参照されるため一式）
- `skills/natural-japanese/assets/style-profile-template.md`
- `skills/natural-japanese/scripts/lint.py`、`outline.py`、`terms.py`、`textcore.py`
- 必要なら検査例として `scripts/fixtures/natural.md` と `ai-smelly.md`（実行には不要）

`semantic.py` は実験的な opt-in 機能、`calibrate.py` は配布元の corpus 校正用なので、既定の単体配布からは外せる。`__pycache__/*.pyc` は生成物であり除外する。対象ディレクトリは生成物を除くと 25 ファイル、約 543 KiB（SKILL 1、references 16、assets 1、scripts の Python 6・fixture Markdown 2）。

## ライセンス

配布元ルートの `LICENSE` は MIT License、Copyright (c) 2026 coji。取り込み時は `LICENSE` を同梱するか、bunmyaku の既存ライセンス表示に MIT の著作権表示と許諾文を含める必要がある。スキルの front matter にも `license: MIT` がある。依存ライブラリは別ライセンスのため、実行環境で解決する依存のライセンス表示は bunmyaku 側の配布方針に従う。

## ファイルと依存

### 既定の軽量検査

`lint.py`、`outline.py`、`terms.py` は各ファイル先頭の PEP 723 メタデータで、Python `>=3.10`、`sudachipy>=0.6.8`、`sudachidict-core>=20240409` を宣言する。いずれも標準ライブラリに加えて同じ Sudachi 依存を使い、`textcore.py` を同じ scripts ディレクトリから `from textcore import ...` で読み込む。`textcore.py` 自体は PEP 723 メタデータを持たず、Sudachi を遅延 import する共有基盤である。

`uv run scripts/<name>.py <file>` を想定し、`uv` が PEP 723 の依存を自動解決する。入力は UTF-8 の Markdown/テキストファイル。ファイル不在、ディレクトリ指定、読み取り不能、非 UTF-8 は exit 1。内容に関する finding の有無は exit 0（lint の JSON も同じ）。`lint.py` は `--json`、`--genre essay|tech|business`、`--baseline PREV.json`、`--experimental`、`--reading-load` を持つ。`outline.py` と `terms.py` は `--json` を持つ。

### オプション検査

`semantic.py` は `sentence-transformers>=3.0.0`、`numpy`、および同じ Sudachi 依存を宣言する。内部で `torch` と `sentence_transformers` を import し、既定モデル `cl-nagoya/ruri-v3-310m` を使用する。10文未満なら統計処理をスキップする設計だが、`uv run` の依存解決だけで torch/CUDA 関連を大量取得し得る。10文以上では Hugging Face からモデル（初回約1GB級）を取得し、以後は HF キャッシュを使う。したがって既定検査への同梱・自動実行は不適切で、明示 opt-in とネットワーク/キャッシュ前提を利用者へ伝える必要がある。

`calibrate.py` は `sudachipy` と `sudachidict-core` のみだが、`scripts/` の親から `corpus/`（`corpus/sources.json`、`human/`、`ai/` 等）を相対的に読む。校正結果を配布先で再現する用途がなければ不要である。

## 相対参照と外部環境依存

スキル本文と16個の reference は `references/...`、`assets/...`、`scripts/...` の相対パスを参照するため、vendor 後も `skills/natural-japanese/` 内の階層を維持する必要がある。`scripts` は実行時の `sys.path[0]`（semantic は明示的に scripts を挿入）に依存して `textcore.py` を見つける。別階層へ平坦化すると import が壊れる。

reference 内には配布元の `corpus/reports/...` を経緯説明として挙げる記述と、外部 Web URL があるが、既定の3検査の実行時に corpus を読む処理はない。説明を完全に自己完結させる必要がなければ corpus 全体の取り込みは不要。文章編集の実行はエージェントの判断に依存し、スクリプトは検出・抽出だけを行う。`uv`、Python 3.10 以上、Sudachi 辞書の取得/キャッシュが実行環境の前提となる。

## 取り込み判断

既定機能を bunmyaku へ統合するなら、上記の SKILL/reference/asset と4 Python（lint・outline・terms・textcore）を同一階層で同梱し、MIT `LICENSE` を保持し、PEP 723 の実行経路を `uv run` として案内する。fixture は動作確認用に任意、`semantic.py` と `calibrate.py`、`__pycache__`、配布元の corpus/研究成果物は最小配布から除外できる。依存は完全には省けない。Sudachi 形態素解析は3検査の実装上の必須依存であり、削るには検出ロジックの別実装が必要になる。semantic の重量依存だけは機能を opt-in 除外することで既定配布から切り離せる。

## 実行確認

配布元の fixture `natural.md` に対して次を実行し、既定3検査はいずれも exit 0、JSON 出力を得た。

```text
uv run .../scripts/lint.py .../scripts/fixtures/natural.md --json
uv run .../scripts/outline.py .../scripts/fixtures/natural.md --json
uv run .../scripts/terms.py .../scripts/fixtures/natural.md --json
```

semantic は短い fixture での確認を試みたが、`uv` が実行前の依存解決で torch/CUDA 等の大容量パッケージを取得し始めたため停止した。モデル推論結果は未検証であり、これは上記の重量依存・ネットワーク依存の確認として扱う。
