# 意味を選び、意味を受け取る時間を残す

## 取捨選択を記事全体から始める

原稿を短くする前に、記事の主張と読者の到達点を一文ずつ書く。各節がどの問いに答え、どの理解を支えているかを決める。単に関連する話題が並ぶ構成にしない。構成は編集時の仮説であり、意味を守れないと分かったら新しい要求から作り直す。

段落内に複数の役割があるなら、引用で指定した意味単位に分ける。主張・根拠・例・留保・作者の声・橋渡し・理解を深める反復を区別する。削除によって説明の依存関係が切れないかを見る。

採否には代案との比較を添える。「長いから削る」「同じだから削る」は十分な理由ではない。読者が同じ意味を別の形で受け取り直せる、抽象を経験に結び付けられる、ここで一息つけるなら、反復を残す理由になる。逆に、言葉だけ変えて理解も印象も動かない反復は削る候補となる。

## 理解の進む速さを調整する

前の文で何が分かった状態なのかを起点に次の文を書く。主語・条件・対象を同時に総入れ替えせず、引き継ぐ意味を残す。一文ごとに新しい発見を要求しない。新しい概念を受け取る前に、例や言い換えで現在地をつかむ時間を置いてよい。

言い換えでは、語を類語に置換するだけでなく、状況を経験として、仕組みを動作として、抽象を場面として捉え直す。ただし視点の変化が新しい事実を生む場合がある。「食べ物が少ない」だけから、誰もが飢えたとは断言できない。主張が増えたかを記録し、必要な根拠を添える。

## v2の選択JSON

editor-selectへ渡すファイルは次の形。各リストの個数は材料に応じて可変。下の記号は形式説明であり、そのまま入力する例ではない。

```json
{
  "strategy": {
    "thesis": "記事で伝える主張",
    "reader_destination": "読者が何を理解できる状態になるか",
    "selection_principle": "何を優先して残すか",
    "sections": [
      {"id":"s1", "question":"答える問い", "answer":"答え", "contribution":"記事全体への役割", "depends_on":[]}
    ],
    "meanings": [
      {"id":"m1", "source_id":"u001", "quote":"原文の正確な引用", "meaning":"保持・削除する意味", "role":"claim", "action":"recast", "section_id":"s1", "depends_on":[], "reason":"選択理由", "loss":"失うもの", "alternative":"比較した別案", "why_not_alternative":"その案を採らない理由"}
    ]
  },
  "decisions": [
    {"source_id":"u001", "action":"compress", "reason":"段落としての扱い", "loss":"意味単位へ切り分けた後に残る省略の説明"}
  ]
}
```

meaningのroleはclaim/evidence/example/qualification/voice/bridge/echo、actionはretain/recast/omit。全素材に少なくとも一つの意味判断を置く。compressにした段落から残す意味と捨てる意味を別々に記録できる。段落全体をkeep/moveにするなら、その意味をomit/recastとはしない。

## v2の再構成JSONへの追加

従来のparagraphs、coverage、cadence等に、meaning_coverageとreading_pathを加える。

```json
{
  "meaning_coverage": [
    {"meaning_id":"m1", "paragraph_id":"v001", "quote":"新しい本文の正確な引用", "reason":"なぜ元の意味が保たれるか"}
  ],
  "reading_path": [
    {"paragraph_id":"v001", "focus":"ここで扱う意味", "relation":"orient", "carry_from":[], "entry_reason":"ここから入る理由", "introduced":["初めて渡す概念"], "settles":["ここで受け取り直せる概念"], "reason":"読者の理解の進め方"}
  ]
}
```

reading_pathは見出しを含め全表示ブロックの順序に合わせる。carry_fromは過去のparagraph_id/quoteの一覧。引き継がず話を始める場合はentry_reasonを書く。relationはorient/advance/unpack/echo/bridge/qualify/close。introducedとsettlesは空でよく、概念数は採点しない。

echoの場合はさらにechoオブジェクトを置く。previous_meaning/current_meaning/shift/reader_effect/claim_delta/support_reasonを文章で説明し、currentへ当該段落のparagraph_id/quoteを置く。entailmentはsame_claimまたはsupported_inference。後者ではsupport_meaning_idsに保持した意味のIDを入れる。根拠が不明なら都合よくsame_claimにせず、資料へ戻る。

これらは編集者が判断を開示する契約であり、意味を機械が理解した証明ではない。各項目の引用や依存関係が合っていても、読者には伝わらない可能性が残る。
