# 書き殴った素材から、読者へ渡す原稿へ

## 先に選び、後で組み直す

生成ループのcompleteは素材の一区切り。表示段落の完成ではない。最初にeditorial-meaning.mdに従い、記事全体の主張・読者の到達点・各節の貢献を決める。その後、原文を意味単位へ分け、主張、根拠、具体例、留保、作者の声、橋渡し、理解を深める反復を選ぶ。理解を進めない繰り返しと、有益な言い換えを区別する。振り返りの記録を本文へすべて露出させず、決定には理由・失うもの・比較した別案を添える。

`editor-request 原稿.md --brief brief.json --out request.json`で素材を固定する。briefはtitle/reader/promise/required_points（id/meaningの一覧）と、任意のmaterials（id/text/sourceの一覧）。追加事実はmaterialsへ出典とともに置き、再構成時に黙って足さない。

`editor-select request.json --decisions decisions.json --out composition.json`へ、strategyとdecisionsを含むオブジェクトを渡す。形式はeditorial-meaning.mdを参照する。decisionsは全素材のsource_id/action/reason/loss。keepとmoveは文面を残す。compressは意味の選別と再表現を許し、dropは本文に使わない。strategyではそれより細かい意味の採否と依存関係を記録する。v1の保存済み要求だけは従来の配列形式を受け付ける。機械は理由の妥当性までは判断しない。

## 読者向けの単位にする

compositionのresponse_contractへ、paragraphs（id/text/source_ids/role/reader_gain）、coverage（requirement_id/paragraph_id/quote/reason）、cadenceを書いて`editor-apply composition.json --response response.json --out result.json`へ渡す。結果のmarkdownが表示用原稿。元の思索の状態は書き換えない。

一段落で読者が得る理解を言えるようにするが、すべてに新情報、独立した結論や起承転結を要求しない。例を出す段落、同じ意味を違う視点から受け取る段落、前の問いを引き受ける段落も認める。v2ではmeaning_coverageで保持した意味の行き先を示し、reading_pathで前から引き継ぐ意味と読者の現在地を記録する。素材と表示段落は多対多でよい。削除率・新概念数・段落文字数のノルマはない。

## 音の流れを検討する

まず、意味上の係り受けと力点、どこで一息入れられるかを考える。語尾、句の並び、読点、反復、長く運ぶ文と短く置く文を、前後との関係で扱う。

cadence.modeはtext_inference。sequenceごとにsetup/departure/settlingをparagraph_idとquoteで指定し、effect、alternative、choice_reasonを残す。文字列上の推定を発声・聴取結果と呼ばない。変更不要ならsequencesを空にし、unchanged_reasonを書く。全段落に崩しと回収を入れない。毎回同じ短長短に整えない。

文字数・文長は観測値にすぎず、快さの点数にしない。モーラ推定も抑揚・アクセント・時間を直接計測しない。音楽の研究を散文の普遍則にしない。根拠と反例はeditorial-research.mdへ。

## 停止

意味を保てること、必要な情報が届くこと、変更に理由があることを優先する。残る迷いはreader_questionsへ書く。受理はeditorial_candidateであり、読み手による改善評価ではない。note等への公開は別の明示操作とする。

## 文体の既定

指定がない新規原稿の標準は「です・ます」調。利用者の明示的な文体指定や、既存原稿の文体保持の依頼を優先する。既存原稿への狭い修正では、文体変更を依頼されていない限り、原稿全体の語尾まで変更しない。引用・コードを改変せず、敬体への変更は意味とリズムを保って行う。

文末の単調さはeditorial-register.mdに従う。敬体の基調を守ることと、全ての文を敬体で閉じることを混同しない。語尾の置換より先に意味の重複と文の切り方を編集し、必要箇所の語り方の変化をcadenceの選択理由へ記録する。割合や交互配置の規則は置かない。
