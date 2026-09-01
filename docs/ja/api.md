# API リファレンス

AI サービスは三つのエンドポイントを公開します。非ストリーミング応答（およびストリーム前のエラー）は、Go の
ビジネスサービスと同じエンベロープを使います。

## レスポンスエンベロープ

```jsonc
{ "code": 0,     "message": "ok", "data": { "…": "…" }, "error": null, "requestId": "…" }
{ "code": 4010,  "message": "Authentication required", "data": null, "error": null, "requestId": "…" }
```

`code === 0` が成功を意味します — `@vh5/api-client` が取るのと同じ分岐です。

## エンドポイント

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| `GET` | `/health` | — | ライブネスプローブ。依存関係には一切触れません。 |
| `GET` | `/ready` | — | レディネスプローブ。リミッターの健全性を報告。 |
| `POST` | `/api/ai/chat` | 任意 | チャット補完を Server-Sent Events としてストリーミング。 |

### POST /api/ai/chat

**ボディ**

```jsonc
{
  "messages": [
    { "role": "user", "content": "Why is streaming useful?", "id": "…", "createdAt": 1700000000 }
  ],
  "conversationId": "conversation-9f2c…" // 任意
}
```

- `role` は `system` | `user` | `assistant`。
- `messages` は 1–100 件必要。各 `content` は 20 000 文字が上限。
- `id` と `createdAt` は受け付けますが必須ではありません。

**レスポンス** — [SSE 契約](/ja/sse) に従う `text/event-stream`。

### GET /health

```jsonc
{
  "code": 0,
  "message": "ok",
  "data": {
    "service": "ai",
    "status": "ok",
    "env": "development",
    "version": "1.0.0",
    "provider": "mock",
    "rateLimiter": "memory"
  },
  "error": null,
  "requestId": "…"
}
```

### GET /ready

`/health` と同じ形状で、レートリミッターが健全なら `status` は `ready`、それ以外は `degraded`（HTTP 503）になります。
チャットではフェイルオープンしますが、オーケストレーターは劣化したリミッターを不健全と扱うべきです。

## エラーコード

| コード | 意味 | HTTP |
|---|---|---|
| `0` | 成功 | 200 |
| `4000` | 不正なリクエスト | 400 |
| `4001` | バリデーション失敗 | 422 |
| `4010` | 未認証 | 401 |
| `4030` | 禁止 | 403 |
| `4040` | 見つからない | 404 |
| `4090` | 競合 | 409 |
| `4290` | レート制限 | 429 |
| `5000` | 内部エラー | 500 |
| `5030` | プロバイダー利用不可 | 502 |

バリデーションエラーはフィールド**名**のみを公開し、提出された値（認証情報や個人情報を含み得る）は決して公開しません。

## レート制限

各呼び出し元はアイデンティティでクォータ管理されます：

- 認証済みの呼び出し元 — JWT の subject ごと；
- 匿名の呼び出し元 — クライアント IP ごと（共有 NAT で一人が他者のクォータを使い果たさないように）。

上限は毎分 `AI_RATE_LIMIT_PER_MINUTE` です。`REDIS_URL` 未設定ならカウンターはプロセス内です。複数レプリカを動かす
場合は `REDIS_URL` を設定してください。
