# クイックスタート

オフラインのモックプロバイダーで AI サービスをローカル実行します — API キーは不要です。

## 前提条件

- **Python 3.12–3.14**
- **[uv](https://docs.astral.sh/uv/)** — パッケージと環境のマネージャー。

## インストールと実行

```bash
cp .env.example .env
uv sync                 # 固定されたロックファイルから依存関係をインストール
make dev                # :8001 で自動リロード付きで実行
```

`make dev` は `uv run uvicorn app.main:app --reload --port 8001` を実行します。デフォルトの `AI_PROVIDER=mock` では
サービスは固定のストリームを返すため、上流アカウントなしでトランスポート全体をテストできます。

## 試してみる

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Why is streaming useful?"}]}'
```

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"delta","delta":"keeps the UI honest. "}
data: {"type":"finish","reason":"stop"}
```

対話型の OpenAPI ドキュメントは `http://localhost:8001/docs` にあります。

## 実際のプロバイダーへ切り替え

任意の OpenAI 互換エンドポイントが動作します（OpenAI、Azure OpenAI、Together、Groq、Ollama、vLLM）：

```bash
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-…
AI_MODEL=gpt-4o-mini
```

完全な一覧は [設定](/ja/configuration) を参照してください。

## 開発ループ

```bash
make check     # lint + typecheck + test
make test      # pytest
make typecheck # mypy --strict
```

## 次のステップ

- [SSE 契約](/ja/sse) — 正確なイベント形状。
- [API リファレンス](/ja/api) — エンドポイントとレスポンスエンベロープ。
- [デプロイ](/ja/deployment) — 本番上の注意点、特にプロキシのバッファリング。
