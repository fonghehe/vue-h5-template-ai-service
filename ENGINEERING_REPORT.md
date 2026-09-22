# FastAPI 服务工程化验收报告

日期：2026-10-02。基线：`cdf6dd3`。本次工作在原仓库渐进实施；未执行 Git commit 或 push，也未向生产环境部署。

## 结论与范围

已完成审计、分阶段改造与本地验收。服务可以安装、迁移、测试、打包、以非 root Docker 容器启动，并具备真实增量 SSE、断连清理、明确事务、分布式限流、基础日志和指标。旧接口保持兼容，新接口提供 `/api/v1` 别名。

这是经过本地与隔离基础设施验证的工程实现；真实模型、外部 Go 服务、生产入口代理和生产负载仍需在目标环境验收。不能用 Mock 输出或覆盖率证明真实模型质量，也不能将估算用量用于精确商业计费。

## 第一阶段：现状与问题

修改前扫描了所有 Python 源码，包括 app、tests、evals、alembic，以及依赖、锁文件、Docker/Compose、CI、Makefile、环境示例、README 和 VitePress 文档。基线工作区干净，79 个测试、Ruff 与严格 mypy 均通过。P0–P3 问题和实施计划保存在 [ARCHITECTURE_REVIEW.md](./ARCHITECTURE_REVIEW.md)。

### 技术栈与已有能力

| 项目 | 实际情况 |
|---|---|
| Python | 支持 3.12–3.14；测试环境 3.14.4，Docker 3.13.16 |
| 依赖管理 | uv + pyproject.toml + uv.lock，保留原方案 |
| Web/契约 | FastAPI 0.141.1、Starlette 1.6.0、Pydantic 2.13.5、pydantic-settings |
| 数据访问 | SQLAlchemy 2.0.54、AsyncEngine/AsyncSession、asyncpg/aiosqlite、Alembic |
| 外部资源 | httpx 0.28.1、Redis 6.4.0、pgvector、LangGraph |
| 业务 | 流式聊天、用户会话/消息、工具、Agent、知识文档/RAG、用量统计 |
| 认证 | 验证 Go 签发的 HS256 JWT，检查签名、exp、iat、sub、issuer、audience；持久化资源按 subject 隔离 |
| 原有优势 | Schema 与 ORM 分离、异步数据库、Provider 接口、受限上下文、注册工具、版本化 Prompt、基础日志/指标、非 root 运行 |

未发现需要新建用户/订单/资产模块的业务依据。用户密码、登录、刷新令牌、普通 CRUD 与令牌签发继续由兄弟 Go 服务负责。没有 WebSocket、MQ 或持久后台任务业务，因此没有为目录完整性加入这些系统。

### 优先级与处置

| 优先级 | 主要问题 | 结果 |
|---|---|---|
| P0 | 流取消后 pending anext 遗留、成功答复和用量分开提交、production 可匿名、health 暴露 Redis URL | 已修复，并覆盖取消/回滚/安全配置回归 |
| P1 | Agent 先完成再切片、每请求重建 HTTP 客户端、Redis 配额释放竞争、启动部分失败泄漏、ready 不检查 DB | 已修复，并做真实 Redis/PostgreSQL 验证 |
| P2 | 会话 Router 耦合业务、无限列表/历史、PDF 阻塞、全局日志猴子补丁、ORM/迁移索引漂移、镜像构建上下文污染 | 已完成服务抽取、有界访问、线程解析、ASGI 日志、补充迁移与多阶段镜像 |
| P1（依赖审计新增） | PyJWT 2.13.0 被 pip-audit 报告 13 条已知安全记录 | 升级到 2.15.0；其余锁定版本不变，加入异常签名和深层 Header 回归 |
| P3 | 精确计费、分布式每日预留、持久文档 Worker、向量索引、追踪出口、目标环境容量规划 | 明确保留为有业务依据的后续工作 |

## 第二、三阶段：架构与实现

### 目录与职责

继续使用现有 `app/api`、`core`、`schemas`、`db`、`providers`、`services`、`tools` 分层，适合当前少量 AI 业务。调用链为：

