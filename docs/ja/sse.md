# SSE プロトコル

両方のチャット API は `text/event-stream` を返し、各フレームは `data:` 行にコンパクト JSON を載せます。名前付き `event:` は使いません。旧 `POST /api/ai/chat` は `@vh5/ai-chat` の 4 種類を維持します。

| 型 | フィールド | 経路 |
|---|---|---|
| `start` | `id` | 両方 |
| `delta` | `delta` テキスト | 両方 |
| `finish` | `reason` | 両方 |
| `error` | `message`, optional `code`, `requestId` | 両方 |
| `thinking_status` | ユーザーに表示可能な `status` | 保存経路 |
| `tool_start`、`tool_result` | `tool`、`callId`、任意の `result` | Agent |
| `sources` | 出典配列 | RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"こんにちは"}

data: {"type":"finish","reason":"stop"}

```

正常時は `finish: stop` です。schema は `abort` と `error` の reason を許しますが、現行ルートは失敗時に `error` イベントを送ります。切断したクライアントは通常、終端フレームを受け取りません。追加イベントは保存経路にのみあり、旧 API には出ません。

JSON POST と Authorization には fetch を使い、画面を閉じたら中断します。`guarded_stream` は切断を確認し、待機中の読み取りをキャンセルして終了を待ち、直接ストリーム・Agent・Provider の反復子を閉じます。無通信時は既定で 15 秒ごとに `: heartbeat` コメントを送り、JSON イベントは増やしません。全体の期限は 90 秒で、コンテキスト・ツール・保存・背圧を含み、送信の終了には追加 5 秒を許可します。Agent は限定されたツール計画の後に最終回答を逐次配信します。保存用本文は出力上限内で保持し、各断片を先に送信します。

配信前の入力/認証/制限エラーは HTTP ステータスと JSON エンベロープ、開始後は SSE の `error` になります。`Cache-Control: no-cache, no-transform` と `X-Accel-Buffering: no` が付くので、プロキシでは両チャット経路のバッファリングを無効にしてください。[デプロイ](/ja/deployment)を参照してください。

## 後処理で例外が発生した場合

ステートレスなチャットでは、Provider ストリームの作成もエラー処理の対象に含めます。アダプターが同期的に失敗した場合は、`start` の後に内部情報を除いた SSE `error` と Request ID を返します。上流の待機中にキャンセルされた場合はキャンセルを伝播し、件数を記録します。Provider の終了処理が失敗しても、実行中ストリーム数と所要時間のメトリクスは確定します。

レスポンスの後処理は、本体のイテレーター、元のデータソース、現在の Token に属する割り当て枠の順に実行します。先の処理が例外を送出しても残りを試み、例外自体も隠しません。通信形式は変わらず、切断されたレスポンスを成功扱いにはしません。
