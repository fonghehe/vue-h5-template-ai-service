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

`/health` はプロセスの生存のみで、接続先は backend 名だけを返します。`/ready` は Redis/limiter と DB を並行して期限付きで確認し、障害時に 503 を返します。モデルや Go サービスは呼びません。Redis の調整が失敗した場合は安全な 503 エンベロープで拒否します。`/metrics` は proxy/network で制限してください。`OTEL_ENABLED` は tracing hook を提供しますが exporter はありません。

Redis を設定するとレプリカ間でリクエスト数、同時ストリーム、会話ロックを共有します。起動後の Redis 障害がすべての操作で自動回復するわけではありません。使用量 API は正常保存された会話ターンのみを数え、請求ではありません。

`.github/workflows/ci.yml` は ruff、mypy、pytest、Docker build を実行し、`deploy-docs.yml` は docs 内の npm で VitePress をビルドして GitHub Pages に公開します。本番文書 base は `/vue-h5-template-ai-service/`、ローカルは `/` です。[設定](/ja/configuration)を参照してください。


## 運用手順

DB 変更は Alembic で管理します。初期 revision は PostgreSQL/pgvector と SQLite をサポートし、追加 `20261002_0002` は ORM index を揃えます。traffic を受ける前に一度 upgrade し、本番 replica ごとに migration を競合実行しません。CI の `alembic check` で差異を確認します。本番 upgrade 前は backup を取り、`downgrade base` は使い捨てテスト DB に限定します。

stream deadline の既定は 90 秒です。Uvicorn graceful shutdown は deadline + 10 秒以上、container stop grace はさらに 10 秒長くします。Compose は `exec uvicorn` で SIGTERM を server に届けます。deadline を変えたら両方の grace period を調整します。

forwarded header を信頼するのは ingress IP/CIDR のみです。例は `--proxy-headers --forwarded-allow-ips=10.0.0.10`。client の X-Forwarded-For を無条件に信用せず、server への直接アクセスを ingress に限定します。旧/版付き chat route の双方に適用します。

```nginx
location /api/ {
    proxy_pass http://ai:8001;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 120s;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

proxy timeout は heartbeat 間隔より長くし、TLS を終端し、設定した Origin/Host だけを許可します。`/metrics` は非公開にします。HTTP metrics は件数、status、全応答時間、active requests を扱い、route template で高 cardinality を防ぎます。log は service/environment/request ID を持ち、Provider/tool へ X-Request-ID を渡します。資格情報は記録しません。使用量は正常完了ターンの概算で請求台帳ではありません。

CI は実 pgvector/Redis と migration 往復を検証します。`make integration` は使い捨て `vh5_ai_test` DB と Redis DB 15 を利用します。モデルは Mock なので実資格情報は不要です。依存監査の例：

```bash
uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/ai-requirements.txt
uvx --from pip-audit==2.10.1 pip-audit --no-deps --disable-pip -r /tmp/ai-requirements.txt
```
