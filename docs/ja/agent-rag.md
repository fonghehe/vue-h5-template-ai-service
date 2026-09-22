# エージェント・ツール・RAG

## ワークフローの条件

`mode="chat"` は直接ストリーム、`mode="agent"` は制限付き LangGraph ツール計画です。auto の商品・計算・時刻キーワード判定は `app/services/conversations.py` にあります。登録ツールの選択と実行の後、Provider が最終回答を逐次生成します。計画は最大 256 出力 tokens で表示しません。完成した回答の分割ではありません。反復回数、全体の期限、出力上限で作業を制限します。

## ツールの境界

`app/tools/base.py` の `ToolRegistry` は登録名のみを公開し、Pydantic で引数を検証します。`get_current_time` は UTC を返し、`calculator` は制限付き AST 算術のみです。`search_product` は `BUSINESS_SERVICE_URL/api/v1/products` に固定 GET を送り、`q`、任意の `maxPrice`、`limit`、`X-User-ID`、設定されている場合のみ Bearer Token を使います。モデルが URL を指定することはできません。Go サービスは Compose 外なので、実際の API と信頼設定を別途確認してください。検索/ツールのテキストは信用しないよう Prompt で指示していますが、プロンプトインジェクションを完全に防ぐ保証ではありません。

## ナレッジ検索

`POST /api/knowledge/documents` は multipart `file` と任意の JSON 文字列 `metadata` を受け付けます。`KnowledgeService` は UTF-8 の txt/md またはテキスト抽出可能な PDF を解析し、文字単位の重複チャンクに分け、Embedding して保存します。スキャン PDF の OCR はありません。デフォルトの上限は 5 MB。PostgreSQL/pgvector は所有者限定のコサイン top-K、SQLite はプロセス内のランキングを使います。Mock Embedding はテスト用の決定的ハッシュで、実用の意味検索ではありません。

`useRag=true` のターンは質問を Embedding して所有文書のチャンクを検索し、コンテキストに加え、`documentId`、`chunkId`、`title` を持つ `sources` を送ります。出典は検索素材を示すだけで、回答の全主張を保証しません。`assistant.rag` v1 Prompt は根拠に基づく回答を求めます。

## 構造化出力と評価

`LLMProvider.structured_output()` は Pydantic で検証し、HTTP アダプターは無効な JSON を一度修復再試行します。`app/schemas/knowledge.py` の `ProductRecommendation` はサンプル schema で、現在の公開 API は返しません。`evals/run.py` は計算器 1 件とその他の Mock 応答が空でないことを確認する簡易オフラインテストで、**定量的 RAG ベンチマークではありません**。pytest に検索・ツール・schema の対象テストがあります。緑の結果だけで実モデル品質は判断できません。

metadata は JSON object が必須です。解析は制限付き worker thread、PDF signature 確認、basename 化、抽出文字数/chunk 数制限、64 chunk 単位の embedding を使います。文書と chunk は一括 commit し、SQLite の外部キー cascade も有効です。厳格な PDF 隔離には、別の resource-limited parser worker が必要です。
