# bunmyaku

**bunmyakuは、日本語の文章生成・推敲の仕組みを研究する実験プロジェクトです。** 完成した製品ではなく、文章品質の向上や、すべての環境での動作を保証するものではありません。

日本語の文章を、書きながら考え直すための執筆支援プロジェクトです。Codex・Claude Code用スキル、Ollama用アダプター、段落単位の認識更新、文章分析と修正履歴を扱います。Pythonパッケージ名と既存CLI名は互換性のため`jlangbase`を維持しています。

参考にした論文・記事・プロジェクト・公式資料は[参考資料一覧](docs/references.md)にまとめています。出典の紹介と、本プロジェクトでの効果の実証は区別します。

## 導入と現在の状態

Python 3.11以上で、このリポジトリを取得・展開したフォルダから実行します。

```bash
python install.py
```

詳細は[導入手順](docs/install.md)と[生成ループ](docs/discovery-loop-guide.md)を参照してください。個人の原稿・修正履歴は各端末内で管理し、中央収集はしません。CodexやClaudeを利用する際のクラウド通信は、端末内保存とは別です。

**開発途中の公開版です。** 一括配置コードとモデル接続アダプターは実装済みですが、3OSでの実インストールと各ツールの自動起動は未検証です。`curl`/PowerShellによる導入、端末内の定期改善、更新候補の承認・復帰、自動更新は未実装です。中央実行の旧案は採用せず、GitHub Actionsによる改善処理は本公開版に含めません。設計資料中の中央実行の記述は旧案として扱ってください。

以下は既存のコーパス分析機能の説明です。

手元の日本語文書を集計し、文章表現と段落構造を比較するPythonのCLIです。SQLiteに本文と解析履歴を保存し、軽量なJSONプロファイルとMarkdownレポートを出力します。分析機能自体は外部APIやWeb UIを使いません。

文章を磨くための入口は[プロジェクト内で完結する編集手順](docs/craft-guide.md)です。[評価された記事の構造分析](docs/research/reading-craft.md)を同梱し、段落の役割、説明の保留、語調・拍の変化、冒頭のひっかかりを記録します。環境側の日本語校正スキルは呼びません。個別フィードバックやローカルの比較実行記録は、この公開版には含めていません。

最初は下のQuick Startを実行してください。比較・評価・改稿記録のコマンドは、その後に必要なものを選べます。設計上の判断と不具合の原因は[作業記録](docs/decisions.md)、採用した要件は[仕様書](docs/spec.md)に残しています。

## 5分でサンプルを解析する

Python 3.11以上が必要です。`python`がない環境では、仮想環境を作る最初のコマンドを`python3.12`などへ置き換えてください。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,morphology]'
python -m jlangbase analyze samples/ --profile magazine --out output/
```

Windows PowerShellでの有効化は `.venv\Scripts\Activate.ps1` です。`uv`を使う場合は以下でも準備できます。

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[dev,morphology]'
.venv/bin/python -m jlangbase analyze samples/ --profile magazine --out output/
```

結果は`output/profile.json`と`output/report.md`に出ます。`samples/magazine.jsonl`の12文書は動作確認用の自作生成文です。すべて`author_type: llm`と記録しており、人間の雑誌文章を代表するデータではありません。

形態素解析が不要なら `pip install -e .` だけでも動きます。SudachiPyとcore辞書が未導入の場合は、文字・文・構造を解析し、token数は`null`、表現の一覧は空にします。未計測を頻度ゼロとは扱いません。`--backend basic`でこの動作を明示でき、`--backend sudachi`は未導入時にエラーを返します。

## 文書を投入し、ジャンルごとに見る

```bash
python -m jlangbase ingest samples/ --source-type magazine --platform local --dry-run
python -m jlangbase ingest samples/ --source-type magazine
python -m jlangbase analyze --source-type magazine
python -m jlangbase expressions --source-type magazine --top 10
python -m jlangbase build-profile --source-type magazine --out output/magazine.json --compact
```

入力はUTF-8のtxt、md、jsonlです。BOMも許容します。JSONLは1行1文書で、文字列の`text`が必須です。その他のメタデータは保存されます。

```json
{"text":"本文です。", "source_type":"magazine", "author_type":"human", "published_at":"2026-09-01", "source_ref":"自分の資料名", "topic":"ゲーム"}
```

同じ本文は全ジャンル共通のハッシュで重複排除し、最初のメタデータを維持します。JSONL内の`source_type`はCLIの既定値より優先されます。投入件数と追加・重複・空文書・失敗件数を表示し、壊れた行やファイルがあっても後続を処理します。失敗があれば終了コード1、設定や入力パスなどのエラーは2です。

