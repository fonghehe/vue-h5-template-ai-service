# コントリビューション

コントリビューションに関心をお寄せいただきありがとうございます。このドキュメントはワークフローを説明します。
行動規範は [CODE_OF_CONDUCT.md](https://github.com/fonghehe/vue-h5-template-ai-service/blob/main/CODE_OF_CONDUCT.md)
にあります。

## セットアップ

```bash
git clone https://github.com/fonghehe/vue-h5-template-ai-service.git
cd vue-h5-template-ai-service
cp .env.example .env
uv sync
```

Python 3.12–3.14 と [uv](https://docs.astral.sh/uv/) が必要です。

## 開発コマンド

```bash
make check     # lint + typecheck + test
make lint      # ruff check + ruff format --check
make typecheck # mypy --strict
make test      # pytest
make format    # ruff format + ruff check --fix
```

## コードスタイル

- フォーマットとリントは **ruff**（設定は `pyproject.toml`）で強制されます。
- 型チェックは **mypy を strict モードで**実行します。
- `app/schemas/` のスキーマは `@vh5/ai-chat` との契約です — フィールドのリネームは破壊的変更です。

## プロバイダーの追加

1. `app/providers/` に `ChatProvider` を実装する。
2. `app/providers/factory.py` に登録する。
3. `tests/` にテストを追加する。
4. 設定リファレンスの `AI_PROVIDER` ドキュメントを更新する。

## プルリクエストチェックリスト

1. テストを追加または更新する。
2. ローカルで `make check` を実行してグリーンを維持する。
3. 意図的にバージョニングしない限り、SSE イベント形状とレスポンスエンベロープを変更しない。
4. 表層が変わる場合はドキュメントを更新する。

## リリース

`pyproject.toml` のバージョンを上げ、リリースにタグを付けます。
