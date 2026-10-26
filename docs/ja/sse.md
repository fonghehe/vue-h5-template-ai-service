# SSE プロトコル

クライアントは `fetch` で JSON を POST し、応答を SSE として読み取ります。両チャット API は `text/event-stream` を返します。各イベントは `data:` に続く JSON と空行で構成し、名前付き `event:` フィールドは使いません。

## イベント

| 型 | フィールド | 対象 |
|---|---|---|
| `start` | `id` | 両チャット API |
| `delta` | `delta` | 両チャット API |
| `finish` | `reason` | 両チャット API |
| `error` | `message`, `code?`, `requestId?` | 両チャット API |
| `thinking_status` | `status` | 保存する会話のみ |
| `tool_start` | `tool`, `callId` | Agent モードのみ |
| `tool_result` | `tool`, `callId`, `result` | Agent モードのみ |
| `sources` | `sources[]` | RAG のみ |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"Hello"}

data: {"type":"finish","reason":"stop"}

```

## 完了とエラー

成功時は `start`、0 個以上の `delta`、最後に `reason="stop"` の `finish` を一つ送ります。配信開始後に失敗した場合は `error` を送ります。どちらかの終端イベントで読み取りを終了してください。schema は `abort` と `error` の finish reason も許しますが、現在のルートは送信しません。

配信前の認証・検証・受付制限エラーは HTTP エラーと標準 JSON 形式で返します。切断時は終端イベントを受け取れない場合があります。delta 受信後の POST 自動再送は、会話ターンやツール操作の重複につながるため避けてください。

## タイムアウト・heartbeat・再試行

| 設定 | 既定値 | 動作 |
|---|---|---|
| `AI_TIMEOUT_SECONDS` | 60 秒 | HTTP Provider の通信タイムアウト。各ストリーム試行では最初の内容 token と後続 token の待機も制限します。コメントや空の delta は期限を更新しません。 |
| `AI_STREAM_TIMEOUT_SECONDS` | 90 秒 | コンテキスト、ツール、保存、クライアントの背圧を含む期限。HTTP 送信の終了にはさらに 5 秒の猶予があります。 |
| `SSE_HEARTBEAT_SECONDS` | 15 秒 | 処理待機中に `: heartbeat` コメントを送信します。JSON イベントでもモデル token でもありません。 |

OpenAI 互換アダプターは `[DONE]` または空でない `finish_reason` を正常終端として扱います。どちらもない EOF はエラーです。usage のみのチャンクも受け付けます。一時的な障害は最初の内容 delta より前だけ、`AI_PROVIDER_MAX_RETRIES` の範囲で再試行します。不正なフレームや途中で終了した出力は再試行しません。

## キャンセルとリソースの所有権

画面を閉じたら fetch を中断します。サービスが待機させる上流読み取りは最大一つです。切断、タイムアウト、送信失敗時は読み取りをキャンセルし、終了を待って guarded・Provider・内部グラフのイテレーターを閉じます。一つの終了処理が失敗しても残りを試みます。共有 HTTP クライアントは各ターンではなくアプリの lifespan が管理します。

回答は逐次送信し、保存用の本文は出力上限内で保持します。完成した回答、ツール履歴、使用量の一括 commit 後に `finish` を送ります。中断時はユーザーメッセージだけ残ることがあります。

## プロキシ設定

応答には `Cache-Control: no-cache, no-transform` と `X-Accel-Buffering: no` が付きます。両チャット API と `/api/v1` エイリアスでプロキシのバッファリングを無効にします。[デプロイ](./deployment.md)を参照してください。
