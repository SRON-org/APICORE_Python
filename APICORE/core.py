import json
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Any

class Response:
    """响应包装器(支持插件化解析)"""
    
    def __init__(self, response_data: Dict[str, Any]):
        self.data = response_data
        self._load_parsers()
        
    def _load_parsers(self):
        parsers_dir = Path(__file__).parent / 'parsers'
        if parsers_dir.exists():
            for _, name, _ in pkgutil.iter_modules([str(parsers_dir)]):
                try:
                    module = importlib.import_module(f'APICORE.parsers.{name}')
                    if hasattr(module, f'parse_{name}'):
                        setattr(self, name, lambda: getattr(module, f'parse_{name}')(self.data))
                except ImportError:
                    continue
                
    def others(self) -> List[Dict[str, Any]]:
        """获取配置中的其他响应配置"""
        return self.data.get('others', [])

class APICORE:
    """APICORE 规范的 API 配置文件解析器"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
    def init(self) -> 'APICORE':
        """初始化并检查配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            # 验证这个配置文件是否达到基础的合格标准
            if not all(key in self.config for key in ['friendly_name', 'link', 'func', 'APICORE_version', 'parameters','response']):
                raise ValueError("配置文件中缺少部分必填字段 ('friendly_name', 'link', 'func', 'APICORE_version', 'parameters','response')")
                
            if self.config['APICORE_version'] != '1.0':
                raise ValueError("不受支持的 APICORE 版本")
                
            return self
            
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"配置文件验证失败: {str(e)}")
    
    def friendly_name(self) -> str:
        """获取 API 友好名称"""
        return self.config['friendly_name']
    
    def intro(self) -> str:
        """获取 API 描述"""
        return self.config.get('intro', '')
    
    def icon(self) -> str:
        """获取 API 的图标图片链接"""
        return self.config.get('icon', '')
    
    def link(self) -> str:
        """获取 API 链接"""
        return self.config['link']
    
    def func(self) -> str:
        """获取 API 调用方法"""
        return self.config['func']
    
    def version(self) -> str:
        """获取 APICORE 版本"""
        return self.config['APICORE_version']
    
    def parameters(self) -> List[Dict[str, Any]]:
        """获取参数配置列表"""
        return self.config.get('parameters', [])
    
    def response(self) -> Response:
        """获取响应配置列表"""
        return Response(self.config.get('response', {}))    
