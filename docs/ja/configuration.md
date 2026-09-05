# 設定リファレンス

`app/core/config.py` の `Settings` は環境変数と任意の `.env` を読みます。配布されるのは **`.env.example` のみ**で、`.env.development` や `.env.production` はありません。未知のキーは無視します。

| 分類 | 実在する変数とデフォルト |
|---|---|
| サービス | `APP_ENV=development`、`DEBUG=false`、`DOCS_ENABLED=true`、`LOG_LEVEL=INFO`、`LOG_FORMAT=text` |
| HTTP | `CORS_ORIGINS` は localhost:5173、`TRUSTED_HOSTS` は localhost、127.0.0.1、testserver |
| DB | `DATABASE_URL=sqlite+aiosqlite:///./.data/ai-service.db`、`DATABASE_AUTO_CREATE=true` |
| セキュリティ | `SERVICE_TOKEN` 未設定、`AI_AUTH_REQUIRED=false`、`JWT_SECRET` 開発用値、`JWT_ISSUER=vue-h5-template`、`JWT_AUDIENCE=vue-h5-template-api` |
| Provider | `AI_PROVIDER=mock`、`AI_BASE_URL=https://api.openai.com/v1`、`AI_API_KEY` 未設定、`AI_MODEL=gpt-4o-mini`、`AI_TIMEOUT_SECONDS=60` |
| 入力/再試行 | `AI_MAX_OUTPUT_CHARS=20000`、`AI_MAX_INPUT_CHARS=100000`、`AI_CONTEXT_TOKEN_BUDGET=8000`、`AI_SUMMARY_TOKEN_BUDGET=1000`、`AI_PROVIDER_MAX_RETRIES=3`、`AI_RETRY_BASE_SECONDS=0.25` |
| ルーティング | `MODEL_SIMPLE_CHAT`、`MODEL_REASONING`、`MODEL_SUMMARIZATION` は未設定なら `AI_MODEL`、`MODEL_EMBEDDING=text-embedding-3-small`、`EMBEDDING_DIMENSIONS=1536` |
| Agent/Go | `AGENT_MAX_ITERATIONS=5`、`BUSINESS_SERVICE_URL=http://localhost:8002`、`BUSINESS_SERVICE_TOKEN` 未設定、`BUSINESS_SERVICE_TIMEOUT_SECONDS=5` |
| ナレッジ | `KNOWLEDGE_MAX_FILE_BYTES=5000000`、`KNOWLEDGE_CHUNK_CHARS=1200`、`KNOWLEDGE_CHUNK_OVERLAP_CHARS=200`、`KNOWLEDGE_TOP_K=5` |
| 制限 | `AI_RATE_LIMIT_PER_MINUTE=20`、`AI_CONCURRENT_STREAM_LIMIT=3`、`AI_DAILY_TOKEN_LIMIT=200000`、`REDIS_URL` 未設定 |
| 観測 | `METRICS_ENABLED=true`、`OTEL_ENABLED=false`、`OTEL_SERVICE_NAME=vue-h5-template-ai-service` |

JWT は HS256、`exp`、`iat`、`sub`、issuer、audience を確認します。保存データには常にユーザー JWT が必要です。`APP_ENV=production` は DEBUG/docs 無効、JSON ログ、設定済み `SERVICE_TOKEN`、開発用でない JWT Secret、PostgreSQL async URL、自動テーブル作成無効、ワイルドカード CORS 禁止を要求します。OpenAI-compatible なら API Key も必要です。**本番検証は `AI_AUTH_REQUIRED=true` を強制しません**。公開前に設定してください。Embedding モデル/次元を変えても既存ベクトルは自動再索引されません。[デプロイ](/ja/deployment)も参照してください。