`--db 任意のパス`でDBを切り替えられます。既定は`data/processed/corpus.sqlite3`です。`analyze パス`は投入後、指定ジャンルのDB内全文書を解析します。そのパスだけを調べたい場合は別DBを指定してください。`build-profile`は最新の解析runを使うため、文書を追加したら先に`analyze`を実行します。

## 人間文と生成文を比較する

```bash
python -m jlangbase compare-human-llm human.jsonl llm.jsonl --out output/comparison
python -m jlangbase compare-human-llm llm.jsonl --human-source magazine --out output/comparison
```

JSONとMarkdownに、1万tokenあたりの頻度、比率、頻度差、文書カバレッジの差を出します。基準頻度が0の場合は比率を`null`とし、理由を付けます。`overrepresented_in_llm`と`underrepresented_in_llm`は指定した2コーパス間の差であり、著者がAIかどうかの判定ではありません。

## 初稿・改稿・基準文を同じ条件で評価する

```bash
python -m jlangbase evaluate \
  --reference eval_cases/super_mario/reference \
  --before eval_cases/super_mario/versions/00_initial.md \
  --after eval_cases/super_mario/versions/02_structure.md \
  --weights config/evaluation.json --out output/evaluation
```

距離は0〜1で、0ほど基準の分布に近いことを示します。文長、文字種、接続候補、文末、n-gramに加え、段落長、段落内文数、冒頭と末尾の比率などを内訳として出します。重みは`config/evaluation.json`で変更できます。未計測の指標は除外し、残りの重みを再正規化します。

語彙や表現の差には題材も影響します。構成が良くなったか、説明が正しいかを総合距離だけで判断しないでください。

## マリオの文章を、表現と構成の両方から記録する

```bash
python -m jlangbase record-experiment eval_cases/super_mario --weights config/evaluation.json
```

実験には、抽象的な初稿、表現を見直した版、構成も見直した版があります。`eval_cases/super_mario/manifest.json`に各版の変更意図と、主張・具体例・段落間の接続・限定・結論についての注釈を残しています。注釈には本文中の根拠と解釈の確信度を付けます。

実行ごとに`records/日時-ID/`へ本文、ハッシュ、プロファイル、構造、指標別評価、`trajectory.md`を保存します。過去の記録は残り、`records/latest.json`が最新の保存先を示します。続きを試すときは、新しい本文とmanifestの版を追加して再実行してください。別の題材でも同じ形式を使えます。

3版と基準文はすべてAI生成です。人間コーパスを用いた独立評価ではありません。構成の注釈も生成者自身による解釈であり、読み手による評価とは分けています。

## 同じ長さの期間を比較する

```bash
python -m jlangbase diff --source-type social --from 2026-09-01 --to 2026-10-01 \
  --thresholds config/diff.json --out output/diff
```

この例は`[2026-08-02, 2026-09-01)`と`[2026-09-01, 2026-10-01)`の30日ずつを比べます。開始日時を含み、終了日時を含みません。公開日時を優先し、なければ収集日時を使います。日時にタイムゾーンがない場合はUTCとして扱います。両期間に文書が必要です。

emerging、rising、stable、declining、sparseは設定ファイルの閾値による分類です。少数の文書から「流行」とは判断しません。

## 指標の読み方と制約

| 用語 | この実装での意味 |
| --- | --- |
| token | Sudachiの分割単位。分母に句読点を含み、URLと空白を除く |
| n-gram | 連続する1〜5 token。文の境界をまたがない |
| 文書カバレッジ | 表現を含む文書数を全対象文書数で割った値 |
| profile | 上位表現と集約値を含む参照用JSON |
| run | 解析器・辞書・対象本文ハッシュを記録した処理単位 |

文字数は空白と記号を含むUnicode文字数です。文長には句読点とMarkdownの見出し文字も含みます。構造の集計は空行を段落境界とし、ATX見出しとコードフェンスを段落から除きます。Setext見出しやHTMLの構造は解釈しません。接続候補は文頭の固定表現と接続詞品詞による抽出で、意味の判定はしません。

同じ本文・メタデータ・解析器・設定で統計は再現します。実行日時とrun_id、記録フォルダ名は実行ごとに変わります。辞書を更新すると分割結果が変わるため、バージョンを揃えて比較してください。

## 検証する

```bash
python -m pytest -q
python -m compileall -q src/jlangbase
```

失敗報告には、実行コマンド、終了コード、解析器・辞書バージョンを添えてください。公開できない本文は報告へ貼らず、再現用の短い自作文に置き換えられるか確認してください。
