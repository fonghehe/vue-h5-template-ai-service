# 会話とコンテキスト

`POST /api/ai/chat` は `@vh5/ai-chat` 向けのステートレスな API として残ります。サーバーで履歴を管理する場合は `/api/conversations` を使います。保存系の API はすべて Go サービスの**ユーザー JWT**が必要です。匿名またはサービス資格情報では会話を所有できません。Repository が所有者を確認します。

## 1 ターンを送る

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"商品相談"}'
# 返された data.id を AI_CONVERSATION_ID に設定:
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"こんにちは","mode":"chat","useRag":false}'
```

`mode` は `auto`（デフォルト）、`chat`、`agent`。`auto` は `app/services/conversations.py` の商品・計算・時刻キーワードだけを見ます。汎用の意図分類器ではありません。`GET /api/conversations/{id}` は順序付きメッセージ、要約、出典を返し、一覧は概要のみを返します。DELETE は所有会話とメッセージを削除します。

## コンテキスト制限と保存

`app/services/context.py` の `ContextBuilder` はバージョン付きシステムプロンプト、保存済み要約、任意の検索/ツール結果、最近のメッセージを組み立てます。約 3 文字/トークンとメッセージの追加コストで見積もり、**実際の Provider tokenizer ではありません**。`AI_CONTEXT_TOKEN_BUDGET` を超える古い履歴は `LLMProvider.complete()` で要約して `conversation.summary` に保存します。検索文やプロンプトが切り詰められることがあります。100 件の履歴のテストがあります。

正常終了時の回答・tool 履歴・使用量は一括 commit します。直接/最終ストリーム tokens は見積もりで、計画には利用可能な Provider 使用量を使います。日次制限は完了済み記録の閾値で、並行実行では超過する場合があります。旧 chat と中断した turn は含みません。正確な請求や前払い予約ではありません。

一覧は `page`（1–100000）と `page_size`（1–100、既定 50）を受け取り、既存の配列エンベロープを保ちます。会話詳細は既定で最新 100 件を返し、`page_size` と `before=<sequence>` で以前のページを取得します。メッセージに `sequence` が追加されます。コンテキストは最新 200 件まで、要約入力にも上限があります。最新 user message を維持し、大きすぎる入力は拒否します。保存メッセージは 20000 文字と context budget の制限を受けます。旧 `/api/*` と `/api/v1/*` の両方が利用できます。
