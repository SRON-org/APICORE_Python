[English](RELEASING.md) | [中文](RELEASING.zh-CN.md)

# 发布 APICORE

## 前置条件

- 确认 `pyproject.toml` 中的版本号。
- 确保 `uv.lock` 是最新的。
- 确保工作树仅包含预期的发布变更。

## 验证

```bash
uv sync --all-groups
uvx ruff format --check .
uvx ruff check .
uv run pytest -q
uv build
uv run --with twine twine check dist/*
```

检查构建的 wheel，确认它仅包含核心 `apicore` 库。它不得包含
`apicore/cli.py`、`apicore/gui.py`、`tools/` 或 console-script 入口点。
同时冒烟测试仓库工具：

```bash
uv run python tools/cli.py --help
uv run python -c "import runpy; runpy.run_path('tools/gui.py', run_name='gui_smoke')"
```

## 发布

使用基于令牌的工作流发布到 PyPI：

```bash
set UV_PUBLISH_TOKEN=pypi-***
uv publish
```

如果需要使用 TestPyPI：

```bash
set UV_PUBLISH_TOKEN=pypi-***
uv publish --publish-url https://test.pypi.org/legacy/
```

## 发布后

- 创建与发布版本匹配的 git 标签。
- 如果同时在 GitHub 上发布，将 `dist/*` 工件附加到发布中。
- 更新 `CHANGELOG.md` 为下一个版本做准备。