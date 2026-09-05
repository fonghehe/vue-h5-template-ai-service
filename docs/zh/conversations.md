# 会话与上下文

`POST /api/ai/chat` 为 `@vh5/ai-chat` 保留无状态模式。需要后端拥有历史时，使用 `/api/conversations`。所有持久化接口都必须提供 Go 服务签发的**用户 JWT**；匿名和服务令牌不能拥有会话。Repository 会检查所有权。

## 发送一轮

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"购物咨询"}'
# 将返回的 data.id 赋给 AI_CONVERSATION_ID：
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"你好","mode":"chat","useRag":false}'
```

`mode` 可以是 `auto`（默认）、`chat`、`agent`。`auto` 仅通过 `app/api/v1/conversations.py` 的商品、计算、时间关键词判断，不是通用意图分类器。`GET /api/conversations/{id}` 返回按顺序排列的消息、摘要和引用；列表只返回会话概要；DELETE 删除自己的会话及消息。

## 上下文预算

`app/services/context.py` 的 `ContextBuilder` 将版本化系统 Prompt、摘要、可选检索/工具内容和最近消息组合起来。约按每三字符一 token 加消息开销估算，**并非** Provider 的真实 tokenizer。历史超过 `AI_CONTEXT_TOKEN_BUDGET` 时，通过 `LLMProvider.complete()` 摘要旧消息并保存到 `conversation.summary`；Prompt/检索文本可能截断。测试包含 100 条历史消息。

同一会话用锁串行化，不同 ID 可并行；Redis 能跨副本协调，否则仅本进程有效。成功完成的轮次保存助手消息和 `UsageRecord`，断连可能留下已保存的用户消息而无助手回复。`GET /api/usage/me` 按模型、会话、日期汇总成功的持久化轮次；旧聊天不记入。直接流的 token 数是估算值，Agent 使用可用的 Provider 用量数据。这不是计费系统。
