# Agent、工具与 RAG

## 何时进入工作流

`mode="chat"` 直接调用 Provider 流；`agent` 进入 LangGraph；`auto` 仅对商品、计算、时间关键词进入 Agent。`app/services/agent.py` 的图是 `START -> classify -> agent -> (tool -> agent)* -> END`。目前 `classify` 只标记路径，不调用模型做分类。`AGENT_MAX_ITERATIONS` 限制循环。工具进度可流式发出，但最终答案在图完成后才切成 `delta`，**不是**模型逐 token 流。

## 工具安全边界

`app/tools/base.py` 的 `ToolRegistry` 只暴露注册名称，并用 Pydantic 验证参数。`get_current_time` 返回 UTC；`calculator` 只支持受限 AST 算术；`search_product` 固定 GET `BUSINESS_SERVICE_URL/api/v1/products`，传 `q`、可选 `maxPrice`、`limit`、`X-User-ID`，配置了令牌时才传 Bearer Token。模型不能指定 URL。Go 服务不包含在 Compose 中；需要在实际部署中核对其接口与信任策略。Prompt 将检索/工具文本视为不可信数据，但这不是提示注入的绝对防护。

## 知识库流程

`POST /api/knowledge/documents` 接收 multipart `file` 和可选 JSON 字符串 `metadata`。`KnowledgeService` 解析 UTF-8 txt/md 或可提取文字的 PDF，按字符重叠切块、Embedding 后入库。扫描 PDF 没有 OCR。默认上传上限 5 MB。PostgreSQL/pgvector 执行按用户限定的余弦 top-K；SQLite 回退为进程内排序。Mock Embedding 是用于测试的确定性哈希，不代表生产语义检索。

发送 `useRag=true` 时，路由对问题做 Embedding、检索自己的文档、将块文本加入上下文，并发送 `sources` 帧（`documentId`、`chunkId`、`title`）。引用只标识检索材料，不能证明答案每个论断都被材料支持。系统 Prompt `assistant.rag` v1 要求基于检索内容回答。

## 结构化输出与评估

`LLMProvider.structured_output()` 用 Pydantic 验证；HTTP 适配器遇到无效 JSON 会修复重试一次。`ProductRecommendation` 是 `app/schemas/knowledge.py` 中的示例 schema，当前**没有**公共 API 返回它。`evals/run.py` 只是离线冒烟检查：一个计算器案例和其他 Mock 补全文本非空检查，**不是**定量 RAG 基准。pytest 还覆盖部分检索、工具、结构化输出行为；绿灯不等于真实模型质量合格。
