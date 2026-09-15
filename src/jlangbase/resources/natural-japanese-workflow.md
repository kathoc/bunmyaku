# 同梱の日本語執筆と検査

bunmyakuはnatural-japaneseの固定版を同梱している。別のスキルをインストールせず、本文の設計、読みやすさ、文体の点検に使う。contextが返すnatural_japaneseディレクトリにSKILL.md、references、assets、scripts、LICENSE.md、由来の記録がある。相対参照はこのディレクトリを起点に解決する。

## 執筆前に読む

通常はこの統合手順を読み、該当する文書型を一つ選ぶ。references/doctypes/のminutes.mdは議事録、report.mdは調査報告、guide.mdは手引き、memo.mdは企画や検討メモ、slide.mdはスライド構成。エッセイには型を強制しない。文体を学ぶ依頼ではassets/style-profile-template.md、診断だけの依頼ではreferences/diagnose.mdを読む。診断を依頼された原稿を書き換えない。

設計では読者、目的、素材の根拠、暫定の主題を定める。ひとつの意味を受け取れる順に説明し、必要な専門用語は働きとともに紹介する。前置きや抽象的な評価を重ねず、根拠のある事実や例を使う。同じ型を全ての節に当てず、詳しく書く箇所は内容から決める。

文意を直すときはreferences/readability-principles.mdを使う。文中の複雑さが原因ならreadability-antipatterns.mdの該当箇所へ進む。禁止語と翻訳調はforbidden-patterns.md、translationese.md、ジャンルによる違いはgenre-notes.mdを参照する。全資料を毎回読み込む必要はない。

## 通常の検査

INSTALLATION.mdの実行コマンドに次の引数を付ける。コマンド名がPATHにあれば、そのまま実行できる。

```text
natural-japanese lint manuscript.md --json
natural-japanese outline manuscript.md --json
natural-japanese terms manuscript.md --json
```

初回は専用のPython仮想環境へSudachiPyと日本語辞書を自動導入するため、通信と追加時間が必要。uvや外部のnatural-japaneseスキルは不要。準備や検査に失敗したら、失敗を報告し、検査済みとしない。通常検査で意味モデルは取得しない。

短い推敲でもlintと意味の通読を行う。必要に応じて--genre essay、--genre tech、--genre businessを指定し、読解負荷は--reading-loadで確認する。反復して直すときは--baselineへ前回のlint JSONを渡す。詳しい検討ではoutlineとtermsも使い、構造、読みやすさ、文書型との対応を点検する。

writing-taskの点検要求には、その原稿をlint・outline・termsで実際に処理した結果がnatural_japanese_checksとして含まれる。担当は結果を読み、文脈上直す点と残す点を既存のreviewsのreason・conditionへ記す。結果が付いている場合、同じ原稿のために検査を重複実行しない。実行に失敗した要求は発行されず、問題を解消してから同じ工程を再開する。

lintの警告は自動的な不合格ではない。意味や事実、作者の声を確認してから修正する。構造は見出しと段落の先頭を通して読み、用語は初出で必要な説明があるか判断する。警告ゼロも、モデルの合格も、実読者の理解を保証しない。検査結果が指す行番号は要求中の原稿本文に対応する。

## bunmyakuでの適用順

依頼者の明示指示と既存原稿の保持条件を優先する。natural-japaneseの原文は同梱するが、次の点ではbunmyakuの統合手順を使う。

- 主題と結論は仮置きにし、書いた結果の発見に応じて更新する。結論先行の構成が必要な報告書でも、生成中の思考まで固定しない。
- 主語と述語の関係、事実、因果を守る。語尾や文長の変化、細部の数、太字の数を達成目標にしない。
- 原稿の生成・点検・編集は既存の担当分担で進める。上流のクイック／フルを理由に分担を解除したり、担当から別の担当を再帰的に起動したりしない。詳しい点検が必要なら、親が既存の点検担当へ構造・読みやすさ・文書型の観点を渡す。
- 上流の自己採点の閾値や所要時間を、bunmyakuの受理条件や性能保証にしない。読みやすさの問題とAIによる執筆かどうかの推定を混同しない。
- sessions、修正理由、検査記録、利用者のメモリーを、上流の後片付け規則で削除しない。完成稿とは分けて既存の保存方針を使う。

Ollama担当はファイルや検査コマンドを自分では実行できない。要求に渡された統合手順と検査結果を使い、必要な追加資料は親側で用意する。使っていない資料を読了済みとしない。

## 任意の診断と更新

意味の類似度を見るsemanticは実験的な追加検査。明示して利用する場合だけ、同梱スクリプトの依存とモデル取得条件を確認する。通常のlintや執筆工程に代わるものではない。

同梱版はbunmyakuの配布更新で変わる。導入時に上流の最新版を取得しない。保守担当はscripts/vendor_natural_japanese.pyで由来とファイルのハッシュを更新し、bunmyakuの統合手順と整合するか点検する。上流の内容をそのまま個人の新しい指示へ昇格させない。
