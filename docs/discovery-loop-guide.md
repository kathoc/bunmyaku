# 発見駆動ループの使い方

`craft-brief`は執筆前の資料。このループは執筆中の状態遷移を担当する。モデルAPIは内蔵していない。利用中のアシスタントへ要求を渡す方法と、Pythonのwriter/reflector関数を接続する方法を用意した。状態はプロジェクト内のJSONだけで保持できる。

## CLIで1段落ずつ進める

```bash
python -m jlangbase loop-start eval_cases/super_mario/discovery-loop/seed.json --out output/discovery/state-00.json
python -m jlangbase loop-request output/discovery/state-00.json --out output/discovery/write-01.json
# write-01.jsonを生成担当へ渡し、本文1段落をparagraph-01.txtとして受け取る。
python -m jlangbase loop-request output/discovery/state-00.json --paragraph output/discovery/paragraph-01.txt --out output/discovery/reflect-01.json
# reflect-01.jsonを抽出担当へ渡し、response_contractに従うresponse-01.jsonを受け取る。
python -m jlangbase loop-step output/discovery/state-00.json --response output/discovery/response-01.json --out output/discovery/state-01.json
```

activeならstate-01から次の要求を作る。事前の予定ではなく、新しい認識・問い・残りの構成が入力される。応答のstate_hashは要求から引き継ぐ。全段落を先に生成して後付けで発見履歴を作る方法とは区別する。

## Pythonから実際の生成器を接続

```python
from jlangbase.discovery_loop import start, run_loop, save_new

# writer(request) -> 本文のstr
# reflector(request) -> response_contractに従うdict
# API認証・タイムアウト・モデル指定は利用側で明示的に設定する。
state = start(seed)
result = run_loop(state, writer=writer, reflector=reflector, max_steps=budget)
save_new("output/discovery/session.json", result)
```

max_stepsは費用・処理量の上限。到達判定ではない。反復途中で例外が出た場合は呼び出し元へ伝播する。長いセッションで各段階を確実に保存したい場合はCLI方式、またはnext_request/reflection_request/advance/save_newを1回ずつ呼ぶ。

## 状態と信頼境界

- complete: 到達内容があり、必須の問いを解決し、未執筆計画がない。面白さが保証された意味ではない。
- stalled: 発見・問いの解決・必要な準備がない、または抽出担当が停滞と判断した。
- needs_evidence / fact_conflict: 段落は採用せず、応答を履歴へ保存する。
- budget_exhausted: 安全上限。完成ではない。

事実台帳のハッシュは偶発的変更の検出用であり、悪意ある改ざんに対する署名ではない。本文の意味をPythonだけで照合する機能もない。fact_reviewがconsistentでも、それは指定したレビュー担当の判断にすぎない。引用照合が保証するのは文字列が存在することだけで、発見が妥当かどうかではない。

原稿中で保持したい認識の対立を、事実矛盾と同じ理由で削除しない。任意の問いは終了時に未解決でもよい。新しい事実を発見した場合は停止し、出典確認後に新しいseedとして別セッションを始める。停止したstateを無断でactiveへ書き換えない。

## 今回の実装状況

CLIとPythonの生成ループを追加。外部生成APIの接続、実際の生成実行、テストは未実施。マリオ用seedと設計上の2段階例を同梱したが、実行ログと混同しない。

### 追記: 動作確認済みの範囲（2026-09-07）

実装後にユーザーの承認を受け、既存テスト74件と追加の個別チェック32項目を実行し、すべて成功。CLIの開始・要求出力・段落受理・出力保護と、固定コールバックによる2段落の反復を確認した。実モデルの接続と文章品質の評価は引き続き未実施。詳細は `docs/discovery-loop-spec.md` の実行記録を参照。
