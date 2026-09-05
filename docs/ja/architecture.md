# アーキテクチャ

このリポジトリにはフロントエンドの `src/`、画面、クライアントルーター、store、composable、UI コンポーネント、CSS テーマはありません。別リポジトリの `@vh5/ai-chat` が旧 SSE エンドポイントを利用します。

```text
Vue / @vh5/ai-chat -> /api/ai/chat -> FastAPI -> LLMProvider -> SSE
Go ビジネスサービス -> JWT 発行 / 商品 API
ユーザー JWT -> /api/conversations/{id}/messages -> ContextBuilder -> 直接 LLM ストリーム
                                                             | agent/auto
                                                             v
                                                       LangGraph -> ToolRegistry
                                                                        |
                                                          search_product -> Go
ユーザー JWT -> /api/knowledge/documents -> embedding -> PostgreSQL + pgvector
Redis -> リクエスト数、同時ストリーム、会話ロック
```

## モジュール

| パス | 責務 |
|---|---|
| `app/main.py` | FastAPI ファクトリー、lifespan、ミドルウェア、エラー形式 |
| `app/api/v1/` | chat、conversation、knowledge、usage、probe の HTTP/SSE 境界 |
| `app/schemas/` | Pydantic の公開契約と SSE フレーム |
| `app/core/` | 設定、JWT、エラー、ログ、可観測性 |
| `app/providers/` | 中立的な LLM/Embedding と Mock/HTTP アダプター |
| `app/services/` | コンテキスト、プロンプト、モデル選択、Agent、検索、制限、キャンセル |
| `app/tools/` | 許可リストにあるツールと引数検証 |
| `app/db/` | SQLAlchemy async と所有者を確認するリポジトリ |
| `alembic/`、`evals/`、`tests/` | マイグレーション、オフライン簡易評価、pytest |

## 処理とデータ

`create_app()` は TrustedHost、CORS、リクエスト ID、ルート、例外処理を登録します。lifespan は Provider、Embedding、DB、リミッター、ロック、ツール、ワークフローを生成します。旧 `/api/ai/chat` はクライアントの `messages[]` を受け取り保存しません。新しい会話ルートは JWT の所有者を検証し、ユーザーメッセージを保存し、制限付きコンテキストを構築して直接ストリームまたは Agent に送ります。正常終了後にアシスタントメッセージと使用量を保存します。切断後にユーザーメッセージだけ残る場合があります。

JSON エラーは `{code,message,data,error,requestId}`、SSE 開始後のエラーは `error` フレームです。PostgreSQL は会話・文書・ベクトル・使用量を保存し、SQLite はローカル/テスト用です。Redis 未設定ならカウンター・ロックはプロセス内だけです。Go サービスはこのリポジトリに含まれず、商品ツールは設定済みベース URL の `/api/v1/products` だけを呼びます。実際の Go 側契約は別途検証が必要です。[会話](/ja/conversations)、[Agent/RAG](/ja/agent-rag)、[拡張](/ja/extending)も参照してください。
