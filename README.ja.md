# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

[vue-h5-template](https://github.com/fonghehe/vue-h5-template) 向け FastAPI AI バックエンドです。SSE の逐次チャット、会話保存、登録済みツール、文書検索（RAG）を提供します。JWT の発行と商品 API は別の Go サービスが担当します。

## ローカル起動

Python 3.12–3.14 と uv が必要です。既定は SQLite とオフライン Mock モデルで、モデルキーは不要です。起動後、別の端末で curl を実行します。

```bash
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn app.main:app --reload --port 8001
```

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

ローカルでも会話保存と文書 API には Go 発行のユーザー access JWT が必要です。Mock テストは実モデル品質や本番容量を示すものではありません。

## 次に読む

- [ローカル環境](./docs/ja/quickstart.md)
- [API と認証](./docs/ja/api.md)
- [配信プロトコル](./docs/ja/sse.md)
- [設定](./docs/ja/configuration.md)
- [デプロイ](./docs/ja/deployment.md)
- [開発とテスト](./docs/ja/contributing.md)

[VitePress](https://fonghehe.github.io/vue-h5-template-ai-service/ja/) · [MIT](./LICENSE)
