# 贡献指南

感谢你有意参与贡献。本文档介绍工作流程；行为准则见
[CODE_OF_CONDUCT.md](https://github.com/fonghehe/vue-h5-template-ai-service/blob/main/CODE_OF_CONDUCT.md)。

## 环境准备

```bash
git clone https://github.com/fonghehe/vue-h5-template-ai-service.git
cd vue-h5-template-ai-service
cp .env.example .env
uv sync
```

需要 Python 3.12–3.14 与 [uv](https://docs.astral.sh/uv/)。

## 开发命令

```bash
make check     # lint + typecheck + test
make lint      # ruff check + ruff format --check
make typecheck # mypy --strict
make test      # pytest
make format    # ruff format + ruff check --fix
```

## 代码风格

- 格式化与 lint 由 **ruff** 强制（配置见 `pyproject.toml`）。
- 类型检查运行 **严格模式 mypy**。
- `app/schemas/` 中的模型是与 `@vh5/ai-chat` 的契约 —— 重命名字段属于破坏性变更。

## 新增供应商

1. 在 `app/providers/` 中实现 `ChatProvider`。
2. 在 `app/providers/factory.py` 中注册。
3. 在 `tests/` 下添加测试。
4. 更新配置参考中的 `AI_PROVIDER` 文档。

## Pull Request 检查清单

1. 新增或更新测试。
2. 本地运行 `make check` 并保持全绿。
3. 保持 SSE 事件结构与响应信封不变，除非有意做版本化。
4. 接口变化时同步更新文档。

## 发布

在 `pyproject.toml` 中提升版本号并打 tag。
