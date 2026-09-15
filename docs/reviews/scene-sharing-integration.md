# scene-sharing 追加の統合調査

## 結論

`src/jlangbase/resources/scene-sharing.md` を追加し、`src/jlangbase/resources/writing-skill.md` の入口点検から参照させれば、配布処理の変更なしで同梱できる。スキルからの参照は相対パスにせず、インストール後の `context` が返す `resources` ディレクトリを起点に読むよう指示する。

## 確認した範囲

- `src/jlangbase/resources/writing-skill.md` 全56行
- `src/jlangbase/resources/reader-functions.md` 全41行
- `docs/editorial-memory.md` 全47行
- `docs/editorial-memory-index.md` 全16行
- `src/jlangbase/distribution.py` の `package_files()` と `install()`（20〜149行）
- `src/jlangbase/bundle_cli.py` の `context` 出力（86〜93行）
- `pyproject.toml` の package-data（20〜23行）
- `install.sh` / `install.ps1` のアーカイブ抽出条件（`src/jlangbase/**`）
- `tests/test_agent_distribution.py` 全105行、`tests/test_github_install.py` 全149行

## 必要な変更

1. `src/jlangbase/resources/scene-sharing.md` を新規作成する。既存の `reader-functions.md` は、文の働きを `role` と `function_outcomes` に記録し、実読者の効果を保証しないという役割を持つ。scene-sharing がこの分析契約を拡張しない限り、同ファイルの変更は不要である。拡張する場合だけ、関連する項目とJSON契約を同時に仕様化する。
2. `writing-skill.md` の「入口の点検」に、`context` で得た `resources` を起点に `scene-sharing.md` を読む条件を追加する。現在のスキルは `reader-loop.md`、`reader-functions.md`、`project-purpose.md` などを参照するが、配布後のスキル自身のディレクトリから `resources/scene-sharing.md` を読む前提にはなっていない。
3. この指針を共通の編集判断として正式採用するなら、`docs/editorial-memory.md` に判断の背景・適用範囲・未検証事項を追記し、`docs/editorial-memory-index.md` に正本と資源の索引を1行追加する。単なる候補資料として追加する段階なら、採用判断を記録するまでメモリーを更新しない。

## 配布処理の判定

変更は不要である。`distribution.package_files()` は `src/jlangbase` 以下を再帰的に走査し、`.md` を含むファイルを POSIX形式のキーで収集する。`install()` は収集した全ファイルをリリース内の `jlangbase` へ書き出す。`pyproject.toml` の `jlangbase = ["resources/*.json", "resources/*.md"]` も新規Markdownを対象にする。GitHubの `install.sh` と `install.ps1` は `install.py` と `src/jlangbase/` 以下だけを展開するため、配置場所を守れば抽出条件の変更も不要である。

`bundle_cli context` は `resources` にインストール済みリソースディレクトリの絶対パスを返す。したがって、配布スキルには「`context` の `resources` を取得し、そのディレクトリの `scene-sharing.md` を必要な場合だけ読む」と記述する。`distribution.py` がテンプレートを置換するのは `__RULES__` と `__AGENT_RULES__` だけなので、リソース名を追加してもテンプレート置換処理は変わらない。

## 検証コマンド

実装後は次を順に実行する。

```bash
.venv/bin/pytest -q tests/test_agent_distribution.py tests/test_github_install.py
.venv/bin/pytest -q
python -m compileall -q src
git diff --check
```

配布確認では、既存の `context` 統合テストに加え、`Path(context["resources"]) / "scene-sharing.md"` が存在することを確認するテストを `tests/test_agent_distribution.py` または `tests/test_github_install.py` に追加するのが適切である。`package_files()` のキーが `resources/scene-sharing.md` になることは、既存のPOSIX/Windowsパス回帰テストと同じ観点で確認できる。本文の日本語品質は、資源追加後に `uv run ~/.agents/skills/natural-japanese/scripts/lint.py src/jlangbase/resources/scene-sharing.md` を実行し、指摘を機械的に全置換せず判断する。

## 参照した根拠

- `writing-skill.md:8-9` は共通手順と個人設定の所在を示し、`writing-skill.md:21-24` は共通資源の参照を指示している。
- `reader-functions.md:18-30` は文の働き、前提、損失を記録する契約を定めている。
- `distribution.py:20-30` はリソース収集とリリースハッシュを定め、`distribution.py:47-49` は収集済みファイルと正本の配置を定めている。
- `bundle_cli.py:86-93` は `context` の `resources` パスを返す。
- `pyproject.toml:22-23` は `resources/*.md` をパッケージデータに含める。
