# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

[vue-h5-template](https://github.com/fonghehe/vue-h5-template) 向けの FastAPI AI アシスタントバックエンドです。`POST /api/ai/chat` と `@vh5/ai-chat` の SSE 契約を維持しながら、ユーザー所有の会話、制限付きコンテキスト、登録済みツール、必要な場合だけ使う LangGraph Agent、PostgreSQL/pgvector による文書検索、使用量・可観測性 API を提供します。

このリポジトリは Python サービスであり、Vue フロントエンドではありません。別の Go ビジネスサービスが JWT の発行と商品 CRUD を担当し、このサービスは固定された登録済みツールを通じて商品 API を呼びます。デフォルトの Mock モデルはオフラインで動きますが、実モデルの回答品質を示すものではありません。

## クイックスタート

```bash
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn app.main:app --reload --port 8001
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"こんにちは"}]}'
```

デフォルトは SQLite と Mock Provider です。ローカルの PostgreSQL/pgvector + Redis 構成は `docker compose up --build` で起動します。Compose ではチャットに認証が必要で、保存されるユーザーデータにはユーザー JWT が必要です。Go サービスは別途起動します。

## ドキュメント

[日本語開発ガイド](https://fonghehe.github.io/vue-h5-template-ai-service/ja/)にアーキテクチャ、API、SSE、会話、ツールと RAG、設定、デプロイ、拡張方法をまとめています。[文書ソース](./docs/ja/index.md)も参照できます。ローカルプレビューは `cd docs && npm ci && npm run docs:dev`。ルートには pnpm docs スクリプトはありません。

## チェック

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs && npm run docs:typecheck && npm run docs:build
```

## アーキテクチャと保守

Python 3.12–3.14 に対応し、uv で FastAPI/Pydantic v2、SQLAlchemy 2 async、Alembic、Redis、httpx を固定します。HTTP route は小さな Service を呼び、Repository は flush のみ、Service が transaction を管理します。lifespan は起動途中の失敗でも pool を閉じます。旧 `/api/*` と `/api/v1/*` の両方を利用できます。[監査と変更計画](./ARCHITECTURE_REVIEW.md)、[実際の検証結果](./ENGINEERING_REPORT.md)も参照してください。

## データベースとデプロイ

ローカル SQLite は自動作成を利用でき、本番は PostgreSQL/pgvector、Redis、明示的 migration を使います。

```bash
uv run alembic upgrade head
uv run alembic check
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

起動前に環境変数を設定します。staging/production は認証、強い秘密値、Redis、明示的 host、JSON log、docs 無効、`DATABASE_AUTO_CREATE=false` が必須です。デプロイ時に migration を一度実行してから replica を起動します。multi-stage image は非 root で動作します。SSE buffering を無効にし、信頼する proxy IP を限定し、stream deadline より長い shutdown grace period を設定します。[デプロイ手順](./docs/ja/deployment.md)に具体例があります。JWT 発行は Go サービスにあり、ユーザー・注文・パスワード管理を重複実装しません。

既定のテストは独立した SQLite と Mock HTTP/model を使います。実インフラテストには、使い捨て `vh5_ai_test` DB を指す `AI_TEST_DATABASE_URL` と Redis DB 15 の `AI_TEST_REDIS_URL` を設定し、`uv run pytest -m integration` を実行します。CI は必要なインフラと migration 往復検証を提供します。実モデル品質、Go 接続、tracing exporter、正確な請求は別途検証が必要です。

## ライセンス

[MIT](./LICENSE)