```text
HTTP -> ASGI Middleware -> Router/Depends -> Service
                                           -> Repository -> Async DB
                                           -> Provider/Tool -> HTTP
                                           -> Shared Redis coordination
```

新增主要文件：`app/services/chat.py`、`app/services/conversations.py`、`app/api/streaming.py`、`app/core/middleware.py`、索引修正迁移、3 个专项测试模块和两份报告。原会话 Router 从 341 行减为约 110 行，处理参数、依赖、响应；Service 控制业务、准入与事务，且不依赖 FastAPI Request/Response。简单知识库列表/删除保留直接 Repository 访问，避免无价值的包装类。

没有大范围移动/删除源码，没有增加 DDD、CQRS、微服务框架或依赖注入容器。唯一运行依赖升级是 PyJWT 安全修复；pip-audit 作为锁定版本的临时 CI 工具使用，不进入运行镜像。

### Async、流式与资源生命周期

- Provider、Embedding 和商品工具复用 HTTP 连接池，明确 connect/read/write/pool 超时；lifespan 使用 AsyncExitStack，分配资源后立即登记关闭，覆盖部分启动失败与关闭异常。
- Redis 限流器、会话锁和流配额复用一个有连接数上限的客户端；DB 连接池参数可配置，关闭时 dispose。
- 流最多只有一个 pending read，消费者发送完成才继续读取，保持背压。等待中检查断连、总截止时间并发送 SSE heartbeat 注释。
- 父任务取消、客户端断开、响应起始发送失败或消费者关闭时，取消并等待 pending read，再关闭生成器/上游 HTTP 流，释放配额。
- 并发配额采用 Redis TIME + Lua + 唯一 token 的过期租约；幂等释放只能移除自己的租约。会话锁租期大于流截止时间，本地取消等待者不会遗留锁字典。
- Agent 仅在有界规划阶段使用 LangGraph；最终回答通过 Provider.stream 即时输出，测试证明最终生成尚未完成时客户端已收到 delta。
- PDF 解析移到有并发上限的线程池，限定文件字节数、页数、提取字符数和块数；Embedding 按批处理。线程不是强资源隔离，见后续边界。

持久化会话在增量发送的同时保留受输出字符上限约束的文本用于写库；不会等待完整答案后才开始 SSE。摘要与工具规划是独立的有界非流式调用。

### Database 与事务

- Repository 写方法仅 flush，不自行 commit。Service 使用 `sessions.begin()` 明确提交/回滚。
- 用户消息先短事务保存，随后释放连接再生成模型答案；成功轮次的工具历史、助手消息、UsageRecord 在一个事务中提交。`finish` 在提交成功后才发送。
- 完成事务失败会整体回滚，测试验证没有助手消息残留。中断时可以保留已经提交的用户消息，但不保存不完整助手回答。
- 列表支持有界 page/page_size 与稳定排序；会话消息支持 `before=sequence` 游标，返回最新一页；模型上下文只加载有界最近历史。
- PostgreSQL 生产必须显式 Alembic；禁止 auto-create。新增 `20261002_0002_model_indexes.py` 补齐 4 个 ORM 索引，不修改用户记录。
- 初始迁移只在 PostgreSQL 创建 vector 扩展，SQLite 使用 JSON 向量变体。真实 PostgreSQL/pgvector 与 SQLite 均验证 upgrade、check、downgrade、再次 upgrade；metadata 无漂移。
- SQLite 开启外键，删除由数据库级联处理，避免加载全部历史；SQLAlchemy 隐藏异常中的绑定参数。

不要把验收中的 `downgrade base` 用于有业务数据的生产环境。生产执行增量 upgrade，并按现有备份与发布流程回滚应用。

### API 兼容性

