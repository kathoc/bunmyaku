このリポジトリの最小構成を作ってください。

要件:
- Python 3.11+
- パッケージ名 `jlangbase`
- `pyproject.toml`
- `src/jlangbase/`
- `tests/`
- `samples/`
- `data/raw/`, `data/processed/`, `output/`
- `docs/decisions.md`
- `.gitignore`
- CLIエントリポイントを用意

依存候補:
- sudachipy
- sudachidict_core

ただし依存は必要最小限にしてください。最初のコミット相当では `python -m jlangbase --help` が動くところまで作ってください。
