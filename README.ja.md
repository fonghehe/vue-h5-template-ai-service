# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

[vue-h5-template](https://github.com/fonghehe/vue-h5-template) 向けの FastAPI AI アシスタントバックエンドです。`POST /api/ai/chat` と `@vh5/ai-chat` の SSE 契約を維持しながら、ユーザー所有の会話、制限付きコンテキスト、登録済みツール、必要な場合だけ使う LangGraph Agent、PostgreSQL/pgvector による文書検索、使用量・可観測性 API を提供します。

このリポジトリは Python サービスであり、Vue フロントエンドではありません。別の Go ビジネスサービスが JWT の発行と商品 CRUD を担当し、このサービスは固定された登録済みツールを通じて商品 API を呼びます。デフォルトの Mock モデルはオフラインで動きますが、実モデルの回答品質を示すものではありません。

## クイックスタート

```bash
cp .env.example .env
uv sync --dev
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

## ライセンス

[MIT](./LICENSE)
