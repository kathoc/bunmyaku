# 一括インストール

## 最初の一回

GitHubの配布物を取得・展開したディレクトリで実行する。Python 3.11以上が必要。Windowsではpythonの代わりにpyを使える。

```bash
python install.py
```

PATH上のcodex/claude/ollamaを検出し、使える入口を登録する。アプリだけの導入などで検出されない場合は明示する。

```bash
python install.py --tools codex,claude,ollama
```

確認のみは--dry-run、隔離先は--home。導入済みの環境は、新しい配布物で`python install.py --update`を実行する。更新は明示操作であり、自動ダウンロードはまだ実装していない。コードの旧版と導入履歴を保持し、個人メモリーは書き換えない。途中のファイル書き込み失敗を含む完全なトランザクション復旧は未実装。競合する既存ファイルは上書きせず停止する。

## Codex / Claude Code

Codexには`~/.agents/skills/japanese-discovery-writing`、Claudeには`~/.claude/skills/japanese-discovery-writing`を配置する。その後は普段どおり記事執筆や推敲を依頼する。認識されなければ新しいセッションまたは再起動を試す。自動選択はモデルの判断であり、100%の起動保証ではない。既存AGENTS.md/CLAUDE.mdや他のスキルを変更・無効化しない。

同梱スキルの手順に従えば、利用中のモデルが生成担当となるため別の生成APIは不要。共通Pythonコードは状態管理を担う。別の校正スキルと同時選択される可能性は残り、自動的に競合を解消したとは扱わない。

## Ollama

Ollamaサーバを起動し、ローカルモデルを用意する。インストーラーはサーバ起動やモデルダウンロードをしない。通常の`ollama run`を置き換えるものではない。

```bash
natural-japanese ollama-write "スーパーマリオとは何だったのか？" --seed eval_cases/super_mario/discovery-loop/seed.json --model LOCAL_MODEL_NAME
```

PATHに`~/.local/bin`がない場合は、インストーラーが表示するinvocationへ`ollama-write ...`を付ける。Windowsは表示されたPowerShell形式を使う。モデルが一つだけなら--modelは省略可。seedは事実と出典を固定するため必要で、事実収集は自動化していない。モデルの構造化出力能力や長い文脈の処理能力によっては停止する。

Ollamaとの通信はループバックのHTTP、プロキシ・リダイレクトなし。クラウド名のモデルは拒否するが、ローカルサーバ自体の内部動作までは制御しない。文章生成の料金や外部通信については、利用するサーバの設定も確認する。

## 共通ルール・スキル・メモリー

ルール正本は`~/.agents/references/jlangbase-writing.md`。スキルは薄い入口。個人メモリーと索引は`~/.agents/memory/jlangbase/`、訂正はcorrections、生成記録はsessions。更新時に個人メモリーを消さず、中央への送信処理は設けない。POSIXでは個人ルートに700を指定するが、既存の権限やWindows ACLは変更しない。

`natural-japanese feedback record.json`で、症状・変更前後・理由・適用条件・user/modelの区分を保存する。これは学習候補の蓄積であり、モデル本体の学習ではない。Codex/Claudeへ原稿を入力すれば、そのサービスへの入力になりうる点は別問題。

## 中央の定期改善

公開先リポジトリで管理者が一度だけ設定する。

1. `.github/workflows/central-improvement.yml`をデフォルトブランチに配置する。
2. GitHub SecretにOPENAI_API_KEYを登録する。利用者各端末に配布しない。
3. Repository VariableのENABLE_CENTRAL_RESEARCHをtrueにする。未設定なら実行しない。
4. 週次月曜03:23 UTC、または手動で候補報告を作る。実行費用は中央管理者側に発生する。
5. Actionsのartifactを人間が読み、比較・読者評価を経て採用する。候補生成は自動、採用・公開版の作成は手動。

成果物は報告一つだけをアップロードする。秘密情報や端末の個人履歴を収集しない。自動PR・自動公開・自動採用は行わない。現状は公開先未指定で、pushも中央ジョブの有効化もしていない。

## 参照と未検証範囲

[Codexスキル](https://learn.chatgpt.com/docs/build-skills)、[Claude Codeスキル](https://code.claude.com/docs/en/skills)、[Ollama chat API](https://docs.ollama.com/api/chat)、[構造化出力](https://docs.ollama.com/capabilities/structured-outputs)、[Codex GitHub Action](https://learn.chatgpt.com/docs/github-action)の関連節を参照した。

今回の実装後のテスト・実インストール・実モデル生成・3OSでの動作確認は未実施。ソース実装があることと、各ツールで自動起動できたことを区別する。
