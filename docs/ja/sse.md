# SSE 契約

`POST /api/ai/chat` は `text/event-stream` を返し、そのイベントは `@vh5/ai-chat` が消費する `ChatChunk` ユニオンと
正確に一致します。

| `type` | フィールド | 意味 |
|---|---|---|
| `start` | `id` | ストリーム受理。会話 ID を運びます。 |
| `delta` | `delta` | テキストの断片 1 つ。順番に連結します。 |
| `finish` | `reason` | 終端イベント：`stop`、`abort`、`error`。 |
| `error` | `message` | ストリーミング開始後の失敗。クライアントが例外を投げます。 |

各フレームはコンパクトな JSON を運ぶ単一の `data:` 行です：

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"finish","reason":"stop"}
```

## 終了理由

- `stop` — プロバイダーが正常に完了。
- `abort` — クライアントがストリーム途中で切断。未読のトークンに課金されないよう、サービスは即座に停止します。
- `error` — クライアントライブラリで `FinishChunk` の reason を通じて報告される失敗用に予約。この場合サービス自体が
  `error` イベントを発行します。

## エラー処理 — ストリームの前 vs 途中

- 最初のバイトより**前**に発生したエラーは、適切な HTTP ステータスとアプリケーションコードを持つ通常の JSON エラー
  エンベロープとして返されます。
- ストリーム**途中**で発生したエラーは、HTTP ステータスがすでに送信済みのため `error` イベントになります。

## ヘッダー

レスポンスは、中継装置がストリームをバッファリングするのを防ぐヘッダーを設定します：

```
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

nginx でサービスを前面に置く場合は、`proxy_buffering off;` も設定してください — [デプロイ](/ja/deployment) を参照。
