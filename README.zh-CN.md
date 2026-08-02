[English](README.md) | [中文](README.zh-CN.md)

<div align="center">

<img width="86" height="86" alt="APICORE娘-圆角图标" src="https://github.com/user-attachments/assets/17814599-a2af-4605-8a18-be7d1fef2c8d" />

# APICORE_Python

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python版本](https://img.shields.io/badge/Python-3.8%2B-brightgreen)
![版本号](https://img.shields.io/badge/Version-2.1.0-lightblue)

面向 Python 的 APICORE 配置文件格式规范访问框架

#### [主仓库](https://github.com/SRON-org/APICORE-2)

</div>

## APICORE

高性能 APICORE 解析器和验证器，支持 APICORE v1、v2.0 和 v2.1。

由 [小树工作室](https://github.com/Little-Tree-Studio) 和 [SRON 团队](https://github.com/SRON-org/) 合作开发。

### 特性

- 导入名称为 `apicore`，而发布的包名称为 `APICORE_Python`。
- 使用 `orjson` 实现快速 JSON 解码。
- 使用 `ruamel.yaml` 配合 `ruamel.yaml.clib` 实现 YAML 解码。
- 保留 `msgspec` 实现快速 TOML 解码。
- 通过单一 API 支持 APICORE v1、v2.0 和 v2.1。
- 当省略 `APICORE_version` 时，保留 APICORE v2.0 的语义；而当文档使用仅适用于 v2.1 的字段或本地化值时，则推断为 v2.1。
- 在 `Parameter.extra` 中保留自定义 v2 参数字段。
- 支持 v2.1 元数据、`$schema`、i18n UI 字符串、请求体类型、轮询和条件参数。
- 支持 v2.1 枚举 `options` 使用标量默认值，同时保留 v2.0 的 `friendly_value` 形式。
- 通过 `response.media` 支持图像、音频、视频、文本、Markdown 和文件输出。
- 暴露 `response.preferred_media`，优先使用 v2.1 `media` 并自动适配旧版 `image`。
- 保持发布的包专注于解析和验证；不安装 CLI 或 GUI 模块。
- 在 `tools/` 下提供仅供仓库使用的 CLI 和桌面验证器工具。
- 暴露类型化文档模型以及 `APICoreError`、`ParseError` 和 `ValidationError`，用于精确的错误处理。

### 安装

```bash
uv add APICORE_Python
```

或

```bash
pip install APICORE_Python
```

安装仅提供 `apicore` Python 库。它不会安装 `apicore-validate` 或
`apicore-gui` 命令。

### 快速开始

```python
from apicore import __version__, load, loads

print(__version__)

document = load("example.api.yaml")
print(document.apicore_version)

inline = loads(
    """
friendly_name: Demo
link: https://api.example.com/v2/generate
func: POST
APICORE_version: '2.1'
parameters:
  - name: style
    type: enum
    friendly_name:
      zh-CN: 风格
      en-US: Style
    options: [realistic, anime]
    friendly_options: [Realistic, Anime]
    value: realistic
response:
  media:
    type: image
    content_type: URL
    path: data.output.url
""",
    format="yaml",
)

forced_v1 = loads(
    """
{
	"friendly_name": "Legacy",
	"link": "https://api.example.com/legacy",
	"func": "POST",
	"APICORE_version": "1.0",
	"parameters": [],
	"response": {
		"image": {
			"content_type": "URL",
			"path": "data.image.url"
		}
	}
}
""",
    version="v1",
)
```

### 仓库 CLI 工具

从仓库检出使用：

```bash
uv sync
uv run python tools/cli.py path/to/config.api.yaml
uv run python tools/cli.py path/to/config.api.json --version v1
uv run python tools/cli.py path/to/config.api.toml --version 2.1
```

### 仓库桌面工具

```bash
uv sync
uv run python tools/gui.py
```

在 Windows 上，同步后可使用 `.venv\Scripts\pythonw.exe tools\gui.py` 无控制台
启动。某些 Linux 发行版需要系统 `python3-tk` 包。

GUI 可验证多个 APICORE 文档，并显示 v2.1 元数据、本地化参数、媒体映射、
请求体、轮询、配置和处理程序。密钥值会被遮蔽，`run` 处理程序会被标记为高风险。

### 错误处理

```python
from apicore import load
from apicore.errors import APICoreError, ParseError, ValidationError

try:
    doc = load("example.api.yaml")
except ParseError as exc:
    print(f"语法错误: {exc}")
except ValidationError as exc:
    print(f"模式错误: {exc}")
except APICoreError as exc:
    print(f"APICORE 错误: {exc}")
```

### 基准测试

```bash
uv run python benchmarks/parse_benchmark.py
```

### 发布工作流

```bash
uv sync --all-groups
uv run pytest -q
uv build
uv run --with twine twine check dist/*
```

详细发布步骤请参见 [RELEASING.zh-CN.md](RELEASING.zh-CN.md)。

贡献设置、编码规范、验证命令和 Pull Request 要求请参见
[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

### 文档

Wiki 文档手动发布到
[GitHub Wiki](https://github.com/SRON-org/APICORE_Python/wiki)。本地 `docs/`
上传源文件被 Git 有意忽略。APICORE v2.1 规范和 JSON Schema 维护在
[APICORE-2](https://github.com/SRON-org/APICORE-2)。

请参见 [SECURITY.zh-CN.md](SECURITY.zh-CN.md) 了解 `run` 操作信任边界、安全宿主集成指南和
依赖安全实践。请参见 [DISCLAIMER.zh-CN.md](DISCLAIMER.zh-CN.md) 了解执行责任和免责信息。