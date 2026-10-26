# デプロイ

## ローカルのコンテナ構成

`docker compose up --build` は API（`127.0.0.1:8001`）、Redis 7、PostgreSQL 17/pgvector を起動します。Uvicorn の前に migration を実行し、Mock モデルとチャット認証を使います。付属の資格情報はローカル用です。Go サービスは別途起動します。`host.docker.internal:8002` には Docker Desktop または同等のホスト設定が必要です。

## 本番の起動

1. PostgreSQL/pgvector と Redis を用意し、秘密値はデプロイ環境で管理します。
2. [設定](./configuration.md)に従い、staging/production と `DATABASE_AUTO_CREATE=false` を設定します。JWT secret・issuer・audience を Go と一致させ、必要なら実 Provider を設定します。
3. 既存データをバックアップし、レプリカ起動前に一度だけ migration を実行します。各レプリカで競合実行しないでください。
4. 起動後に `/health` と `/ready` を確認し、Go 商品 API の service token と `X-User-ID` の認可方針を別途検証します。

```bash
uv run alembic upgrade head
uv run alembic check
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --timeout-graceful-shutdown 100
```

## プロキシと終了処理

入口で TLS を終端します。旧チャットと `/api/v1` の両方でバッファリングを無効にし、読み取りタイムアウトを heartbeat 間隔より長くします。転送ヘッダーは入口の IP/CIDR だけを信頼します。例は `--proxy-headers --forwarded-allow-ips=10.0.0.10` です。入口を迂回する直接アクセスも制限してください。

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

Uvicorn の終了猶予は stream deadline より 10 秒以上長く、コンテナの停止猶予はさらに 10 秒長くします。既定は 90 / 100 / 110 秒です。変更時はまとめて調整します。Compose は `exec uvicorn` で SIGTERM をサーバーに届けます。

## ヘルスチェックと可観測性

| エンドポイント | 意味 |
|---|---|
| `/health` | プロセスの生存のみを示し、依存先の正常性は保証しません。 |
| `/ready` | DB とリミッターを並行して期限付きで確認し、障害時は 503。モデルや Go は呼びません。 |
| `/metrics` | 有効時は Prometheus 指標を公開します。プロキシ・ネットワークでアクセスを制限してください。 |

HTTP 指標はルートテンプレートと標準メソッドを使い、その他は `OTHER` に集約します。ログは request ID を含み、Provider/ツールへ `X-Request-ID` を転送します。例外ログは型とスタック位置を保持し、例外値とチェーンのメッセージを省略します。ログ本文と追加フィールドにも秘密を含めないでください。

`OTEL_ENABLED` は追跡を設定しますが exporter は付属しません。観測基盤に合わせて exporter と sampling を構成してください。設定を有効にするだけでは trace は送信されません。

## 運用上の制約

- 日次使用量は保存済みの完了ターンの概算で、請求台帳ではありません。同時リクエストで受付しきい値を超える場合があります。
- PDF は並行数を制限したスレッドで解析し、プロセス分離は行いません。大規模な未信頼アップロードにはリソース制限付き解析プロセスや Worker が必要です。
- 既定の pool・制限値は出発点であり、実証済みの本番容量ではありません。モデル、Go、プロキシ切断、バックアップ、ローリング終了を対象環境で検証してください。

隔離した統合テスト、migration 検証、ローカルベンチマークは[貢献ガイド](./contributing.md)を参照してください。
