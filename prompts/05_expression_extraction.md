表現抽出機能を実装してください。

対象:
- 1〜5 token n-gram
- 文末2〜6 token
- 文頭2〜5 token
- 接続表現候補
- 助詞・助動詞を含む定型句

重要:
単純な高頻度語だけを出さない。ジャンル内部の頻度と文書カバレッジを分離する。

各表現について最低限:
- expression
- token_length
- count
- documents_count
- per_10k_tokens
- source_type
- period

を保存する。

ノイズ削減:
- 記号だけ
- 1文字だけの一般的助詞
- URL断片
- 数字列だけ
を除外できるようにする。

CLIで上位表現を確認できるようにする。
