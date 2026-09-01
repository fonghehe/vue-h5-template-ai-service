---
layout: home

hero:
  name: "ai-service"
  text: "vue-h5-template のストリーミング AI"
  tagline: 型付きメッセージリストを Server-Sent Events ストリームに変換する、プロバイダー中立な AI サービス。
  actions:
    - theme: brand
      text: クイックスタート
      link: /ja/quickstart
    - theme: alt
      text: SSE 契約
      link: /ja/sse
    - theme: alt
      text: GitHub で見る
      link: https://github.com/fonghehe/vue-h5-template-ai-service

features:
  - title: プロバイダー中立
    details: モデルアクセスは <code>ChatProvider</code> インターフェースの背後にあり、オフラインのモックと任意の OpenAI 互換エンドポイントを、トランスポートに手を加えず入れ替えられます。
  - title: SSE を標準搭載
    details: <code>start</code>、<code>delta</code>、<code>finish</code> イベントを発行し、<code>@vh5/ai-chat</code> が直接消費します。
  - title: 共有アイデンティティ
    details: Go のビジネスサービスが発行した同じ JWT を検証するため、ログイン済みユーザーはここでも認証済みです。
  - title: 運用即応
    details: 非 root Docker イメージ、ヘルス/レディネスプローブ、Redis 対応レート制限、構造化ログ、GitHub Actions CI。
---

## なぜ別サービスなのか？

これは vue-h5-template バックエンドペアのストリーミング側です：

| | ビジネスサービス (Go) | AI サービス (Python) |
|---|---|---|
| ワークロード | 短いトランザクション CRUD | 長時間のストリーミング |
| スケーリング | リクエストレート | 同時ストリーム数 |
| 障害モード | データベース遅延 | 上流モデルの遅延 |

分離しておくことで、遅いモデルプロバイダーがログインやカタログを提供する接続プールを使い果たすことはありません。

## パイプライン

```
Vue H5 アプリ ──POST /api/ai/chat──▶ ai-service ──▶ モックプロバイダー        (開発)
        ◀── SSE: start/delta/finish ──┘         └─▶ OpenAI 互換  (本番)
```
