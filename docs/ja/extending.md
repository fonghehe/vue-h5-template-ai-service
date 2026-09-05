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
