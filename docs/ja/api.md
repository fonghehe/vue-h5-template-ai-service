# API リファレンス

ローカル Base URL は `http://localhost:8001` です。通常の JSON 成功とストリーム開始前のエラーは `{"code":0,"message":"ok","data":...,"error":null,"requestId":"..."}` の形で、失敗時は code が 0 以外になります。SSE はこの形式を使いません。レスポンスヘッダーに `X-Request-ID` が付きます。`/docs` と `/openapi.json` は `DOCS_ENABLED=true` の場合のみ公開されます。

| メソッド | パス | 認証 | 応答 |
|---|---|---|---|
| GET | `/health` | 公開 | プロセス生存 |
| GET | `/ready` | 公開 | リミッター準備状態、劣化時 503 |
| GET | `/metrics` | 有効なら公開 | Prometheus、無効なら 404 |
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

作成には任意の `title`（既定 `New conversation`）と `model`（設定済みモデルに限る）を指定できます。メッセージ Body は `content`（1–100000 文字）が必須、`mode: "auto" | "chat" | "agent"`、`useRag: boolean` が任意で、応答は SSE です。詳細は `id`、`userId`、`title`、`model`、`summary`、`createdAt`、`updatedAt`、`messages` を返します。メッセージには `id`、`conversationId`、`role`、`content`、`toolCallId`、`tokenUsage`、`latencyMs`、`citations`、`createdAt` があります。一覧では messages を省略します。[会話](/ja/conversations)へ。

## ナレッジと使用量

```bash
curl -s http://localhost:8001/api/knowledge/documents -H "Authorization: Bearer $AI_USER_JWT" -F 'file=@notes.md' -F 'metadata={"topic":"catalog"}'
curl -s http://localhost:8001/api/usage/me -H "Authorization: Bearer $AI_USER_JWT"
```

登録できるのは txt、md、pdf。`metadata` はフォームに入れた JSON オブジェクト文字列で、既定は `{}`。文書は `id`、`title`、`source`、`metadata`、`createdAt` を返し、一覧/削除は所有者限定です。使用量は `promptTokens`、`completionTokens`、`totalTokens`、`requests` と `byModel`、`byConversation`、`byDate` を返します。旧チャットは含みません。

## エラーと制限

| code | HTTP | 意味 |
|---|---|---|
| 4000 / 4001 | 400 / 422 | 不正リクエスト / Pydantic 検証 |
| 4010 / 4030 / 4040 | 401 / 403 / 404 | 認証 / 所有者 / 存在しない |
| 4090 / 4290 | 409 / 429 | 競合 / クォータ |
| 5000 / 5030 | 500 / 502 | 内部 / Provider 障害 |

検証エラーは値を公開せず、フィールド名だけを示します。旧 API は分単位リクエスト数と同時ストリーム数、保存会話にはその日の記録済みトークン閾値も適用されます。[設定](/ja/configuration)を参照してください。`/ready` はリミッターのみを確認します。
