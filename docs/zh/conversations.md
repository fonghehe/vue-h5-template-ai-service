# 会话与上下文

`POST /api/ai/chat` 为 `@vh5/ai-chat` 保留无状态模式。需要后端拥有历史时，使用 `/api/conversations`。所有持久化接口都必须提供 Go 服务签发的**用户 JWT**；匿名和服务令牌不能拥有会话。Repository 会检查所有权。

## 发送一轮

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"购物咨询"}'
# 将返回的 data.id 赋给 AI_CONVERSATION_ID：
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"你好","mode":"chat","useRag":false}'
```

`mode` 可以是 `auto`（默认）、`chat`、`agent`。`auto` 仅通过 `app/services/conversations.py` 的商品、计算、时间关键词判断，不是通用意图分类器。`GET /api/conversations/{id}` 返回按顺序排列的消息、摘要和引用；列表只返回会话概要；DELETE 删除自己的会话及消息。

## 上下文预算

`app/services/context.py` 的 `ContextBuilder` 将版本化系统 Prompt、摘要、可选检索/工具内容和最近消息组合起来。约按每三字符一 token 加消息开销估算，**并非** Provider 的真实 tokenizer。历史超过 `AI_CONTEXT_TOKEN_BUDGET` 时，通过 `LLMProvider.complete()` 摘要旧消息并保存到 `conversation.summary`；Prompt/检索文本可能截断。测试包含 100 条历史消息。

成功轮次的助手消息、工具历史和用量原子提交。直接流/最终答案的 token 数是估算，规划使用可用的 Provider 用量。每日阈值检查已完成记录，并发时可能超过阈值；旧聊天和中断轮次不入账。这是准入阈值，尚非精确计费或预付费预留系统。

列表支持 `page`（1–100000）、`page_size`（1–100，默认 50），保留原列表信封。会话详情默认返回最近 100 条消息，通过 `page_size` 和 `before=<sequence>` 查询更早消息；消息新增 `sequence`。上下文最多读取最近 200 条，摘要输入有上限，保留最新用户消息，过大时拒绝。持久化消息同时受 20000 字符和上下文预算限制。旧 `/api/*` 路径保留，业务路由新增 `/api/v1/*` 别名。
