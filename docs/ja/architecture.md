# アーキテクチャ

Vue クライアントはこの FastAPI サービスから SSE を読み取ります。別の Go サービスが access JWT の発行と商品 API を担当します。本サービスはトークンを検証し、AI 会話と文書を保存し、必要に応じて登録済みツールを呼び出します。

```text
Vue -> FastAPI routes -> Services -> LLM / Embedding providers
                            |----> Repositories -> PostgreSQL / pgvector
                            |----> Agent -> ToolRegistry -> Go product API
                            `----> Redis: counters / stream leases / locks
Go -> access JWT -> FastAPI authentication
```

## モジュールの責務

| パス | 責務 |
|---|---|
| `app/main.py` | アプリの生成と lifespan のリソース管理 |
| `app/api/` | HTTP/SSE 通信と依存関係 |
| `app/schemas/` | 公開リクエスト・応答・イベントの契約 |
| `app/services/` | 会話、コンテキスト、Agent、検索、制限の処理 |
| `app/providers/` | ベンダーに依存しない LLM/Embedding インターフェースとアダプター |
| `app/tools/` | 登録済みツールと引数検証 |
| `app/db/` | 非同期 Session、モデル、所有者を確認する Repository |
| `app/core/` | 設定、JWT 検証、エラー、可観測性 |
| `alembic/`、`tests/`、`evals/` | マイグレーション、動作テスト、オフライン簡易評価 |

## トランザクションとリソース

Repository は flush のみを行い、Service が commit と rollback を決めます。会話は短いトランザクションでユーザーメッセージを保存し、そのトランザクションを保持せずにコンテキスト構築と生成を進め、最後に完成した回答と使用量を一括保存します。[会話](./conversations.md)を参照してください。

lifespan は生成直後にリソースの終了処理を登録し、起動途中の失敗にも対応します。HTTP/Redis クライアントは共有し、Session と応答ストリームはリクエスト・ターン単位で管理します。SSE ラッパーは内部イテレーターを明示的に閉じます。[SSE](./sse.md)も参照してください。

## 保存と複数レプリカの調整

PostgreSQL/pgvector は会話、文書、ベクトル、使用量を保存し、SQLite はローカル・テスト用です。Redis はリクエスト数、同時ストリームのリース、会話ロックをレプリカ間で共有します。未設定ならプロセス内のみの調整です。staging/production は Redis と PostgreSQL が必須です。

商品ツールは設定済み Go URL の `/api/v1/products` だけを呼びます。接続先のトークンと `X-User-ID` の検証方針は別途確認してください。[Agent と RAG](./agent-rag.md)、[拡張ガイド](./extending.md)も参照できます。
