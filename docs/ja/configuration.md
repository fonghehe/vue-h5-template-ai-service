# 設定

すべての設定は環境変数から読み込まれます（必要に応じて `.env` ファイルで補完できます）。設定は先行的に検証されます：
安全でない組み合わせは、最初のリクエストではなく起動時に失敗します。

## 全リファレンス

| 変数 | デフォルト | 説明 |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `test` \| `production`。 |
| `DEBUG` | `false` | FastAPI のデバッグモード。 |
| `DOCS_ENABLED` | `true` | `/docs`、`/redoc`、`/openapi.json` を配信。 |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`。 |
| `LOG_FORMAT` | `text` | ローカル開発は `text`、本番では `json`（必須）。 |
| `CORS_ORIGINS` | `http://localhost:5173,…` | カンマ区切りのブラウザオリジン許可リスト。 |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,testserver` | 許可する `Host` ヘッダーの値。 |
| `SERVICE_TOKEN` | — | ゲートウェイ→サービスの共有シークレット。本番では必須。 |
| `AI_AUTH_REQUIRED` | `false` | `true` にすると匿名アクセスを拒否。 |
| `JWT_SECRET` | dev placeholder | ビジネスサービスと**必ず**一致させる。 |
| `JWT_ISSUER` | `vue-h5-template` | ビジネスサービスと一致させる。 |
| `JWT_AUDIENCE` | `vue-h5-template-api` | ビジネスサービスと一致させる。 |
| `AI_PROVIDER` | `mock` | `mock` \| `openai-compatible`。 |
| `AI_BASE_URL` | `https://api.openai.com/v1` | 任意の OpenAI 互換エンドポイント。 |
| `AI_API_KEY` | — | `openai-compatible` では必須。 |
| `AI_MODEL` | `gpt-4o-mini` | プロバイダーに送るモデル。 |
| `AI_TIMEOUT_SECONDS` | `60` | プロバイダーのタイムアウト（0–300）。 |
| `AI_MAX_OUTPUT_CHARS` | `20000` | 1 ターンの上限（文字数）。 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` | アイデンティティごと、毎分。 |
| `REDIS_URL` | — | 空 = プロセス内リミッター。複数インスタンス実行時に設定。 |

## 本番環境での検証

`APP_ENV=production` の場合、起動は以下を満たさない限り実行を拒否します：

- `DEBUG` が `false`、かつ `DOCS_ENABLED` が `false`。
- `LOG_FORMAT` が `json`。
- `SERVICE_TOKEN` が設定済み。
- `JWT_SECRET` がデフォルトのプレースホルダーではない。
- `AI_PROVIDER=openai-compatible` の場合 `AI_API_KEY` が設定済み。
- `CORS_ORIGINS` に `*` が含まれない。

さらに、`JWT_SECRET` がプレースホルダーのまま `AI_AUTH_REQUIRED` を有効化するのは拒否されます — さもなければ誰でも
サービスが受け入れるトークンを発行できてしまいます。

## 認証モデル

三種類の呼び出し元が、優先順位順に認識されます：

1. **service** — `SERVICE_TOKEN` を提示する信頼済みゲートウェイ。
2. **user** — ビジネスサービスが発行した JWT（`HS256`、issuer/audience/expiry を強制）。
3. **anonymous** — `AI_AUTH_REQUIRED` が `false` の間のみ許可。
