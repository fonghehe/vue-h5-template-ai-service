# クイックスタート

## 必要な環境

API は Python 3.12–3.14 と uv を使います。Node.js/npm は VitePress 文書のためだけに必要です。ルートは `pyproject.toml` と `uv.lock` の Python プロジェクトで、`package.json` と `package-lock.json` は `docs/` の中にあります。ルートに pnpm docs スクリプトはありません。

## オフライン起動

```bash
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload --port 8001
```

デフォルトは Mock Provider と `.data/ai-service.db` の SQLite で、起動時にテーブルを作ります。これはローカル開発用で、本番の PostgreSQL/pgvector 構成ではありません。`DOCS_ENABLED=true` のとき `http://localhost:8001/docs` に OpenAPI UI があります。

```bash
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"こんにちは"}]}'
```

`start`、複数の `delta`、`finish` が返ります。Mock は定型文を返し、実際には質問に答えません。

## 保存される会話

`AI_AUTH_REQUIRED=false` でも、会話とナレッジベースは Go サービスが発行した**ユーザー JWT**を要求します。`SERVICE_TOKEN` ではユーザーデータを操作できません。このサービスは JWT を発行しません。

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"最初の会話"}'
```

返された `data.id` を `POST /api/conversations/{id}/messages` に使います。[会話ガイド](/ja/conversations)を参照してください。

## Compose と検証

`docker compose up --build` は API、Redis、PostgreSQL/pgvector を起動し、Alembic を先に実行します。Compose は `AI_AUTH_REQUIRED=true` なので上記の匿名 curl は 401 になります。Go サービスは含まれません。[デプロイ](/ja/deployment)も参照してください。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs
npm ci
npm run docs:dev
npm run docs:build
```

文書の開発サーバーは API を起動しません。設定は[設定リファレンス](/ja/configuration)へ。
