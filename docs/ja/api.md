# API リファレンス

ローカル Base URL は `http://localhost:8001` です。通常の JSON 成功とストリーム開始前のエラーは `{"code":0,"message":"ok","data":...,"error":null,"requestId":"..."}` の形で、失敗時は code が 0 以外になります。SSE はこの形式を使いません。レスポンスヘッダーに `X-Request-ID` が付きます。`/docs` と `/openapi.json` は `DOCS_ENABLED=true` の場合のみ公開されます。

| メソッド | パス | 認証 | 応答 |
| --- | --- | --- | --- |
| GET | `/health` | 公開 | プロセス生存 |
| GET | `/ready` | 公開 | DB とリミッター準備状態、劣化時 503 |
| GET | `/metrics` | 有効なら公開 | Prometheus、無効なら 404 |
| GET | `/api/ai/suggestions` | — | JSON `string[]` |
| POST | `/api/ai/chat` | 許可時はユーザー/サービス/匿名 | 旧 SSE、非保存 |
| POST、GET | `/api/conversations` | ユーザー JWT | 作成/一覧 |
| GET、DELETE | `/api/conversations/{id}` | 所有者 JWT | 詳細/削除 |
| POST | `/api/conversations/{id}/messages` | 所有者 JWT | 保存 SSE |
| POST、GET | `/api/knowledge/documents` | ユーザー JWT | 登録/一覧 |
| DELETE | `/api/knowledge/documents/{id}` | 所有者 JWT | 削除 |
| GET | `/api/usage/me` | ユーザー JWT | 合計と内訳 |

## 旧チャット

```bash
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"こんにちは"}]}'
```

Body には `messages`（1–100 件）が必要で、`conversationId`（最大 120 文字）は任意です。各メッセージには `role`（`system`、`user`、`assistant`、`tool`）、`content`（最大 20000 文字）、任意の `id`、`createdAt`、`toolCalls`、`toolCallId` があります。`tool` メッセージは `toolCallId` が必要で、空の content には tool call が必要です。合計 content は最大 100000 文字。このルートはクライアントの履歴を使い、保存しません。[SSE](/ja/sse)を参照してください。

## 会話

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"商品相談"}'
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"500円以下の商品を探して","mode":"agent","useRag":false}'
```

作成には任意の `title`（既定 `New conversation`）と `model`（設定済みモデルに限る）を指定できます。メッセージ Body は `content`（1–20000 文字）が必須、`mode: "auto" | "chat" | "agent"`、`useRag: boolean` が任意で、応答は SSE です。詳細は `id`、`userId`、`title`、`model`、`summary`、`createdAt`、`updatedAt`、`messages` を返します。メッセージには `id`、`conversationId`、`sequence`、`role`、`content`、`toolCallId`、`tokenUsage`、`latencyMs`、`citations`、`createdAt` があります。一覧では messages を省略します。[会話](/ja/conversations)へ。

## ナレッジと使用量

```bash
curl -s http://localhost:8001/api/knowledge/documents -H "Authorization: Bearer $AI_USER_JWT" -F 'file=@notes.md' -F 'metadata={"topic":"catalog"}'
curl -s http://localhost:8001/api/usage/me -H "Authorization: Bearer $AI_USER_JWT"
```

登録できるのは txt、md、pdf。`metadata` はフォームに入れた JSON オブジェクト文字列で、既定は `{}`。文書は `id`、`title`、`source`、`metadata`、`createdAt` を返し、一覧/削除は所有者限定です。使用量は `promptTokens`、`completionTokens`、`totalTokens`、`requests` と `byModel`、`byConversation`、`byDate` を返します。旧チャットは含みません。

## エラーと制限

| code               | HTTP            | 意味                           |
| ------------------ | --------------- | ------------------------------ |
| 4000 / 4001        | 400 / 422       | 不正リクエスト / Pydantic 検証 |
| 4010 / 4030 / 4040 | 401 / 403 / 404 | 認証 / 所有者 / 存在しない     |
| 4090 / 4290        | 409 / 429       | 競合 / クォータ                |
| 5000 / 5030        | 500 / 502       | 内部 / Provider 障害           |

`/health` はプロセスの生存のみで、接続先は backend 名だけを返します。`/ready` は Redis/limiter と DB を並行して期限付きで確認し、障害時に 503 を返します。モデルや Go サービスは呼びません。Redis の調整が失敗した場合は安全な 503 エンベロープで拒否します。`/metrics` は proxy/network で制限してください。`OTEL_ENABLED` は tracing hook を提供しますが exporter はありません。

一覧は `page`（1–100000）と `page_size`（1–100、既定 50）を受け取り、既存の配列エンベロープを保ちます。会話詳細は既定で最新 100 件を返し、`page_size` と `before=<sequence>` で以前のページを取得します。メッセージに `sequence` が追加されます。コンテキストは最新 200 件まで、要約入力にも上限があります。最新 user message を維持し、大きすぎる入力は拒否します。保存メッセージは 20000 文字と context budget の制限を受けます。旧 `/api/*` と `/api/v1/*` の両方が利用できます。

## 開始用プロンプト API

公開 JSON API の `GET /api/ai/suggestions` は、標準の応答形式で三つの固定プロンプトを返します。モデル呼び出し、モデルキー、トークン消費、会話保存、ストリーム用の同時実行リースは不要です。`/api/v1/ai/suggestions` も同じ API です。SSE ではありません。

任意の `locale` は `en-US`、`zh-CN`、`ja-JP` のみを受け付け、既定は `en-US` です。`zh-TW` を含む他の値は HTTP 422、業務コード 4001 を返します。クライアント側で送信前に変換します。`Accept-Language` では選択しません。

```bash
curl -s 'http://localhost:8001/api/ai/suggestions'
curl -s 'http://localhost:8001/api/v1/ai/suggestions?locale=ja-JP'
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    "Help me compare products before buying.",
    "What should I check before placing an order?",
    "Explain how streaming AI responses work."
  ],
  "error": null,
  "requestId": "example-request-id"
}
```

文言は `app/services/suggestions.py`、HTTP 検証と包装は `app/api/v1/suggestions.py` にあります。言語追加時は Literal、フロントエンドの OpenAPI enum、テストをそろえ、各言語の文言を個別に調整してください。共有 tuple を変更できないよう、新しい list を返します。ユーザー履歴からの個別推薦は行いません。

[テスト](./extending.md)
