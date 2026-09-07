# このプロジェクトだけで、書く・残す・比べる

今回の入口は`craft-brief`と`reading-map`です。ホームディレクトリの日本語スキルや外部lintは呼びません。手元の文章を自動で良文へ置き換える機能ではなく、執筆の判断材料を作り、原文・解釈・読者の反応を区別して残す編集基盤です。

[分析した記事と採用した考え方](research/reading-craft.md)を先に読むと、数値の使いどころが分かります。人間の記事の本文をコーパスとして再配布せず、出典、評価根拠、短い構造分析、編集上の問いをパッケージに同梱しています。

## 書く前に、読者の変化を決める

```bash
python -m jlangbase craft-brief \
  --topic 'スーパーマリオとは何だったのか？' \
  --reader 'ゲームを遊んだことのある人' \
  --purpose '失敗した後にもう一度試したくなる理由を考える' \
  --genre essay --out output/brief
```

`brief.md`は、各段落で何を変えるか、説明を待たせる理由はあるか、書き手の偏りを残せるかを問います。指定できるジャンルはessay、explanation、guide。guideでは、操作に必要な前提を隠すような仕掛けを勧めません。

## 原稿のどこで調子が変わるかを見る

```bash
python -m jlangbase reading-map \
  eval_cases/super_mario/versions/03_friction.md \
  --review eval_cases/super_mario/reviews/03_friction.json \
  --out output/mario-reading-map
```

`reading-map.md`に段落番号、元の行、冒頭文、文長、検討箇所、根拠付き注釈が出ます。`reading-map.json`は順序付きの段落情報を持ち、段落を入れ替えれば隣接関係も変わります。

解析器に指摘されなかったことは、面白さや読みやすさの保証ではありません。機械は説明の連続や局所的な形の近さを示し、その箇所を残すかどうかは、段落の働きと本文を見て判断します。

## ひっかかりを消す前に、役割を記録する

review JSONは本文のSHA-256ハッシュで対応付けます。本文が変わると古い注釈は拒否されるので、改稿に合わせて見直してください。`nodes`は段落の役割と読者が得ること、`frictions`はひっかかりの機能を記録します。

| 項目 | 記録すること |
| --- | --- |
| anchor | ひっかかりの段落と短い原文 |
| foothold | そこまでに読者へ渡した手がかり |
| reader_question | 読者に残ると考えた問い |
| benefit / risk | 残す効果の仮説と、分かりにくくなるリスク |
| resolution / payoff | 同じ箇所で解く、後で解く、開いたままにする、の区別と回収先 |
| necessity / required_at | 主張・操作に必要な情報か、必要になるのはいつか |
| decision / decision_reason | 残す・直す・消す・比較する、の判断と理由 |
| confidence | その解釈の確信度。読者の実測値ではない |
| claim_status / claim_source | 数字などが仮の例か、未検証か、出典を持つか |

語調の切り替えは`register_shift`、数量の桁の意外さは`scale_jump`、局所的な拍の変化は`rhythm`です。語の強さや疑問符だけを数えて品質得点にはしません。引用が本文にあることは検査しますが、解釈や出典の真偽まで自動認定しません。

[ユーザーの即興例と冒頭配置の対照例](../eval_cases/attention/README.md)も保存しています。「鬼のような」と「3万回ほど」を同じ不自然さとして扱わず、異なる働きとして注釈しました。原文は導入の断片なので、断片内の位置を記事全体の位置とは呼びません。

## 5-7-5から13-4-6への変化を、文字数と分ける

reading-mapには句読点で区切った拍列の分析を含めています。直前3文で句数が揃う場合に、各位置の拍数の中央値と次の文を比較します。5-7-5が続いた後の13-4-6なら、差は+8、-3、+1になります。

拍数はモーラを数えます。小さい「ゃ」などは前の音と結合し、「っ」「ん」「ー」は各1拍です。漢字の読みは任意依存のSudachiに頼るため、辞書の読みが文脈と合わない場合もあります。`--rhythm-backend basic`なら、かなで読みを確定できる箇所だけを測ります。

読めない句の拍数は`null`です。文字数で埋めたり、測定できなかったことを抑揚がない証拠にしたりしません。アクセント、間、声の高さは音声を使っていないため未計測です。局所変化の検出条件はJSON出力に残ります。

## 導入の印象と読後の理解を分けて比較する

```bash
python -m jlangbase reader-study \
  eval_cases/attention/versions/01_early.md \
  eval_cases/attention/versions/02_later.md \
  --out output/attention-study
```

読者には`public/`だけを渡してください。最初に`packet-01-opening.md`で導入を読み、続きを読みたいかを記録します。その後、`packet-01.md`で全文を読みます。別の読者にはpacket-02を渡すと順序が逆になります。実際にこの順で読んだかは機械では監視していません。

`private/key.json`は版名との対応表なので、回答が終わるまで見せません。回答用JSONを記入し、回答者ごとに1行へまとめたJSONLを集計します。

```bash
python -m jlangbase reader-results output/attention-study \
  --responses answers.jsonl --out output/attention-results.json
```

興味、理解の自己申告、読む労力、最初に注意を引いた箇所、内容の説明、思い出した言葉を分けます。理解の自己申告が高くても、説明した内容が合っているとは限りません。人間とモデルの回答も別集計です。未回答の場合は未計測とし、改善したとは報告しません。

## 過去の版を残して次へ進む

```bash
python -m jlangbase record-experiment eval_cases/super_mario --backend sudachi
```

03は説明を一部保留し、筆者の好みを残す版です。04は同じ主張を明示的に説明する対照版です。読者の反応を調べる前に03を勝者とは決めていません。新しいrecord-experimentの結果には、各版の`craft/reading-map.md`も保存されます。

新しい題材でも、ブリーフ、原稿、review、比較用の版を揃えれば同じ手順を使えます。新機能の純粋なPython部分は標準ライブラリだけで動きます。`python -m pytest -q`で注釈や集計を検証できますが、テストの成功は文章の質が向上した証拠とは区別してください。
