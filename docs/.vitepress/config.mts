import { defineConfig } from "vitepress";

const repo = "https://github.com/fonghehe/vue-h5-template-ai-service";

// The CLI does not set NODE_ENV=development before loading this config.
// Select the local root by the actual VitePress command; build/preview retain
// the repository sub-path required by GitHub Pages.
const base = process.argv.includes("dev") ? "/" : "/vue-h5-template-ai-service/";

const sidebar = (prefix: string, labels: string[]) => [
  {
    text: labels[0],
    items: [
      { text: labels[1], link: `${prefix}/` },
      { text: labels[2], link: `${prefix}/quickstart` },
      { text: labels[3], link: `${prefix}/configuration` },
      { text: labels[4], link: `${prefix}/deployment` },
    ],
  },
  {
    text: labels[5],
    items: [
      { text: labels[6], link: `${prefix}/architecture` },
      { text: labels[7], link: `${prefix}/conversations` },
      { text: labels[8], link: `${prefix}/agent-rag` },
      { text: labels[9], link: `${prefix}/sse` },
    ],
  },
  {
    text: labels[10],
    items: [
      { text: labels[11], link: `${prefix}/api` },
      { text: labels[12], link: `${prefix}/extending` },
      { text: labels[13], link: `${prefix}/contributing` },
    ],
  },
];

const en = {
  label: "English",
  lang: "en-US",
  title: "vue-h5-template-ai-service",
  description: "FastAPI AI assistant service with compatible SSE, conversations, tools and RAG.",
  themeConfig: {
    nav: [
      { text: "Guide", link: "/quickstart" },
      { text: "Architecture", link: "/architecture" },
      { text: "API", link: "/api" },
      { text: "GitHub", link: repo },
    ],
    sidebar: sidebar("", [
      "Start",
      "Introduction",
      "Quick start",
      "Configuration",
      "Deployment",
      "How it works",
      "Architecture",
      "Conversations and context",
      "Agent, tools and RAG",
      "SSE protocol",
      "Develop",
      "API reference",
      "Extension guide",
      "Contributing",
    ]),
    search: { provider: "local" as const },
    outline: { level: [2, 3] as [number, number] },
    editLink: { pattern: `${repo}/edit/main/docs/:path` },
    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2026 fonghehe",
    },
  },
};

const zh = {
  label: "简体中文",
  lang: "zh-CN",
  title: "vue-h5-template-ai-service",
  description: "FastAPI AI 助手服务：兼容 SSE、会话、工具与 RAG。",
  themeConfig: {
    nav: [
      { text: "指南", link: "/zh/quickstart" },
      { text: "架构", link: "/zh/architecture" },
      { text: "API", link: "/zh/api" },
      { text: "GitHub", link: repo },
    ],
    sidebar: sidebar("/zh", [
      "入门",
      "项目简介",
      "快速开始",
      "配置参考",
      "部署",
      "实现原理",
      "架构",
      "会话与上下文",
      "Agent、工具与 RAG",
      "SSE 协议",
      "开发",
      "API 参考",
      "扩展指南",
      "贡献指南",
    ]),
    search: {
      provider: "local" as const,
      options: {
        locales: {
          zh: {
            translations: {
              button: {
                buttonText: "搜索文档",
                buttonAriaLabel: "搜索文档",
              },
              modal: {
                displayDetails: "显示详情",
                resetButtonTitle: "清除查询",
                backButtonTitle: "关闭搜索",
                noResultsText: "无结果",
                footer: {
                  selectText: "选择",
                  navigateText: "切换",
                  closeText: "关闭",
                },
              },
            },
          },
        },
      },
    },
    outline: { level: [2, 3] as [number, number], label: "本页目录" },
    editLink: {
      pattern: `${repo}/edit/main/docs/:path`,
      text: "在 GitHub 上编辑此页",
    },
    footer: {
      message: "基于 MIT 许可证发布。",
      copyright: "Copyright © 2026 fonghehe",
    },
  },
};

const ja = {
  label: "日本語",
  lang: "ja-JP",
  title: "vue-h5-template-ai-service",
  description: "SSE、会話、ツール、RAG を備えた FastAPI AI アシスタントサービス。",
  themeConfig: {
    nav: [
      { text: "ガイド", link: "/ja/quickstart" },
      { text: "構成", link: "/ja/architecture" },
      { text: "API", link: "/ja/api" },
      { text: "GitHub", link: repo },
    ],
    sidebar: sidebar("/ja", [
      "開始",
      "概要",
      "クイックスタート",
      "設定",
      "デプロイ",
      "仕組み",
      "アーキテクチャ",
      "会話とコンテキスト",
      "エージェント・ツール・RAG",
      "SSE プロトコル",
      "開発",
      "API リファレンス",
      "拡張ガイド",
      "コントリビューション",
    ]),
    search: {
      provider: "local" as const,
      options: {
        locales: {
          ja: {
            translations: {
              button: {
                buttonText: "文書を検索",
                buttonAriaLabel: "文書を検索",
              },
              modal: {
                displayDetails: "詳細を表示",
                resetButtonTitle: "検索をクリア",
                backButtonTitle: "検索を閉じる",
                noResultsText: "結果がありません",
                footer: {
                  selectText: "選択",
                  navigateText: "移動",
                  closeText: "閉じる",
                },
              },
            },
          },
        },
      },
    },
    outline: { level: [2, 3] as [number, number], label: "このページの目次" },
    editLink: {
      pattern: `${repo}/edit/main/docs/:path`,
      text: "GitHub でこのページを編集",
    },
    footer: {
      message: "MIT ライセンスの下で公開されています。",
      copyright: "Copyright © 2026 fonghehe",
    },
  },
};

export default defineConfig({
  lang: "en-US",
  base,
  cleanUrls: false,
  locales: {
    root: en,
    zh: zh,
    ja: ja,
  },
});
