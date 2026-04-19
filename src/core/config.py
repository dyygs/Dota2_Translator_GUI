# -*- coding: utf-8 -*-
"""
配置管理模块 - 完整版（替代原GUI中的Config类）
"""

import os
import sys
import json
import copy

class Config:
    """配置管理器 - 完整版"""
    
    DEFAULT_CONFIG = {
        "trigger_key": "f6",
        "toggle_hotkey": "ctrl+alt+t",
        "cooldown": 0.2,
        "source_lang": "zh-CN",
        "target_lang": "en",
        "strict_mode_enabled": True,
        "strict_mode_position": "",
        "realtime_enabled": False,
        "realtime_hotkey": "f7",
        "capture_region": {"x": 718, "y": 732, "width": 611, "height": 25},
        "danmaku_position": {"x": -200, "y": 300},
        "show_region_border": False,
        "realtime_settings": {
            "interval": 3.0,
            "display_duration": 5.0,
            "max_messages": 5,
            "font_size": 16,
            "original_color": "#FFFFFF",
            "translated_color": "#00FF00",
            "bg_alpha": 0.5
        }
    }
    
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = self._get_default_config_file()
        self.config_file = config_file
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.load_config()
    
    def _get_default_config_file(self):
        """获取默认配置文件路径（exe所在目录）"""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "config.json")
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        """
        获取配置值
        支持嵌套键：'realtime_settings.interval'
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default if default is not None else self._get_default(key)
        return value
    
    def set(self, key: str, value):
        """
        设置配置值
        支持嵌套键：'realtime_settings.interval'
        """
        keys = key.split('.')
        data = self.config
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
    
    def get_all(self):
        """获取完整配置字典"""
        return self.config.copy()
    
    def update(self, data: dict):
        """批量更新配置"""
        self.config.update(data)
        self.save_config()
    
    def reset(self):
        """重置为默认配置"""
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.save_config()
    
    @property
    def trigger_key(self) -> str:
        return self.get('trigger_key', 'f6')
    
    @property
    def realtime_hotkey(self) -> str:
        return self.get('realtime_hotkey', 'f7')
    
    @property
    def email(self) -> str:
        return self.get('email', '')
    
    @property
    def strict_mode_enabled(self) -> bool:
        return self.get('strict_mode_enabled', True)
    
    @property
    def realtime_enabled(self) -> bool:
        return self.get('realtime_enabled', False)
    
    def _get_default(self, key: str):
        """从默认配置中获取值"""
        keys = key.split('.')
        value = self.DEFAULT_CONFIG
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
