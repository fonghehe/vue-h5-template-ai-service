# 貢献ガイド

## ローカルの検証

Python 3.12–3.14 と uv を使います。既定のテストは隔離した SQLite、Mock モデル・HTTP を使い、実モデルの資格情報は不要です。インフラ未設定時は該当テストをスキップします。

```bash
uv sync --frozen --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
uv run python -m evals.run
```

## 隔離した統合テスト

使い捨て PostgreSQL インスタンスに pgvector と `vh5_ai_test` DB を用意し、隔離した Redis インスタンスの DB 15 を使います。以下の変数を対象インスタンスに設定してください。業務データには接続しないでください。

```bash
export AI_TEST_DATABASE_URL='postgresql+asyncpg://<user>:<password>@<isolated-host>:5432/vh5_ai_test'
export AI_TEST_REDIS_URL='redis://<isolated-host>:6379/15'
DATABASE_URL="$AI_TEST_DATABASE_URL" DATABASE_AUTO_CREATE=false uv run alembic upgrade head
uv run pytest -m integration
```

スキーマ変更時は `uv run alembic upgrade head` と `uv run alembic check` を実行します。`downgrade base` を含む migration 往復は使い捨て DB に限ります。テストは別の DB 名・Redis 番号を拒否しますが、名前だけでは隔離を保証できません。

## ローカルの測定

```bash
uv run python -m scripts.benchmark_hot_paths
```

ベンチマークは合成入力、7 回の計時、`tracemalloc` の割り当てピークを使います。同じスクリプト、Python、マシンで別の checkout を比較し、変更のある作業ツリーを reset しないでください。実モデルや本番スループットの測定ではありません。

## ドキュメント

以下は `docs/` で実行します。文書の開発サーバーは API を起動しません。build は内部ページリンクを検証します。英語・中国語・日本語をそろえて更新してください。

```bash
npm ci
npm run docs:dev
# Validation before publishing:
npm run docs:typecheck
npm run docs:build
```

## PR の前に

`AGENTS.md` に従い、変更した動作をテストし、Provider/SSE 契約を維持します。Service が transaction を管理し、リソース生成直後に終了処理を登録します。契約変更時は三言語の文書も更新します。[拡張ガイド](./extending.md)を参照してください。資格情報、実 JWT、ユーザー文書をコミットしないでください。

CI は PostgreSQL/pgvector、Redis、migration 往復、Python 検証、パッケージ・イメージの build、依存監査を設定しています。文書は VitePress の検証と build 後に Pages に公開します。ローカルの成功はリモート CI やデプロイ完了を示しません。
