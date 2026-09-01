# アーキテクチャ

サービスはアプリケーションファクトリー方式の FastAPI アプリで、プロセス全体の依存関係は lifespan フックで生成・破棄されます。

```
app/main.py            アプリファクトリー、lifespan、ミドルウェア、例外ハンドラー
app/core/config.py     フェイルファストな設定
app/core/security.py   プリンシパル解決（service / user / anonymous）
app/core/errors.py     エラーコード（ビジネスサービスと整合）
app/core/logging.py    リクエストスコープ付き JSON / テキストロギング
app/providers/         ChatProvider 抽象 + ファクトリー（mock / openai-compatible）
app/schemas/           リクエスト + SSE チャンク + エンベロープモデル
app/services/          レートリミッター（memory / redis）
app/api/v1/            ルート（chat, system）
```

## リクエストライフサイクル

1. **信頼済みホスト + CORS + リクエストコンテキストのミドルウェア**が相関 ID を割り当て、リクエストごとに
   アクセスログを 1 行出力します。
2. **認証**がプリンシパルを解決します：サービス トークン → ユーザー JWT → 匿名。
3. **ハンドラー**が入力を検証し、レート制限を適用し、プロバイダーの断片を SSE フレームとしてストリーミングします。
4. **例外ハンドラー**が `AppError` と `RequestValidationError` を共有 JSON エンベロープに写像します。

## プロバイダー抽象

モデルアクセスは `ChatProvider` の背後にあります：

- `MockChatProvider` — 固定のストリーム。開発やテストでトランスポート全体をオフライン動作させます。
- `OpenAICompatibleProvider` — `httpx` 経由の任意の OpenAI 互換エンドポイント。

ファクトリー（`app/providers/factory.py`）が起動時に `AI_PROVIDER` から選択します。プロバイダーを入れ替えても、
トランスポートやフロントエンドには何も影響しません。

## ストリーミング動作

- ストリームは `start`、0 個以上の `delta`、そして `finish` を発行します。
- ハンドラーは断片の合間に `request.is_disconnected()` を確認し、ブラウザが離脱したら即座に中止します。
  これにより誰も読まないトークンへの課金を避けられます。
- ストリーム途中の失敗は、クライアント安全なメッセージを持つ `error` イベントとして報告されます — プロバイダー内部が
  漏れることはありません。

## クロスサービスアイデンティティ

`JWT_SECRET`、`JWT_ISSUER`、`JWT_AUDIENCE` はビジネスサービスと一致させる必要があります。これにより、そこでログイン
したユーザーはここでも認証済みになります。加えて `SERVICE_TOKEN` により、信頼済みゲートウェイが自身のユーザーに代わって
呼び出せます。
