---
layout: home
hero:
  name: "vue-h5-template-ai-service"
  text: "AI アシスタントのバックエンド"
  tagline: FastAPI による会話保存、コンテキスト制限、ツール、互換 SSE ストリーミング。
  actions:
    - theme: brand
      text: クイックスタート
      link: /ja/quickstart
    - theme: alt
      text: アーキテクチャ
      link: /ja/architecture
    - theme: alt
      text: API
      link: /ja/api
features:
  - title: 既存クライアントとの互換性
    details: POST /api/ai/chat は @vh5/ai-chat の start、delta、finish、error を維持します。
  - title: サーバー管理の会話
    details: JWT による履歴、要約、使用量記録と会話単位の順序制御。
  - title: 境界のあるエージェント
    details: ツールが必要な処理だけ LangGraph を使い、通常のチャットは直接ストリームします。
  - title: 小規模ナレッジベース
    details: txt、md、pdf を登録し、PostgreSQL/pgvector で検索して出典を返します。
---

## このリポジトリの責務

これは Python の AI サービスで、Vue フロントエンドではありません。別の Go ビジネスサービスがログイン、JWT 発行、商品 CRUD を担当します。このサービスは JWT を検証し、AI 会話を保存し、登録済みツールを通じてのみ Go の商品 API を呼びます。`src/`、画面ルーター、フロントエンド store、ブラウザテーマ、i18n、モバイルレイアウトはありません。

[開始手順](/ja/quickstart)、[アーキテクチャ](/ja/architecture)、[API](/ja/api) の順に参照してください。オフライン Mock は通信経路を確認するためのもので、実際のモデル品質や Go 連携の稼働を証明しません。
