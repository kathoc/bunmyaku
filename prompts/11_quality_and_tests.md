全体品質を見直してください。

確認事項:
- pytestが通る
- 例外メッセージが理解しやすい
- Windows/macOS/Linuxで極端に依存しない
- パス操作はpathlib
- 日本語ファイル名でも動く
- DB transactionが壊れにくい
- 同一データの再投入で結果が二重化しない
- 解析runの再現性がある
- profile JSONにschema_versionがある
- READMEに5分で試せるQuick Startがある

さらに10〜20本程度の小さな日本語サンプルを `samples/` に用意し、著作権上問題のない自作文だけを使う。
