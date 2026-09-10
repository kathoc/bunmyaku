# GitHub配布の検証結果

2026-09-10。Linuxで、GitHubと同じ構成のZIPから新規導入し、執筆代理追加前の公開版から更新できた。インストーラー本体は変更せず、入口を通す統合テストと3OSのCIを追加した。

## 確認した範囲

install.sh、install.ps1、install.py、src/jlangbase/distribution.py、tests/test_agent_distribution.py、README.md、docs/install.md、配布関連仕様の全文を読んだ。新しい統合テストtests/test_github_install.pyと.github/workflows/distribution.ymlも全文を見直した。

実行はLinuxの一時ホームで行った。ZIPのダウンロードだけをローカルのコピーに置き換え、シェル入口の展開処理とPythonインストーラーはそのまま実行した。既存版の再現には公開コミット227c024のinstall.pyとsrc/jlangbaseを使った。

## 結果

`uv run --with pytest python -m pytest -q tests/test_agent_distribution.py tests/test_github_install.py`は5件すべて成功した。独立した静的確認として`sh -n install.sh`と`git diff --check`も成功した。

- 空白と日本語を含む新規ホームへ、共通コード・ルール・環境別スキル・メモリー索引を導入できた。
- 導入されたランチャーのcontextで、執筆代理の共通手順を参照できた。
- writing-startとwriting-taskで、Codex・Claude・Ollamaそれぞれのhostを保持した依頼を作れた。
- 更新指定なしで導入済みホームへ再実行すると停止し、導入マニフェストを変更しなかった。
- 旧公開版から--updateで更新でき、個人原稿・訂正記録・追記済みメモリーと旧導入マニフェストを保持した。
- 既存の配布テストでは、競合時に部分導入をしないこと、最終点検前の原稿を書き出さないことも確認した。

追加検証では、仮想環境を有効化せず`.venv/bin/pytest`を直接起動すると、新規テスト2件がPython不足で失敗した。テストの子プロセスがシステムのPython 3.10だけをPATHで見つけ、テスト実行中のPython 3.12を引き継いでいなかったためである。子プロセスのPATH先頭に`sys.executable`の親ディレクトリを加えた。インストーラーの最低Python条件は変更していない。`.venv/bin/pytest -q tests/test_github_install.py tests/test_agent_distribution.py`で5件の成功を確認した。

日本語lintではREADMEと導入手順の指摘は0件だった。仕様と本記録には文長の均質さが各1件出たが、条件を正確に並べる技術文書として内容と読みやすさを優先し、長さを変えるためだけの修正はしなかった。

## 公開後に確認する範囲

ローカル検証は実際のGitHub通信やmacOS・Windowsでの実行結果を含まない。GitHub Actionsにはubuntu-latest、macos-latest、windows-latestを登録した。WindowsではPowerShell入口を使い、Invoke-WebRequestだけをローカルZIPのコピーに置き換える。

公開後はリポジトリ直下で、次のコマンドを実行する。現在のinstall.shが公開main.zipを実際にダウンロードする。取得後にcontextの内容と環境別スキルを確認し、結果をこの節に追記する。

```sh
check_root=$(mktemp -d /tmp/bunmyaku-github-check.XXXXXXXX)
sh install.sh --home "$check_root/home" --tools codex,claude,ollama
"$check_root/home/.local/bin/natural-japanese" context
sh install.sh --home "$check_root/home" --tools codex,claude,ollama --update
```

GitHub Actionsの3OSの結果も、完了したジョブのURLとともに追記する。今回のCIは配布と状態管理の確認であり、ClaudeやOllamaでの文章品質を評価するものではない。
