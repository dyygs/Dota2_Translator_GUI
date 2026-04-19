# -*- coding: utf-8 -*-
"""
环境检查核心模块
"""

import os
import sys
import time

from .python_installer import PythonInstaller
from .dependency_manager import DependencyManager

def get_log_file():
    """获取日志文件路径"""
    app_dir = _get_app_dir()
    return os.path.join(app_dir, "launcher.log")

def _get_app_dir():
    """获取应用目录（exe所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def log_to_file(msg):
    """写入日志文件"""
    log_file = get_log_file()
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

class EnvironmentChecker:
    """环境检查器"""
    
    @staticmethod
    def check_and_setup_environment(log_func=None, progress_callback=None):
        """
        检查并设置环境（逐项检查）
        
        Args:
            log_func: 日志回调函数
            progress_callback: 进度回调函数(percent)
            
        Returns:
            bool: 环境是否就绪
        """
        runtime_dir = PythonInstaller.get_runtime_dir()
        
        def log(msg):
            log_to_file(msg)
            print(f"[环境检查] {msg}")
            if log_func:
                log_func(msg)
        
        def report_progress(percent):
            if progress_callback:
                progress_callback(percent)
        
        log(f"项目目录: {_get_app_dir()}")
        log(f"运行时目录: {runtime_dir}")
        
        os.makedirs(runtime_dir, exist_ok=True)
        
        # 1. 检查/安装 Python (10% → 30%)
        report_progress(10)
        if not PythonInstaller.find_system_python():
            log("Python未安装，开始安装...")
            report_progress(15)
            if not PythonInstaller.install_python(runtime_dir, log):
                log("Python安装失败")
                return False
        else:
            log("Python已安装")
        report_progress(30)
        
        # 2. 检查/安装 pip (30% → 50%)
        if not DependencyManager.check_pip_module():
            log("pip未安装，开始安装...")
            report_progress(35)
            if not DependencyManager.install_pip(runtime_dir, log):
                log("pip安装失败")
                return False
        else:
            log("pip已安装")
        report_progress(50)
        
        # 3. 检查/安装依赖 (50% → 90%)
        success, skipped, installed = DependencyManager.check_and_install_dependencies(log_func=log, progress_callback=progress_callback)
        
        if not success:
            log("=" * 50)
            log(f"环境初始化失败: 依赖安装失败")
            log("=" * 50)
            return False
        
        log("=" * 50)
        log(f"依赖检查完成: {skipped}个已存在, {installed}个新安装, {len(DependencyManager.DEPENDENCIES)}个总计")
        log("=" * 50)

        report_progress(95)
        log("环境初始化完成!")
        log_to_file("环境初始化完成!")
        
        report_progress(100)

        return True
