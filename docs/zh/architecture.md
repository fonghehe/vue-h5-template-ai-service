# 架构

Vue 客户端从本 FastAPI 服务读取 SSE。兄弟 Go 服务负责签发 access JWT 和提供商品 API；本服务校验令牌、保存 AI 会话与文档，并按需调用注册工具。

```text
Vue -> FastAPI routes -> Services -> LLM / Embedding providers
                            |----> Repositories -> PostgreSQL / pgvector
                            |----> Agent -> ToolRegistry -> Go product API
                            `----> Redis: counters / stream leases / locks
Go -> access JWT -> FastAPI authentication
```

## 模块职责

| 路径 | 职责 |
|---|---|
| `app/main.py` | 应用工厂与 lifespan 资源管理 |
| `app/api/` | HTTP/SSE 传输与依赖 |
| `app/schemas/` | 公开请求、响应和事件契约 |
| `app/services/` | 会话、上下文、Agent、检索与配额编排 |
| `app/providers/` | 供应商无关的 LLM/Embedding 接口及适配器 |
| `app/tools/` | 注册工具和参数校验 |
| `app/db/` | 异步 Session、模型和按所有者隔离的 Repository |
| `app/core/` | 配置、JWT 校验、错误及可观测性 |
| `alembic/`、`tests/`、`evals/` | 迁移、行为测试和离线冒烟评估 |

## 事务与资源归属

Repository 只 flush，Service 决定提交或回滚。会话请求先用短事务保存用户消息，构建上下文和生成回答时不持有该事务，最后将完整回答与用量一起提交。参见[会话](./conversations.md)。

lifespan 在资源创建后立即登记清理，覆盖部分启动失败。HTTP 和 Redis 客户端共享；Session 与响应流按请求或轮次管理。SSE 包装层负责显式关闭内层迭代器。参见 [SSE](./sse.md)。

## 存储与多副本协调

PostgreSQL/pgvector 保存会话、文档、向量和用量；SQLite 用于本地和测试。Redis 在副本间共享请求计数、并发流租约和会话锁；不配置时仅在进程内协调。staging/production 必须使用 Redis 和 PostgreSQL。

商品工具只调用配置的 Go 地址下的 `/api/v1/products`。目标部署如何校验令牌和 `X-User-ID`，需要单独联调。参见 [Agent 与 RAG](./agent-rag.md)及[扩展指南](./extending.md)。
