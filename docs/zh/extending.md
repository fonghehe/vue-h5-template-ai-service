# 扩展指南

## 新增接口

公共 Pydantic 契约放 `app/schemas/`；在 `app/api/v1/` 新增单一职责路由，并在 `app/api/v1/router.py` 注册；数据库约束放 `app/db/repositories.py`，业务编排放 `app/services/`。用户数据使用 `AuthenticatedUser` 和 `get_db_session`。JSON 响应使用 `ApiResponse(data=..., requestId=request.state.request_id)`，流式响应使用 `encode_sse`。生产 schema 变更需新增 Alembic revision。

以下摘自真实用量路由，省略 imports：

```python
@router.get("/me", response_model=ApiResponse[UsageView])
async def my_usage(request: Request, user: AuthenticatedUser, session: DbSession) -> ApiResponse[UsageView]:
    summary = await UsageRepository(session).summary(user.subject)
    return ApiResponse(data=UsageView.model_validate(summary), requestId=request.state.request_id)
```

## Provider、模型和工具

`app/providers/base.py` 的 `LLMProvider` 定义 `stream`、`complete`、`structured_output`、`tool_calling`。实现后在 `app/providers/factory.py` 注册，并扩展 `AI_PROVIDER` 配置校验；不要向 service 泄漏供应商 SDK 类型。Embedding 有独立接口。任务选模在 `app/services/model_router.py`，版本化 Prompt 在 `app/services/prompts.py`。

新工具继承 `app/tools/base.py` 的 `Tool`，提供名称、说明、Pydantic `input_model` 和 `execute()`，再于 `app/main.py` 注册。`Tool.run()` 负责参数校验。外部访问目标应由运营方固定配置并有超时，不能接受模型给出的任意 URL；现有 `ProductSearchTool` 可作参考。

CI 使用 Mock/模拟 HTTP，不调用真实 API。改 `ChatRequest`、SSE 或 Provider 契约时，更新测试与三语 [SSE 文档](/zh/sse)，保留 `POST /api/ai/chat` 兼容性。

Repository 只 flush；Service 用 `async with database.sessions.begin()` 管理写入和跨 Repository 事务。资源创建后立即登记 lifespan 关闭回调。SSE 使用 `QuotaStreamingResponse` 管理租约、截止时间、心跳与清理。Service 不接收 FastAPI Request/Response。域路由自身 prefix 不带 `/api`，聚合层注册旧路径和 `/api/v1`。

`stream` 返回 `AsyncGenerator[str, None]`：实现必须支持 `aclose()`，将取消传递到上游 HTTP 流并增量输出；复用的客户端须在 lifespan 注册关闭。

## 聊天建议语言

固定文案位于 `app/services/suggestions.py`，HTTP 校验位于 `app/api/v1/suggestions.py`。新增语言时同步 Literal 契约、测试和消费方前端的 OpenAPI 枚举。

运行相关行为测试及[贡献指南](./contributing.md)中的检查。
