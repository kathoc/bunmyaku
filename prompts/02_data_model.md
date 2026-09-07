SQLite中心のデータモデルを実装してください。

最低限のテーブル:
- documents
- sentences
- tokens
- ngrams
- document_metrics
- expression_stats
- style_profiles
- runs

`documents` には最低限以下を持たせる:
- id
- collected_at
- published_at nullable
- source_type
- platform nullable
- topic nullable
- author_type nullable
- edited nullable
- source_ref nullable
- text_hash
- raw_text

要件:
- 同一text_hashの重複投入を防ぐ。
- run_idで解析実行単位を追跡できる。
- schema migrationは最初は独自の単純なversion管理でよい。
- DB操作を1モジュールに集中させる。
- テストを付ける。
