# SSE プロトコル

両方のチャット API は `text/event-stream` を返し、各フレームは `data:` 行にコンパクト JSON を載せます。名前付き `event:` は使いません。旧 `POST /api/ai/chat` は `@vh5/ai-chat` の 4 種類を維持します。

| 型 | フィールド | 経路 |
|---|---|---|
| `start` | `id` | 両方 |
| `delta` | `delta` テキスト | 両方 |
| `finish` | `reason` | 両方 |
| `error` | `message` | 両方 |
| `thinking_status` | ユーザーに表示可能な `status` | 保存経路 |
| `tool_start`、`tool_result` | `tool`、`callId`、任意の `result` | Agent |
| `sources` | 出典配列 | RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"こんにちは"}

data: {"type":"finish","reason":"stop"}

```

正常時は `finish: stop` です。schema は `abort` と `error` の reason を許しますが、現行ルートは失敗時に `error` イベントを送ります。切断したクライアントは通常、終端フレームを受け取りません。追加イベントは保存経路にのみあり、旧 API には出ません。

JSON POST と Authorization を使うため `fetch` を利用します。標準 `EventSource` ではこのリクエスト形式を送れません。画面を閉じるときは fetch を中断してください。`cancel_aware_stream` は直接 Provider の待機中の読み取りをキャンセルし、反復子を閉じます。Agent は進捗を送りますが、回答本文はグラフ完了後に分割します。

配信前の入力/認証/制限エラーは HTTP ステータスと JSON エンベロープ、開始後は SSE の `error` になります。`Cache-Control: no-cache, no-transform` と `X-Accel-Buffering: no` が付くので、プロキシでは両チャット経路のバッファリングを無効にしてください。[デプロイ](/ja/deployment)を参照してください。
