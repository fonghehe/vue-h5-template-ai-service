# 部署

## 本地容器环境

`docker compose up --build` 启动 API（`127.0.0.1:8001`）、Redis 7 和 PostgreSQL 17/pgvector。容器先迁移再启动 Uvicorn，使用 Mock 模型并要求聊天认证；内置凭据只用于本地。Go 服务需单独启动，`host.docker.internal:8002` 依赖 Docker Desktop 或等效主机映射。

## 生产启动

1. 准备 PostgreSQL/pgvector 和 Redis，通过部署环境提供密钥。
2. 按[配置参考](./configuration.md)设置 staging/production 参数，包括 `DATABASE_AUTO_CREATE=false`。JWT secret、issuer、audience 与 Go 一致；按需接入真实 Provider。
3. 备份已有数据，在启动副本前单独执行一次迁移，避免每个副本争抢迁移。
4. 启动后检查 `/health`、`/ready`，另行验证目标 Go 商品 API 的服务令牌及 `X-User-ID` 授权规则。

```bash
uv run alembic upgrade head
uv run alembic check
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --timeout-graceful-shutdown 100
```

## 代理与关闭

入口负责 TLS。旧聊天路由和 `/api/v1` 别名都要关闭缓冲；以下示例同时覆盖两者，读取超时须大于心跳间隔。只信任入口 IP/CIDR 的转发头，例如 `--proxy-headers --forwarded-allow-ips=10.0.0.10`，并限制绕过入口的直接访问。

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

Uvicorn 关闭宽限至少比流截止时间长 10 秒，容器停止宽限再长 10 秒。默认分别为 90 / 100 / 110 秒，修改时一起调整。Compose 使用 `exec uvicorn`，确保服务收到 SIGTERM。

## 探针与可观测性

| 端点 | 含义 |
|---|---|
| `/health` | 仅表示进程存活，不证明依赖可用。 |
| `/ready` | 并发执行有超时的数据库和限流器探测，故障返回 503；不调用模型或 Go。 |
| `/metrics` | 开启时提供 Prometheus 指标，应由代理或网络限制访问。 |

HTTP 指标使用路由模板和标准方法名，其他方法统一为 `OTHER`。日志带请求 ID，Provider/工具请求转发 `X-Request-ID`。异常日志保留类型和堆栈位置，省略异常值及异常链消息；日志正文和额外字段仍须避免秘密。

`OTEL_ENABLED` 配置追踪，但没有 exporter。需在目标观测系统中接入 exporter 和采样策略，开启变量本身不会导出追踪。

## 运行边界

- 每日用量是成功持久化轮次的估算，不是计费账本；并发请求可能超过准入阈值。
- PDF 解析使用有并发上限的线程，不是进程隔离。大规模不可信上传需要独立限资源解析进程或 Worker。
- 默认连接池和限额是配置起点，不代表已验证的生产容量。真实模型、Go、代理断连、备份和滚动关闭需要在目标环境验证。

隔离集成测试、迁移检查和本地基准见[贡献指南](./contributing.md)。
