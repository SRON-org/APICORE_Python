<div align="center">

<image src="https://github.com/user-attachments/assets/83078bfd-fb6a-4ffd-90b2-27bf7f611bf9" height="86"/>

# APICORE_Python

[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](VERSION)

APICORE access framework for Python

#### [Main Repo](https://github.com/SRON-org/APICORE)

</div>

## 介绍
APICORE_Python 是一个 Python 库，用于解析符合 APICORE 规范的 API 配置文件。

## 安装 （即将上架）

```bash
pip install APICORE_Python
```

## 功能特性

- 加载和验证 APICORE 配置文件
- 便捷访问配置参数
- 类型提示支持
- 完善的错误处理
- **可扩展的插件系统**

## 使用方法

```python
from APICORE import APICORE

# 加载并验证配置文件
cfg = APICORE("path/to/config.json").init()

# 访问配置项
print(cfg.friendly_name())  # API 友好名称
print(cfg.intro())  # API 介绍
print(cfg.icon())  # API 图标图片链接
print(cfg.link())  # API 端点URL
print(cfg.func())  # HTTP 方法
print(cfg.version())  # APICORE 版本

# 访问参数配置
for param in cfg.parameters():
    print(param['friendly_name'])

# 访问响应配置
print(cfg.response().image()['path'])  # 图片路径
for other in cfg.response().others():
    for data in other['data']:
        print(data['friendly_name'])
```

## 配置文件格式

APICORE 配置文件遵循特定的 JSON 格式，完整规范请参考 [APICORE_Wiki.md](https://github.com/SRON-org/APICORE/wiki/Create-a-New-APICORE-Configuration-File)。

## 插件开发指南

### 1. 插件位置
所有解析器插件应放置在 `APICORE/parsers/` 目录下

### 2. 命名规范
- 插件文件名：`[解析类型].py` (如 `image.py`, `video.py`)
- 解析函数名：`parse_[解析类型]` (如 `parse_image`, `parse_video`)

### 3. 插件模板
```python
from typing import Dict, Any

def parse_[解析类型](response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    [解析类型] 响应解析器
    
    参数:
        response_data: 完整的响应数据字典
        
    返回:
        解析后的[解析类型]配置字典
    """
    # 实现解析逻辑
    return response_data.get('[解析类型]', {})
```

### 4. 示例插件 (image.py)
```python
from typing import Dict, Any

def parse_image(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    图像响应解析器
    
    从响应数据中提取图像配置
    
    返回格式:
    {
        "content_type": "URL|BINARY",
        "path": "数据路径",
        "is_list": bool,
        "is_base64": bool
    }
    """
    return {
        'content_type': response_data.get('image', {}).get('content_type'),
        'path': response_data.get('image', {}).get('path'),
        'is_list': response_data.get('image', {}).get('is_list', False),
        'is_base64': response_data.get('image', {}).get('is_base64', False)
    }
```

### 5. 插件开发注意事项
1. 必须包含类型提示
2. 函数必须返回字典
3. 做好错误处理，避免因字段缺失导致异常
4. 保持函数纯净，不修改输入数据
5. 文档字符串需清晰说明功能和返回格式

### 6. 插件注册
插件会自动注册为 `response()` 的方法，例如：
- `image.py` → `response().image()`
- `video.py` → `response().video()`

## 许可证

MIT License
