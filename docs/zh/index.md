---
layout: home
hero:
  name: "vue-h5-template-ai-service"
  text: "AI 助手后端"
  tagline: 基于 FastAPI 的会话、受限上下文、工具与兼容 SSE 流式服务。
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/quickstart
    - theme: alt
      text: 架构
      link: /zh/architecture
    - theme: alt
      text: API
      link: /zh/api
features:
  - title: 保留前端契约
    details: POST /api/ai/chat 保留 @vh5/ai-chat 使用的 start、delta、finish、error。
  - title: 服务端会话
    details: JWT 限定的历史、摘要、用量记录和同一会话的顺序控制。
  - title: 有边界的 Agent
    details: 只有工具工作负载走 LangGraph；普通聊天直接流式调用 Provider。
  - title: 轻量知识库
    details: txt、md、pdf 入库；PostgreSQL/pgvector 检索并返回来源。
---


## 从这里开始

按[快速开始](./quickstart.md)运行 Mock 服务，通过 [API](./api.md)接入客户端，准备部署时阅读[部署指南](./deployment.md)。Go 负责签发 access JWT，本服务负责 AI 会话与文档检索。Mock 回答可用于验证接入流程，不代表真实模型质量。