- 保留 `/api/ai/chat`、`/api/conversations`、`/api/knowledge/documents`、`/api/usage/me`；同时提供 `/api/v1/*`。
- 保留 camelCase envelope、HTTP 状态语义、基本 SSE `start/delta/finish/error`；Agent 工具与 RAG 事件沿用已有扩展。
- Heartbeat 是 SSE 注释，不新增业务事件；error 增加可选 code/requestId。客户端应在 error 或断连后结束当前轮次，不能自动重试已经部分生成的 POST。
- 有意收紧：production/staging 拒绝不安全配置；列表和历史由无限结果改成有界页，客户端需要翻页；模型名限于服务配置；输出超限明确报错而非悄悄成功截断。
- 没有引入写入幂等键：重复提交消息仍是新轮次。没有支付/Webhook 等必须 exactly-once 的业务；未来若需要无重复重试，应先定义请求 ID、重放与流恢复语义。

### 安全改进

- staging/production 强制认证、至少 32 字节的非占位秘密、Redis、明确 Trusted Hosts、禁止 wildcard CORS、关闭 debug/docs 和数据库 auto-create，使用 JSON 日志与 PostgreSQL。
- 上游模型 production 使用 HTTPS；模型/业务 URL 限定为部署配置并拒绝 URL 内凭据、查询与 fragment，客户端不能提交任意 URL。
- Settings repr/校验错误隐藏秘密，health 只返回 Redis 后端名称；JWT/service token 不写入日志，校验异常仅暴露安全字段名。requestId 格式和长度校验，外部 HTTP 传递 correlation header。
- 纯 ASGI 接收层限制请求大小；上传限制内容、UTF-8/PDF 格式与 metadata JSON 对象，规范化 basename，文件名不作为服务器路径。
- Redis 故障准入返回安全 503，避免静默退回本地配额。资源越权、异常 JWT、过期/错误签名/错误 audience、生产配置拒绝均有测试。
- 依赖审计发现 PyJWT 旧版本记录，升级并加入无效签名字符和递归 Header 的 401 回归。Embedding 测试覆盖缺失向量、重复 index、混合维度、非有限数值和输入顺序一致性。部分记录涉及本服务没有使用的 JWKS/混合算法，未将所有记录都宣称为本服务可利用漏洞。发布依据：[PyJWT 2.15.0](https://github.com/jpadilla/pyjwt/releases/tag/2.15.0)。
- 限定模式的 Git 历史扫描未发现私钥、长 sk 密钥或 GitHub token；它不是完整 Secret Scanner，也不是渗透测试。

### 可观测性与部署

- 采用 ContextVar 日志上下文，移除全局 Logger.makeRecord 修改，避免并发请求串号；JSON 日志包含 service/environment/requestId，HTTP 完整生命周期记录 method/path/status/latency，具备 traceId 时记录。
- Prometheus 提供 HTTP 请求/状态、完整 SSE 耗时、活跃请求、AI 请求/用量估算/TTFT/活跃流、工具与 Provider 错误，以及标准进程指标。路由模板与工具名限制指标基数。
- `/health` 仅代表进程存活；`/ready` 并发执行有界数据库/Redis 探测，失败为 503。不会把 liveness 与 readiness 混为一谈。
- 保留 OpenTelemetry span 接口；没有伪造 tracing exporter 已接入。DB/Redis 池与上游详细时延监控仍需目标监控栈接入。
- 多阶段镜像冻结运行依赖、非 root 用户、构建排除 .env 与本地数据；Uvicorn 关闭宽限 100 秒，Compose stop_grace_period 110 秒，默认流截止 90 秒。
- 文档给出关闭 SSE 代理缓冲、read timeout、HTTPS 与可信 forwarded IP 的配置；metrics 应由私网/入口策略保护。
- CI 配置真实 PG17/pgvector 与 Redis7 测试服务，迁移往返、Ruff/mypy/pytest、生产依赖审计、wheel/sdist 与镜像构建。CI 文件已更新，本次没有远端触发 GitHub Actions。
- English/简体中文/日本語 README 和相关 VitePress 页面同步更新 Provider、SSE、配置、数据库与部署契约。

## 第四阶段：实际验收

| 检查 | 实际结果 |
|---|---|
| 冻结安装 | `uv sync --frozen --dev --offline` 成功，PyJWT 2.15.0 |
| Lint | `uv run ruff check .` 通过 |
| 格式 | `uv run ruff format --check .` 通过，105 个文件 |
| 类型 | `uv run mypy app` 通过，46 个源码文件，strict |
| pytest | **114 passed**，16.66 秒；包含 4 个真实基础设施测试，覆盖率 **88%** |
| PostgreSQL/pgvector | 独立可丢弃数据库 `vh5_ai_test`：事务回滚、向量检索/所有权/级联与迁移往返通过 |
| Redis | 独立 DB15：跨客户端配额原子性、过期/迟到释放、请求计数与会话锁通过 |
| SQLite 迁移 | upgrade/check/downgrade/upgrade 通过；schema 与 ORM 一致 |
| 包构建 | `uv build --offline` 成功生成 wheel 和 sdist |
| 文档 | `docs:typecheck` 与 VitePress 1.6.4 build 通过，使用 bundled Node 24.19 |
| Docker | 默认 `docker build -t vue-h5-template-ai-service:local .` 成功；最终镜像包含 PyJWT 2.15.0 |
| 生产容器 | health/ready 200，docs 404，匿名聊天 401；JWT 会话、Agent start/tools/deltas/finish、持久化用量与删除通过 |
| 真实 HTTP SSE | 52 个事件，首 delta 到结束间隔约 0.55 秒；断连后 active_streams=0 |
| SIGTERM | 本机与容器均出现 `Application shutdown complete.`，资源 lifespan 正常结束；本机 Uvicorn 重发 SIGTERM 返回 -15，容器返回 0 |
| 依赖审计 | 旧锁文件 13 条记录全部归属于 PyJWT 2.13.0；升级后 64 个生产依赖 **0 条已知漏洞** |

审计工具为 pip-audit 2.10.1。标准工具安装/查询出现 TLS 超时；使用只访问官方 PyPI 的临时 curl 传输获取相同版本 JSON，保留 pip-audit 原始漏洞解析和判定。审计按本机 Python/OS marker 检查冻结生产列表，原始摘要保存在 [DEPENDENCY_AUDIT.json](./DEPENDENCY_AUDIT.json)。结果是当日已知记录快照，不代表没有未知漏洞。项目/CI 仍使用标准官方索引与普通 pip-audit 命令，未写入临时代理或修改系统网络配置。

测试使用合成内容与临时密钥，未连接生产数据库、Redis 或真实收费模型。基础设施测试会拒绝非指定测试库名/Redis DB，使用独立 UUID 数据；未执行 flushall。迁移及运行检查使用本次创建的临时容器，验收后已清理；保留最终 `vue-h5-template-ai-service:local` 镜像。

## 未完成内容及有价值的后续工作

1. **真实 Provider 与 Go 联调**：没有提供上游凭据或目标部署。验证 OpenAI-compatible SSE、工具调用及业务服务 service-token/X-User-ID 的真实性能与授权；确认 Go 与此处的 JWT issuer/audience/secret 配置一致。
2. **精确计费与硬日配额**：流输出 token 是估算；日阈值只检查成功持久化记录，并发可以超出，旧无状态接口和中断轮次不入账。若进入收费业务，需要跨副本预留、结算/补偿、供应商真实 usage 与审计流水。
3. **强隔离文档处理**：当前线程池与输入限额避免普通 event-loop 阻塞，但恶意 PDF 解压/解析可能消耗大量 CPU/内存，线程取消不会强制终止解析。公开不可信大规模上传前改为独立限资源进程/持久 Worker，并规划隔离扫描、对象存储与任务状态。
4. **监控与容量**：接入 OTLP exporter、DB/Redis 池与上游细粒度时延指标，按目标 SLO 做并发/长连接压测。HTTP/DB/Redis 默认池参数是可配置起点，不是经过生产容量证明的最佳值。向量全量规模增大后用真实检索数据决定 HNSW/IVFFlat 与索引发布方式。
5. **入口与发布演练**：在实际代理验证 heartbeat/缓冲/断连、forwarded IP 白名单、metrics 私网访问、证书、备份恢复及滚动关闭。Docker/Compose 本地通过不等于这些生产部署条件已经落实。

上述工作需要真实业务策略或外部环境，没有为了泛化清单添加用户系统、缓存体系、MQ 或多余目录。
