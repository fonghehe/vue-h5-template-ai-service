---
layout: home

hero:
  name: "ai-service"
  text: "vue-h5-template 的流式 AI"
  tagline: 一个供应商中立的 AI 服务，把结构化的消息列表换成 Server-Sent Events 流。
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/quickstart
    - theme: alt
      text: SSE 契约
      link: /zh/sse
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/fonghehe/vue-h5-template-ai-service

features:
  - title: 供应商中立
    details: 模型访问封装在 <code>ChatProvider</code> 接口之后 —— 离线 mock 与任意 OpenAI 兼容端点可无缝替换，无需改动传输层。
  - title: 开箱即用 SSE
    details: 发出 <code>start</code>、<code>delta</code>、<code>finish</code> 事件，<code>@vh5/ai-chat</code> 直接消费。
  - title: 共享身份
    details: 校验 Go 业务服务签发的同一套 JWT，登录过的用户在这里天然已认证。
  - title: 可运维
    details: 非 root Docker 镜像、健康/就绪探针、Redis 限流、结构化日志、GitHub Actions CI。
---

## 为什么要拆成独立服务？

这是 vue-h5-template 后端的流式半边：

| | 业务服务（Go） | AI 服务（Python） |
|---|---|---|
| 负载类型 | 短事务型 CRUD | 长连接流式 |
| 扩容维度 | 请求速率 | 并发流数量 |
| 故障模式 | 数据库延迟 | 上游模型延迟 |

拆开之后，慢模型供应商永远无法耗尽为登录与商品目录服务的连接池。

## 数据流

```
Vue H5 app ──POST /api/ai/chat──▶ ai-service ──▶ mock provider        (开发)
        ◀── SSE: start/delta/finish ──┘         └─▶ OpenAI-compatible  (生产)
```
