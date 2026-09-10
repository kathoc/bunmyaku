# 一括インストール

## 最初の一回

Python 3.11以上が必要です。macOS・Linuxではcurlを使います。

```bash
curl -fsSL https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.sh | sh
```

スクリプトを先に読んでから実行したい場合は、未使用のファイル名で保存してください。

```bash
curl -fSL https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.sh -o bunmyaku-install.sh
```

保存したファイルをエディターで開き、内容に納得したら`sh bunmyaku-install.sh`を実行します。ダウンロードに失敗した場合は実行しないでください。公開mainの最新版を取得します。署名検証や固定バージョン指定は未実装です。

### Windows（PowerShell）

Windows PowerShell 5.1以降を対象とした入口です。Git Bashは不要です。

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.ps1)))
```

内容を読んでから実行する場合は、まず取得したスクリプトを表示します。

```powershell
$installer = Invoke-RestMethod https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.ps1 -ErrorAction Stop
$installer
```

表示した内容に納得したら、`& ([scriptblock]::Create($installer))`を実行します。管理者権限や実行ポリシーの変更は不要です。

明示的な更新は次のコマンドです。

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.ps1))) -Update
```

ツールを指定する場合は`-Tools codex,claude,ollama`ではなく、文字列として`-Tools 'codex,claude,ollama'`を渡します。導入先を変更する場合は`-InstallHome 'C:\\bunmyaku-sandbox'`、導入先を変更せず予定を見る場合は`-DryRun`を付けます。`-DryRun`でも配布物の取得と一時展開は行います。

### ダウンロード済みの配布物から導入する場合

GitHubから実行コード、環境別スキル、共通手順、個人メモリーの入口をまとめて導入します。今回追加した執筆代理も含まれます。GitHubの配布物を取得・展開したフォルダでも導入できます。Windowsでは`py install.py`、ほかのOSでは次のコマンドを使います。

```bash
python install.py
```

PATH上のcodex/claude/ollamaを検出し、使える入口を登録する。アプリだけの導入などで検出されない場合は明示する。

```bash
curl -fsSL https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.sh | sh -s -- --tools codex,claude,ollama
```

導入済みの環境は、同じ入口から明示的に更新できます。新規導入のコマンドをそのまま再実行すると停止するため、次のように`--update`を付けてください。

```bash
curl -fsSL https://raw.githubusercontent.com/kathoc/bunmyaku/main/install.sh | sh -s -- --update
```

確認のみは`--dry-run`、隔離先は`--home`です。curl方式の`--dry-run`でも配布物の取得と一時展開は行いますが、導入先は変更しません。取得済みの配布物なら`python install.py --update`でも更新できます。定期的な自動更新ではありません。コードの旧版と導入履歴を保持し、個人メモリーは書き換えません。途中のファイル書き込み失敗を含む完全なトランザクション復旧は未実装です。競合する既存ファイルは上書きせず停止します。

## Codex / Claude Code

Codexには`~/.agents/skills/japanese-discovery-writing`、Claudeには`~/.claude/skills/japanese-discovery-writing`を配置する。その後は普段どおり記事執筆や推敲を依頼する。認識されなければ新しいセッションまたは再起動を試す。自動選択はモデルの判断であり、100%の起動保証ではない。既存AGENTS.md/CLAUDE.mdや他のスキルを変更・無効化しない。

新規執筆では、CodexからはCodexの、Claude CodeからはClaudeのサブエージェントへ依頼する。親AIがbunmyakuの共通コマンドで執筆指示、点検、差し戻し、全文編集を管理し、最終点検を通過した原稿を返す。別の生成APIは不要。サブエージェント機能が利用できない環境では理由を報告して停止する。別の校正スキルと同時選択される可能性は残る。

呼び出しを明示したい場合は「bunmyaku（japanese-discovery-writing）で、○○について書いて」と依頼する。通常は親AIが依頼の整理とコマンド操作を行う。開発者向けの手順とbriefの例は[執筆代理の共通手順](../src/jlangbase/resources/agent-writing.md)にある。

## Ollama

