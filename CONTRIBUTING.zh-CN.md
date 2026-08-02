[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh-CN.md)

# 为 APICORE_Python 做贡献

感谢您帮助改进 APICORE_Python。贡献可以包括缺陷报告、解析器修复、验证改进、
测试、性能优化以及文档修正。

## 开始之前

- 在提交重复内容之前，请先搜索已有的 Issues 和 Pull Requests。
- 每次变更聚焦于一个问题。在实施之前，请先在 Issue 中讨论广泛的 API 变更或
  破坏性行为。
- 按照 [SECURITY.md](SECURITY.md) 中所述，私下报告疑似漏洞，不要在公开的
  Issue 中报告。
- APICORE 规范的变更应首先在相应的规范仓库中进行。本项目应实现已文档化的
  APICORE 行为，而不是独立定义冲突的格式。

## 开发环境搭建

本项目需要 Python 3.12 或更高版本，并使用
[uv](https://docs.astral.sh/uv/) 进行依赖和环境管理。

```bash
git clone https://github.com/SRON-org/APICORE_Python.git
cd APICORE_Python
uv sync --all-groups
```

需要时从本地检出运行仓库工具：

```bash
uv run python tools/cli.py path/to/config.api.yaml
uv run python tools/gui.py
```

CLI 和 GUI 是仅供仓库使用的工具。它们不得成为安装的包模块或
console-script 入口点。

## 进行更改

- 遵循现有的 Python 风格，并为公共和内部接口保留类型注解。
- 保持公共导入面审慎。新的公共 API 必须从 `src/apicore/__init__.py` 导出，
  并由公共 API 测试覆盖。
- 保持 APICORE v1、v2.0 和 v2.1 的兼容性，除非提议的变更明确记录了破坏性变更。
- 解码失败时返回 `ParseError`，APICORE 结构无效时返回 `ValidationError`。
  在可能的情况下，在验证消息中包含精确的 JSON 风格路径。
- 不要修改调用者传递给 `parse()` 的映射。
- 将配置内容视为不可信的。解析器或工具的更改不得执行 `run` 脚本、调用配置的
  URL、泄露密钥值，或将 YAML 切换为不安全的加载器。
- 为每个行为变更和回归修复添加或更新测试。优先使用嵌入在相关测试中的小型
  固定数据，而不是大型生成的工件。
- 当用户可见的行为、兼容性或工作流发生变更时，更新 `README.md`、本地 `docs/`
  源文件和 `CHANGELOG.md`。
- 不要提交虚拟环境、缓存、构建输出、凭据、令牌或不相关的生成文件。

## 验证

在提交 Pull Request 之前，运行项目期望的相同核心检查：

```bash
uvx ruff format --check .
uvx ruff check .
uv run pytest -q
uv build
```

解析器变更应使用所有受影响的序列化格式和 APICORE 版本进行测试。
打包变更必须保持以下不变量：

- Wheel 仅包含核心 `apicore` 库。
- 已安装的包中不包含 `tools/`。
- 不安装 `apicore-validate` 或 `apicore-gui` 入口点。

对于与发布相关的变更，还请遵循 [RELEASING.md](RELEASING.md)。

## Pull Requests

Pull Request 应：

- 解释问题和所选的解决方案。
- 在适用时引用相关的 Issue 或 APICORE 规范章节。
- 描述兼容性、安全性和性能影响。
- 包含没有修复时失败、修复后通过的测试。
- 列出已运行的验证命令，并披露任何未能完成的检查。
- 避免将重构、依赖更新、格式化变更和行为变更合并在一起，除非它们不可分割。

维护者可能会要求更改以保护包边界、公共 API、支持的 APICORE 版本或安全模型。
贡献只有在经过维护者审查并合并后才被视为已接受。

## 许可证

通过提交贡献，您同意该贡献可以按照项目 [LICENSE](LICENSE) 的条款分发，
并且您确认您有权提交所贡献的材料。