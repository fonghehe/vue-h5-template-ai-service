# コントリビューション

```bash
cp .env.example .env
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m evals.run
```

`pyproject.toml` に厳格な mypy と ruff の設定があります。テストは Mock を使い、実際の OpenAI Key は不要です。DB schema を変更するときは Alembic マイグレーションを追加します。API、Provider、ツールの変更は[拡張ガイド](/ja/extending)を参照してください。

VitePress は `docs/` 内にあり、英語 `/`、中国語 `/zh/`、日本語 `/ja/` です。3 言語とサイドバーを同期してください。

```bash
cd docs
npm ci
npm run docs:dev
npm run docs:typecheck
npm run docs:build
```

ルートに pnpm docs スクリプトはありません。ローカル検索は有効で、ビルドは内部リンクを検査します。SSE/Provider 契約の変更は `AGENTS.md` に従いテストと文書も更新します。実 JWT、モデルの秘密鍵、ユーザー文書をコミットしないでください。