Ollamaサーバを起動し、ローカルモデルを用意する。インストーラーはサーバ起動やモデルダウンロードをしない。通常の`ollama run`を置き換えるものではない。

執筆から全文編集・最終点検まで任せる場合は、[共通手順の例](../src/jlangbase/resources/agent-writing.md)に沿ってbrief.jsonを作り、次のコマンドを使う。執筆役・点検役・編集役を同じOllama接続で呼び出す。別モデルによる独立評価ではない。

```bash
natural-japanese writing-start brief.json --session ./writing-session --host ollama
natural-japanese writing-run ./writing-session --model LOCAL_MODEL_NAME
natural-japanese writing-handoff ./writing-session --out manuscript.md
```

最後の書き出しはcompleteになった場合だけ成功する。資料不足や修正上限で止まった場合は、セッションに残った理由を解決する。従来の段落生成だけを使う場合は次の入口も残る。

writing-runはJSON Schemaで応答形式を指定し、文脈容量を既定16,384トークンで要求する。初回は`--context-length`で変更できる。入力が容量上限に達したときは停止し、本文を黙って省いて受理しない。意味の点検精度はモデルによるため、モデルの合格を事実保証には使わない。

```bash
natural-japanese ollama-write "スーパーマリオとは何だったのか？" --seed eval_cases/super_mario/discovery-loop/seed.json --model LOCAL_MODEL_NAME
```

PATHに`~/.local/bin`がない場合は、インストーラーが表示するinvocationへ`ollama-write ...`を付ける。Windowsは表示されたPowerShell形式を使う。モデルが一つだけなら--modelは省略可。seedは事実と出典を固定するため必要で、事実収集は自動化していない。モデルの構造化出力能力や長い文脈の処理能力によっては停止する。

Ollamaとの通信はループバックのHTTP、プロキシ・リダイレクトなし。クラウド名のモデルは拒否するが、ローカルサーバ自体の内部動作までは制御しない。文章生成の料金や外部通信については、利用するサーバの設定も確認する。

## 共通ルール・スキル・メモリー

ルール正本は`~/.agents/references/jlangbase-writing.md`。スキルは薄い入口。個人メモリーと索引は`~/.agents/memory/jlangbase/`、訂正はcorrections、生成記録はsessions。更新時に個人メモリーを消さず、中央への送信処理は設けない。POSIXでは個人ルートに700を指定するが、既存の権限やWindows ACLは変更しない。

`natural-japanese feedback record.json`で、症状・変更前後・理由・適用条件・user/modelの区分を保存する。これは学習候補の蓄積であり、モデル本体の学習ではない。Codex/Claudeへ原稿を入力すれば、そのサービスへの入力になりうる点は別問題。

## 定期的な改善について

各利用者の端末で調査・比較・採用判断を行う方針です。中央で個人データを集める仕組みは設けません。端末内の定期調査、改善案の自動比較、ルールの採用・復帰はまだ未実装です。上の`--update`は公開されたコードを手動で更新する操作であり、文章のルールを自動で学習する処理ではありません。

## 参照と未検証範囲

[Codexスキル](https://learn.chatgpt.com/docs/build-skills)、[Claude Codeスキル](https://code.claude.com/docs/en/skills)、[Ollama chat API](https://docs.ollama.com/api/chat)、[構造化出力](https://docs.ollama.com/capabilities/structured-outputs)、[Codex GitHub Action](https://learn.chatgpt.com/docs/github-action)の関連節を参照した。

従来機能の検証状況は各仕様書に残す。2026-09-10追加の執筆代理については[仕様と検証結果](agent-writing-spec.md)を参照。ソース実装、隔離環境の動作確認、各ホストでの実モデル実行を区別する。

GitHubのZIPを模した配布物による入口からの検証は、[配布の検証記録](reviews/github-distribution.md)にまとめています。Linux・macOS・Windowsの配布CIが成功しました。Linuxでは公開GitHubからの新規導入・更新・個人記録保持も確認しています。Windowsの旧版更新テストには、旧版のパス表現だけを補正した試験用ソースを使っています。詳細は記録を参照してください。
