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

## 仓库职责

这是 Python AI 服务，不是 Vue 前端。兄弟 Go 服务负责登录、签发 JWT 和商品 CRUD；本服务验证 JWT、保存 AI 会话，并只通过注册工具访问 Go 商品 API。这里没有 `src/`、页面路由、前端 store、浏览器主题、国际化或移动布局。

先看[快速开始](/zh/quickstart)、[架构](/zh/architecture)和 [API](/zh/api)。离线 Mock 只验证传输与业务流程，不能证明真实模型质量或 Go 服务已经集成成功。
