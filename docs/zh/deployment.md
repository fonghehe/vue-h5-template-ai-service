# 部署

## 容器与迁移

```bash
docker build -t vue-h5-template-ai-service:local .
docker compose up --build
```

镜像用非 root 用户监听 8001。Compose 启动 Redis 7、PostgreSQL 17 + pgvector、AI API；先运行 `alembic upgrade head`，开启认证并使用 Mock Provider。内置数据库密码和 JWT Secret **仅用于本地**。Go 服务不在 Compose 中；`host.docker.internal:8002` 假设外部进程可达，非 Docker Desktop 环境可能需要额外 host 映射。

生产应准备 PostgreSQL/pgvector 和 Redis，配置 `DATABASE_URL=postgresql+asyncpg://...`、`DATABASE_AUTO_CREATE=false`，部署前执行 `uv run alembic upgrade head`；Embedding 维度要与迁移和模型一致。更换示例密钥，设置真实域名的 Trusted Hosts/CORS，启用 `AI_AUTH_REQUIRED=true`，与 Go 服务共享 JWT issuer 配置。还需验证 Go 商品接口确实信任 service token 和 `X-User-ID`；当前仓库不能证明外部服务已对接。

## 代理与运维

`/health` 只表示进程存活，连接后端只返回名称。`/ready` 并发检查 Redis/限流器和数据库，使用有界超时，故障返回 503；不调用模型或 Go 服务。Redis 协调故障返回安全的 503 信封并拒绝继续。`/metrics` 应由代理/网络限制访问；`OTEL_ENABLED` 提供追踪挂钩，尚无 exporter。

设置 Redis 可跨副本共享请求计数、并发流配额和会话锁；启动后的 Redis 故障并非所有操作都能透明恢复。用量 API 只统计成功持久化的会话轮次，不是账单。

CI 的 `.github/workflows/ci.yml` 检查 ruff、mypy、pytest 并构建 Docker；`deploy-docs.yml` 使用 docs 下的 npm 构建并部署 GitHub Pages。文档生产 base 为 `/vue-h5-template-ai-service/`，本地为 `/`。参见[配置](/zh/configuration)。


## 运维流程

数据库变更使用 Alembic。初始迁移支持 PostgreSQL/pgvector 和 SQLite，新增 `20261002_0002` 对齐 ORM 索引。接流量前单独执行升级，生产副本不应同时竞争运行迁移。CI 用 `alembic check` 检查漂移。生产升级前备份；`downgrade base` 仅用于可丢弃的测试库。

默认整流截止时间为 90 秒，Uvicorn 关闭宽限期至少为截止时间 + 10 秒，容器再额外留 10 秒。Compose 使用 `exec uvicorn`，确保 SIGTERM 到达服务进程；修改截止时间时同步调整两处宽限期。

只信任入口代理 IP/CIDR 的转发头，例如 `--proxy-headers --forwarded-allow-ips=10.0.0.10`，不要盲目信任客户端 X-Forwarded-For；网络层限制服务只能由入口访问。旧与版本化聊天路由均适用：

```nginx
location /api/ {
    proxy_pass http://ai:8001;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 120s;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

代理读取超时需大于心跳间隔，入口终止 TLS，只允许配置的 Origin/Host，限制 `/metrics` 访问。HTTP 指标覆盖次数、状态、完整响应耗时和活动请求，使用路由模板防止会话 ID 导致高基数。日志包含服务、环境、请求 ID；外部 Provider/工具请求传递 X-Request-ID，不记录凭据。用量仅表示已完成轮次的估算，尚非计费账本。

CI 使用真实 pgvector/Redis 验证事务、查询、锁和迁移往返。`make integration` 只连接可丢弃的 `vh5_ai_test` 数据库和 Redis DB 15；模型使用 Mock，无需真实密钥。依赖审计：

```bash
uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/ai-requirements.txt
uvx --from pip-audit==2.10.1 pip-audit --no-deps --disable-pip -r /tmp/ai-requirements.txt
```
