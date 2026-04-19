# -*- coding: utf-8 -*-
"""
环境检查模块 - 兼容层
⚠️ 已废弃：请使用 src.environment.checker.EnvironmentChecker

此文件保留用于向后兼容，实际功能已迁移到：
- src/environment/checker.py (新)
- src/environment/dependency_manager.py (新)
- src/environment/python_installer.py (新)
"""

import warnings

warnings.warn(
    "environment_checker 已废弃，请使用 from src.environment.checker import EnvironmentChecker",
    DeprecationWarning,
    stacklevel=2
)

try:
    from src.environment.checker import EnvironmentChecker as NewEnvironmentChecker
    
    class EnvironmentChecker(NewEnvironmentChecker):
        """兼容层：继承自新模块的EnvironmentChecker"""
        pass
        
except ImportError:
    EnvironmentChecker = None
