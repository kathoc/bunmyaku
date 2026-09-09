# 読者の現在地を持つ生成

新規loop-startはv2。確認可能なWORLD_STATE、変化するNARRATOR_STATE、推定であるREADER_STATEを分ける。reader.profileとreader.assumed_knowledgeはseedで任意指定する。titleは任意で、省略時はquestionを使う。説明したことを理解されたことにしない。

新規stateにはreader_review_version=2も付く。reader-functions.mdに従い、修正前に文の働きを分析する。保存済みv2でこのキーがない場合は旧読解版1であり、この追加工程を要求しない。古い記録を上書き移行しない。

## 六つを必要な場所で使う

欠けた前提、前文との連続、消した場合の損失、言い換えで得る理解や実感、題名へのつながりを判断する。実読者が止まった箇所は別途記録する。問題のない段落は無変更を選べる。診断は草案の引用と具体的原因を伴い、原因を示せない全文修正はしない。原文の比較案を残し、採用理由と保持する意味、適用条件を記す。未対応の原因には残す理由が必要。

最小修正は最少文字数ではない。接続だけで通れば接続だけ、前提が欠けていれば必要な説明を補う。意味を支える反復と意図的な引っ掛かりは残す。語尾や段落長を均等にも不均等にも割り当てない。残りの候補はreader-options.mdで、原因に関係するものだけを参照する。

## 手動で進める場合

以下のengineコマンドは同梱の実行入口から呼ぶ。jlangbase CLIではengineを省く。全て出力先は新規ファイル。

```text
engine loop-start seed.json --out state-0.json
engine loop-request state-0.json --out write-request.json
```

要求に沿って一段落を書きdraft.txtへ保存する。

```text
engine loop-functions state-0.json --paragraph draft.txt --out functions-request.json
```

functions-request.jsonの契約に従い、修正案をまだ作らず、声・想像・考える余地などを引用とともにfunctions-response.jsonへ記録する。その応答を固定して次へ進む。

```text
engine loop-review state-0.json --paragraph draft.txt --function-review functions-response.json --out reading-request.json
```

response_contractに沿って読解判断をreading-response.jsonへ保存する。diagnosis_shape、unresolved_shape、explanation_shapeは要素の形の説明で、問題や引用を必ず作る指示ではない。variantsには原文そのままの案が必要。問題がなければdiagnoses=[]、無変更案だけでもよい。

読解版2ではfunction_reviewとfunction_review_hashを変更せず返し、function_outcomesで記録した各働きをどう扱ったか示す。無変更でもpreserveの引用と理由を残す。function_shapeやfunction_outcome_shapeは例で、件数のノルマではない。旧読解版1ではloop-functionsと--function-reviewを省略する。

```text
engine loop-request state-0.json --reading-review reading-response.json --out reflect-request.json
```

採用本文から発見を抽出し、契約どおりの応答をreflection.jsonへ保存する。reading_reviewは改変しない。

```text
engine loop-step state-0.json --response reflection.json --out state-1.json
```

事実確認に疑義があれば本文も読者状態も受理しない。保存済みv1は従来手順を維持する。Ollamaではこれらを自動実行する。読解版2は読解版1より文の働きの分析が一回増え、執筆・働きの分析・修正選択・振り返りを一段落ごとに行う。新規Python run_loopにはreviewerとfunction_reviewerコールバックが必要。モデルによる意味判断は保証ではなく、受理してもquality_improvedはnull。

## 読者の反応を残す

同梱入口のloop-reader-feedback state.json --feedback report.jsonで端末内へ保存する。reportのstate_hashは対象stateをdiscovery_loop.fingerprintで計算した値。stateが変わったら別の版として扱う。observationsは実際の回答がある項目だけでよい。

```json
{
  "state_hash": "対象stateのfingerprint",
  "origin": "reader",
  "observation_source": "本人から受け取った回答の識別情報",
  "observations": [{
    "paragraph_index": 0,
    "version": "accepted",
    "quote": "止まった箇所の正確な引用",
    "interpretation": "本人がどう受け取ったか",
    "difficulty": "どこが分からなかったか",
    "applicability": "知識や読んだ場面など、共有してよい範囲",
    "effect": "unknown"
  }]
}
```

versionはdraft/accepted、effectはunknown/better/same/worse。比較していなければunknown。モデルの試答はorigin=model。名前など不要な個人情報は求めない。実回答も改善の自動証明ではない。contextのmemory_indexから関連記録を選び、本人の適用条件を無断で一般化しない。ローカルに保存するだけでモデルの重みや共通ルールは更新しない。
