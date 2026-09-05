# 会話とコンテキスト

`POST /api/ai/chat` は `@vh5/ai-chat` 向けのステートレスな API として残ります。サーバーで履歴を管理する場合は `/api/conversations` を使います。保存系の API はすべて Go サービスの**ユーザー JWT**が必要です。匿名またはサービス資格情報では会話を所有できません。Repository が所有者を確認します。

## 1 ターンを送る

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"商品相談"}'
# 返された data.id を AI_CONVERSATION_ID に設定:
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"こんにちは","mode":"chat","useRag":false}'
```

`mode` は `auto`（デフォルト）、`chat`、`agent`。`auto` は `app/api/v1/conversations.py` の商品・計算・時刻キーワードだけを見ます。汎用の意図分類器ではありません。`GET /api/conversations/{id}` は順序付きメッセージ、要約、出典を返し、一覧は概要のみを返します。DELETE は所有会話とメッセージを削除します。

## コンテキスト制限と保存

`app/services/context.py` の `ContextBuilder` はバージョン付きシステムプロンプト、保存済み要約、任意の検索/ツール結果、最近のメッセージを組み立てます。約 3 文字/トークンとメッセージの追加コストで見積もり、**実際の Provider tokenizer ではありません**。`AI_CONTEXT_TOKEN_BUDGET` を超える古い履歴は `LLMProvider.complete()` で要約して `conversation.summary` に保存します。検索文やプロンプトが切り詰められることがあります。100 件の履歴のテストがあります。

同じ会話 ID のターンはロックで直列化し、異なる ID は並行できます。Redis があればレプリカ間で共有、なければプロセス内だけです。正常終了したターンはアシスタントメッセージと `UsageRecord` を保存します。切断時はユーザーメッセージだけ残る場合があります。`GET /api/usage/me` は成功した保存済みターンをモデル・会話・日付で集計します。旧チャットは含みません。直接ストリームのトークン数は推定値で、Agent は利用可能な Provider の使用量を使います。請求システムではありません。
