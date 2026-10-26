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


## ここから始める

[クイックスタート](./quickstart.md)で Mock サービスを起動し、[API](./api.md)でクライアントを接続します。環境準備は[デプロイ](./deployment.md)を参照してください。Go が access JWT を発行し、本サービスが AI 会話と文書検索を担当します。Mock は接続の確認用で、実モデル品質を示しません。
