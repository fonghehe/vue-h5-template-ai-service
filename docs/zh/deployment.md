# 部署指南

## 构建镜像

```bash
docker build -t vue-h5-template-ai-service:latest .
# 或
make docker
```

镜像以**非 root** 用户运行，并包含容器健康检查。

## 用 docker compose 运行

```bash
cp .env.example .env
docker compose up --build
```

这会启动服务加上 Redis 7 实例（用于多实例限流）。API 监听 `http://localhost:8001`。

## 流式相关的注意事项

SSE 对代理缓冲很敏感。用 nginx 或等价代理反向代理时：

```nginx
location /api/ai/chat {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
}
```

服务本身已发送 `X-Accel-Buffering: no` 与 `Cache-Control: no-cache, no-transform`，以阻止中间层缓冲或
重新压缩流。

## 生产环境检查清单

- **设置 `SERVICE_TOKEN`**，并与网关一起轮换。
- **替换 `JWT_SECRET`** —— 并保持与业务服务一致。
- 对外公开前**设置 `AI_AUTH_REQUIRED=true`**。
- **使用 `AI_PROVIDER=openai-compatible`** 并配置真实的 `AI_API_KEY`。
- 多副本运行时**设置 `REDIS_URL`** —— 否则每个副本各自维护配额。
- **在上游终结 TLS**，并把 `CORS_ORIGINS` 设为真实域名。
- 生产环境**设置 `DOCS_ENABLED=false`**。

## CI

GitHub Actions 在每个 PR 与 `main` 的 push 上运行：`ruff check`、`ruff format --check`、`mypy app`、带覆盖率的
`pytest`，以及 Docker 镜像构建。
