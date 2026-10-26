# 設定リファレンス

既定値と検証規則は `app/core/config.py` を参照してください。環境変数は `.env` より優先され、未知のキーは無視されます。ローカルでは `.env.example` をコピーし、実際の資格情報はコミットしないでください。時間の単位は秒、サイズは変数名に応じてバイトまたは文字数です。

## HTTP モデルへの接続

Provider URL、キー、モデルをバックエンド環境に設定します。資格情報をフロントエンドの `VITE_*` に置かないでください。タスク別 `MODEL_*` は未設定なら `AI_MODEL` を使い、Embedding は専用モデルを使います。タイムアウトと再試行は [SSE](./sse.md)を参照してください。

```dotenv
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=<provider-key>
AI_MODEL=<model-id>
```

## Provider と配信

| 変数 | 既定値 |
|---|---|
| `AI_PROVIDER` | `mock` |
| `AI_BASE_URL` | `https://api.openai.com/v1` |
| `AI_MODEL` | `gpt-4o-mini` |
| `AI_TIMEOUT_SECONDS` | `60` |
| `AI_STREAM_TIMEOUT_SECONDS` | `90` |
| `SSE_HEARTBEAT_SECONDS` | `15` |
| `AI_MAX_INPUT_CHARS` | `100000` |
| `AI_MAX_OUTPUT_CHARS` | `20000` |
| `AI_CONTEXT_TOKEN_BUDGET` | `8000` |
| `AI_SUMMARY_TOKEN_BUDGET` | `1000` |
| `AI_PROVIDER_MAX_RETRIES` | `3` |
| `AI_RETRY_BASE_SECONDS` | `0.25` |
| `MODEL_SIMPLE_CHAT` | 未設定 |
| `MODEL_REASONING` | 未設定 |
| `MODEL_SUMMARIZATION` | 未設定 |
| `MODEL_EMBEDDING` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `1536` |
| `AI_API_KEY` | 未設定 |

## 認証と制限

| 変数 | 既定値 |
|---|---|
| `AI_AUTH_REQUIRED` | `false` |
| `JWT_SECRET` | `dev-only-change-me-before-production` |
| `JWT_ISSUER` | `vue-h5-template` |
| `JWT_AUDIENCE` | `vue-h5-template-api` |
| `SERVICE_TOKEN` | 未設定 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` |
| `AI_CONCURRENT_STREAM_LIMIT` | `3` |
| `AI_DAILY_TOKEN_LIMIT` | `200000` |

## データベースと Redis

| 変数 | 既定値 |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./.data/ai-service.db` |
| `DATABASE_AUTO_CREATE` | `true` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `10` |
| `DATABASE_POOL_TIMEOUT` | `10` |
| `DATABASE_POOL_RECYCLE` | `1800` |
| `REDIS_URL` | 未設定 |
| `REDIS_MAX_CONNECTIONS` | `50` |

## ツールと文書

| 変数 | 既定値 |
|---|---|
| `AGENT_MAX_ITERATIONS` | `5` |
| `BUSINESS_SERVICE_URL` | `http://localhost:8002` |
| `BUSINESS_SERVICE_TOKEN` | 未設定 |
| `BUSINESS_SERVICE_TIMEOUT_SECONDS` | `5` |
| `KNOWLEDGE_MAX_FILE_BYTES` | `5000000` |
| `KNOWLEDGE_CHUNK_CHARS` | `1200` |
| `KNOWLEDGE_CHUNK_OVERLAP_CHARS` | `200` |
| `KNOWLEDGE_TOP_K` | `5` |

## サービスと HTTP

| 変数 | 既定値 |
|---|---|
| `APP_ENV` | `development` |
| `DEBUG` | `false` |
| `DOCS_ENABLED` | `true` |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `text` |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,testserver` |
| `MAX_REQUEST_BYTES` | `6000000` |
| `READINESS_TIMEOUT_SECONDS` | `3` |
| `METRICS_ENABLED` | `true` |
| `OTEL_ENABLED` | `false` |
| `OTEL_SERVICE_NAME` | `vue-h5-template-ai-service` |

## JWT と本番設定

ユーザー JWT は Go 発行の access token が必要です。HS256、有効な issuer/audience、`exp`、`iat`、`sub`、ペイロードの `typ="access"` を検証します。refresh token や型の欠落は 401 です。`SERVICE_TOKEN` は内部サービスのステートレスチャット用であり、ユーザー所有データには使えません。

`APP_ENV` は `local`、`development`、`test`、`staging`、`production` を受け付けます。staging/production は認証、Redis、非同期 PostgreSQL、auto-create/debug/docs 無効、JSON ログ、明示的なホスト、ワイルドカードのない CORS が必須です。JWT/service 秘密値は 32 バイト以上とし、JWT の開発用値を拒否します。HTTP Provider はキーと HTTPS が必要です。[デプロイ](./deployment.md)を参照してください。

`AI_DAILY_TOKEN_LIMIT` は保存済みの完了ターンを確認するしきい値で、原子的な日次予約や請求台帳ではありません。Embedding モデル・次元の変更時には再生成を計画してください。既存ベクトルは自動変換されません。
