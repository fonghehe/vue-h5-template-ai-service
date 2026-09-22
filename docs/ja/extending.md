# 拡張ガイド

ここは Python サービスで、Vue の画面、メニュー、フロントエンド権限、store、composable、UI コンポーネントはありません。これらはフロントエンドのリポジトリで変更します。

## API を追加する

公開 Pydantic 契約を `app/schemas/` に置き、`app/api/v1/` に小さなルートを作り、`app/api/v1/router.py` に登録します。DB 規則は `app/db/repositories.py`、処理の組み立ては `app/services/` に置きます。ユーザー所有データには `AuthenticatedUser` と `get_db_session` を使います。JSON は `ApiResponse(data=..., requestId=request.state.request_id)`、SSE は `encode_sse` で返します。本番 schema を変えたら Alembic revision を追加します。

実際の usage ルートからの抜粋です（imports は省略）：

```python
@router.get("/me", response_model=ApiResponse[UsageView])
async def my_usage(request: Request, user: AuthenticatedUser, session: DbSession) -> ApiResponse[UsageView]:
    summary = await UsageRepository(session).summary(user.subject)
    return ApiResponse(data=UsageView.model_validate(summary), requestId=request.state.request_id)
```

## Provider・モデル・ツール

`app/providers/base.py` の `LLMProvider` は `stream`、`complete`、`structured_output`、`tool_calling` を定義します。実装を `app/providers/factory.py` に登録し、`AI_PROVIDER` の設定検証を拡張します。SDK 型を service に漏らさないでください。Embedding は別インターフェースです。タスクごとのモデルは `app/services/model_router.py`、バージョン付き Prompt は `app/services/prompts.py` にあります。

新しいツールは `app/tools/base.py` の `Tool` を継承し、名前、説明、Pydantic `input_model`、`execute()` を実装し、`app/main.py` で登録します。`Tool.run()` が引数を検証します。外部 URL は運用側が固定し、タイムアウトを設け、モデルが指定した任意の URL を受け付けないでください。`ProductSearchTool` が現行例です。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m evals.run
cd docs && npm run docs:typecheck && npm run docs:build
```

CI は Mock/模擬 HTTP を利用し、実 API Key を不要にします。`ChatRequest`、SSE、Provider 契約を変える場合はテストと 3 言語の [SSE 文書](/ja/sse) を更新し、`POST /api/ai/chat` との互換性を保ちます。

Repository は flush のみ。Service で `async with database.sessions.begin()` を使い、複数 Repository の書き込みを一括管理します。lifespan に即座に終了処理を登録します。SSE は `QuotaStreamingResponse` で lease・期限・heartbeat・cleanup を管理します。Service は FastAPI Request/Response を受け取りません。domain router の prefix に `/api` を含めず、集約側で旧 prefix と `/api/v1` を登録します。

`stream` は `AsyncGenerator[str, None]` を返します。`aclose()` と上流 HTTP ストリームへのキャンセル伝播を実装し、逐次出力してください。共有クライアントの終了処理は lifespan に登録します。

## 追加機能の回帰テスト

`tests/test_suggestions.py` は二つのパス、三言語、既定値、不正入力、Request ID、返却リストの独立性を検証します。実モデルのキーは不要です。PostgreSQL/Redis の統合確認は `tests/test_infrastructure.py` で別途設定し、ローカルの単体テストではスキップされる場合があります。

```bash
uv run pytest tests/test_suggestions.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

文言は `app/services/suggestions.py`、HTTP 検証と包装は `app/api/v1/suggestions.py` にあります。言語追加時は Literal、フロントエンドの OpenAPI enum、テストをそろえ、各言語の文言を個別に調整してください。共有 tuple を変更できないよう、新しい list を返します。ユーザー履歴からの個別推薦は行いません。

[API](./api.md)
