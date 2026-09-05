# デプロイ

## コンテナとマイグレーション

```bash
docker build -t vue-h5-template-ai-service:local .
docker compose up --build
```

非 root イメージは 8001 で待ち受けます。Compose は Redis 7、PostgreSQL 17 + pgvector、AI API を起動し、Uvicorn の前に `alembic upgrade head` を実行します。認証を有効にし、Mock Provider を使います。埋め込まれた DB パスワードと JWT Secret は**ローカル例**です。Go サービスは含まれず、`host.docker.internal:8002` は外部のプロセスを想定します。Docker Desktop 以外ではホスト設定が必要な場合があります。

本番では PostgreSQL/pgvector と Redis を用意し、`DATABASE_URL=postgresql+asyncpg://...`、`DATABASE_AUTO_CREATE=false` を設定し、起動前に `uv run alembic upgrade head` を実行します。Embedding の次元をマイグレーションとモデルに合わせます。サンプルの秘密値を置換し、実ホストの Trusted Hosts/CORS、`AI_AUTH_REQUIRED=true`、Go と一致する JWT issuer 設定を使います。Go 商品 API が service token と `X-User-ID` を信頼するかは別途確認が必要です。

## プロキシと運用

`/api/ai/chat` と `/api/conversations/{id}/messages` の両方でプロキシのバッファリングを無効にし、十分な読み取りタイムアウトと TLS を設定します。サービスは `X-Accel-Buffering: no` と `Cache-Control: no-cache, no-transform` を送ります。

`/health` はプロセスの生存のみ。`/ready` はリミッターだけを ping して障害時 503 を返し、**DB、モデル、Go サービスは確認しません**。`/metrics` はデフォルト有効かつ内蔵認証なしなので、ネットワーク/プロキシで制限するか無効にします。`OTEL_ENABLED=true` は tracer provider を導入しますが、exporter はありません。

Redis を設定するとレプリカ間でリクエスト数、同時ストリーム、会話ロックを共有します。起動後の Redis 障害がすべての操作で自動回復するわけではありません。使用量 API は正常保存された会話ターンのみを数え、請求ではありません。

`.github/workflows/ci.yml` は ruff、mypy、pytest、Docker build を実行し、`deploy-docs.yml` は docs 内の npm で VitePress をビルドして GitHub Pages に公開します。本番文書 base は `/vue-h5-template-ai-service/`、ローカルは `/` です。[設定](/ja/configuration)を参照してください。
