# 収集コネクタは本文と出典だけを渡す

外部サービスへの接続は未実装です。将来のコネクタは以下の共通形式を返し、解析・集計は既存の処理へ委ねます。RSS、公開API、手動エクスポートしたXデータ、自分のnote投稿、YouTube字幕、利用許諾のあるニュース配信を想定します。

```python
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping, Protocol

@dataclass(frozen=True)
class SourceDocument:
    raw_text: str
    source_ref: str
    metadata: Mapping[str, object]
    retention: Literal["raw_allowed", "statistics_only"]

class Connector(Protocol):
    def collect(self) -> Iterable[SourceDocument]: ...
```

`source_ref`は必須です。metadataには取得日時、公開日時、取得方法、利用条件を確認した記録を含めます。本文を取得できても保存できるとは限らないため、保存方針を文書単位で渡します。

現行DBは本文保持を前提にしています。`statistics_only`を扱う前に、本文を永続化せず集計へ渡す処理と、集計の再現性が制限される旨の記録が必要です。今の投入処理へそのまま流す設計は採りません。

| 取得経路 | 実装前に確認すること |
| --- | --- |
| RSS・公開API | 配信範囲、利用条件、取得間隔、本文保存の可否 |
| 手動エクスポート | エクスポート形式、他者の投稿の扱い、出典ID |
| 自分の投稿 | 著作権と投稿サービス側の取得条件 |
| YouTube字幕 | 字幕の取得権限、提供形式、動画と時間位置の出典 |
| ニュース配信 | 契約で許される本文・統計の保存範囲 |

robots.txtや利用規約を無視した取得は前提にしません。APIキーは環境変数または権限を制限した設定ファイルから読み、コード・DB・解析記録へ保存しません。実接続時には対象サービスの公式資料を確認します。
