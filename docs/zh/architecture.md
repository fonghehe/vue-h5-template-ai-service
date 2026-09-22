# 架构

本仓库没有前端 `src/`、页面、客户端路由、store、composable、UI 组件或 CSS 主题。外部 `@vh5/ai-chat` 消费这里的旧 SSE 端点。

```text
Vue / @vh5/ai-chat -> /api/ai/chat -> FastAPI -> LLMProvider -> SSE
Go 业务服务 -> 签发 JWT / 商品 API
用户 JWT -> /api/conversations/{id}/messages -> ContextBuilder -> 直接流式 LLM
                                                        | agent/auto
                                                        v
                                                  LangGraph -> ToolRegistry
                                                                   |
                                                     search_product -> Go
用户 JWT -> /api/knowledge/documents -> embedding -> PostgreSQL + pgvector
Redis -> 请求计数、流并发配额、会话锁
```

## 模块边界

| 路径 | 职责 |
|---|---|
| `app/main.py` | FastAPI 工厂、生命周期依赖、中间件、错误信封 |
| `app/api/v1/` | chat、conversation、knowledge、usage、探针的 HTTP/SSE 边界 |
| `app/schemas/` | Pydantic 请求、响应、SSE 类型 |
| `app/core/` | 配置、JWT、错误、日志、观测 |
| `app/providers/` | LLM/Embedding 中立接口、Mock/HTTP 适配器 |
| `app/services/` | 上下文、Prompt、模型路由、Agent、检索、配额、取消 |
| `app/tools/` | 白名单工具和参数校验 |
| `app/db/` | SQLAlchemy async 模型、会话、按所有者查询 |
| `alembic/`、`evals/`、`tests/` | 迁移、离线冒烟评估、pytest |

## 请求与数据流

`create_app()` 安装 TrustedHost、CORS、请求 ID、路由和异常处理；lifespan 创建 Provider、Embedding、DB、限流器、锁、工具及工作流。旧 `/api/ai/chat` 接受客户端 `messages[]`，不持久化。新会话路由校验 JWT 所有权、保存用户消息、构建受限上下文，再走直接流或 Agent。成功完成后保存一条助手消息和一条用量记录。断连时可能只保留用户消息，客户端需允许这种状态。

JSON 错误使用 `{code,message,data,error,requestId}`；SSE 开始后错误改用 `error` 帧。PostgreSQL 保存会话、消息、文档、向量与用量；SQLite 仅作本地/测试回退。未配 Redis 时计数、流配额、锁均为进程内；多副本应配置 Redis。Go 服务不在此仓库，商品工具固定调用配置域名下的 `/api/v1/products`，具体 Go 部署契约需单独验证。继续阅读[会话](/zh/conversations)、[Agent/RAG](/zh/agent-rag)和[扩展](/zh/extending)。

## 事务与资源所有权

HTTP -> 纯 ASGI 上下文/请求大小中间件 -> Router/Dependency -> ChatService 或 ConversationService -> Repository/Provider。`AsyncExitStack` 在每个资源创建后立即登记关闭回调，覆盖部分启动失败。Repository 只 flush，Service 控制事务。会话使用短 Session，在摘要和最终模型生成前释放连接。成功轮次将工具历史、助手消息和用量原子提交后才发 finish；取消仍可能保留用户消息。Redis 使用共享有界连接池、按令牌持有的过期流租约和会话锁。ASGI 计时覆盖完整 SSE，ContextVar 日志隔离并发请求。
