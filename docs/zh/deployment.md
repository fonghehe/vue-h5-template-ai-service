# 部署

## 容器与迁移

```bash
docker build -t vue-h5-template-ai-service:local .
docker compose up --build
```

镜像用非 root 用户监听 8001。Compose 启动 Redis 7、PostgreSQL 17 + pgvector、AI API；先运行 `alembic upgrade head`，开启认证并使用 Mock Provider。内置数据库密码和 JWT Secret **仅用于本地**。Go 服务不在 Compose 中；`host.docker.internal:8002` 假设外部进程可达，非 Docker Desktop 环境可能需要额外 host 映射。

生产应准备 PostgreSQL/pgvector 和 Redis，配置 `DATABASE_URL=postgresql+asyncpg://...`、`DATABASE_AUTO_CREATE=false`，部署前执行 `uv run alembic upgrade head`；Embedding 维度要与迁移和模型一致。更换示例密钥，设置真实域名的 Trusted Hosts/CORS，启用 `AI_AUTH_REQUIRED=true`，与 Go 服务共享 JWT issuer 配置。还需验证 Go 商品接口确实信任 service token 和 `X-User-ID`；当前仓库不能证明外部服务已对接。

## 代理与运维

两个聊天端点（`/api/ai/chat`、`/api/conversations/{id}/messages`）均需关闭代理缓冲、设置合理读取超时并终止 TLS。服务已发送 `X-Accel-Buffering: no` 与 `Cache-Control: no-cache, no-transform`。`/health` 只表示进程存活；`/ready` 只 ping 限流器，异常时 503，**不**检查 DB、模型或 Go 服务。`/metrics` 默认启用且无内置认证，应在代理/网络层限制或关闭。`OTEL_ENABLED=true` 只安装 tracer provider，没有 exporter。

设置 Redis 可跨副本共享请求计数、并发流配额和会话锁；启动后的 Redis 故障并非所有操作都能透明恢复。用量 API 只统计成功持久化的会话轮次，不是账单。

CI 的 `.github/workflows/ci.yml` 检查 ruff、mypy、pytest 并构建 Docker；`deploy-docs.yml` 使用 docs 下的 npm 构建并部署 GitHub Pages。文档生产 base 为 `/vue-h5-template-ai-service/`，本地为 `/`。参见[配置](/zh/configuration)。
