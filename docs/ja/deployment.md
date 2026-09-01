# デプロイ

## イメージのビルド

```bash
docker build -t vue-h5-template-ai-service:latest .
# または
make docker
```

イメージは**非 root** ユーザーとして動作し、コンテナのヘルスチェックを含みます。

## docker compose で実行

```bash
cp .env.example .env
docker compose up --build
```

サービスと Redis 7 インスタンス（複数インスタンスのレート制限用）が起動します。API は `http://localhost:8001` で
待ち受けます。

## ストリーミング特有の注意点

SSE はプロキシのバッファリングの影響を受けやすいです。nginx などでサービスを前面に置く場合：

```nginx
location /api/ai/chat {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
}
```

サービスはすでに `X-Accel-Buffering: no` と `Cache-Control: no-cache, no-transform` を送信し、中継装置がストリームを
バッファリング・再圧縮するのを防ぎます。

## 本番チェックリスト

- **`SERVICE_TOKEN` を設定**し、ゲートウェイと一緒にローテーションする。
- **`JWT_SECRET` を置き換え**、ビジネスサービスと同一に保つ。
- サービスを公開する前に **`AI_AUTH_REQUIRED=true` を設定**。
- **`AI_PROVIDER=openai-compatible`** を実際の `AI_API_KEY` と共に使う。
- 複数レプリカを動かす場合は **`REDIS_URL` を設定** — さもないと各レプリカが独自のクォータを保持します。
- **TLS を上流で終端**し、`CORS_ORIGINS` を実際のドメインに設定。
- 本番では **`DOCS_ENABLED=false` を設定**。

## CI

GitHub Actions は `main` へのすべての PR と push で実行されます：`ruff check`、`ruff format --check`、`mypy app`、
カバレッジ付き `pytest`、Docker イメージビルド。
