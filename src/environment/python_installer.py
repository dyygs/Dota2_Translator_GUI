# -*- coding: utf-8 -*-
"""
Python安装和查找模块
"""

import os
import sys
import subprocess
import ctypes
import platform

def get_startupinfo():
    """获取隐藏窗口的启动信息"""
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None

STARTUPINFO = get_startupinfo()

class PythonInstaller:
    """Python安装管理器"""
    
    _python_dir = None
    _download_dir = None
    
    @classmethod
    def get_app_dir(cls):
        """获取应用主目录"""
        return r"D:\Dota2Translator"
    
    @classmethod
    def get_python_dir(cls):
        """获取Python目录"""
        if cls._python_dir is None:
            cls._python_dir = os.path.join(cls.get_app_dir(), "python")
        return cls._python_dir
    
    @classmethod
    def get_download_dir(cls):
        """获取下载目录（临时存放安装包等）"""
        if cls._download_dir is None:
            cls._download_dir = os.path.join(cls.get_app_dir(), "downloads")
        return cls._download_dir
    
    @classmethod
    def get_python_exe(cls):
        """获取Python可执行文件路径"""
        return os.path.join(cls.get_python_dir(), "python.exe")
    
    @classmethod
    def get_pip_exe(cls):
        """获取pip可执行文件路径"""
        return os.path.join(cls.get_python_dir(), "Scripts", "pip.exe")
    
    @staticmethod
    def find_system_python():
        """
        查找系统中的Python 3.11+
        
        Returns:
            str|None: Python可执行文件路径，如果未找到返回None
        """
        possible_paths = []
        
        possible_paths.extend([
            PythonInstaller.get_python_exe(),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python311', 'python.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python310', 'python.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python39', 'python.exe'),
        ])
        
        for python_path in possible_paths:
            if os.path.exists(python_path):
                try:
                    result = subprocess.run([python_path, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                    ver_output = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')
                    if 'Python 3.' in ver_output:
                        return python_path
                except Exception:
                    pass
        
        try:
            result = subprocess.run(['where', 'python'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
            if result.returncode == 0:
                paths = result.stdout.decode('utf-8', errors='ignore').strip().split('\n')
                for p in paths:
                    p = p.strip()
                    if p and os.path.exists(p):
                        try:
                            ver_result = subprocess.run([p, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                            ver_output = ver_result.stdout.decode('utf-8', errors='ignore') + ver_result.stderr.decode('utf-8', errors='ignore')
                            if 'Python 3.' in ver_output:
                                return p
                        except Exception:
                            continue
        except Exception:
            pass
        
        return None
    
    @classmethod
    def install_python(cls, log_func=None):
        """
        安装Python完整版到 D:\Dota2Translator\python
        
        Args:
            log_func: 日志回调函数
            
        Returns:
            bool: 是否安装成功
        """
        from .mirrors import MIRRORS
        import shutil
        import urllib.request
        import ssl
        import time
        
        log = lambda msg: (log_func(msg) if log_func else None)
        
        python_dir = cls.get_python_dir()
        python_exe = cls.get_python_exe()
        
        if os.path.exists(python_exe):
            log(f"Python已安装: {python_exe}")
            return True
        
        system_python = cls.find_system_python()
        if system_python and system_python != python_exe:
            log(f"发现系统Python: {system_python}")
            return True
        
        log("未发现Python，开始安装...")
        
        download_dir = cls.get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(python_dir, exist_ok=True)
        
        exe_path = os.path.join(download_dir, "python_installer.exe")
        
        if not os.path.exists(exe_path):
            log("下载Python完整版安装包...")
            
            last_error = None
            for url in MIRRORS["python"]:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    urllib.request.urlretrieve(url, exe_path)
                    log("下载成功!")
                    break
                except Exception as e:
                    last_error = str(e)
                    log(f"  失败: {last_error[:50]}")
            else:
                log("Python下载失败，请检查网络连接")
                return False
        
        try:
            log(f"正在安装Python到 {python_dir}...")
            
            result = subprocess.run(
                [exe_path, "/passive", "InstallAllUsers=0", f"TargetDir={python_dir}", 
                 "PrependPath=0", "Include_test=0", "Include_pip=1"],
                capture_output=True, timeout=600
            )
            
            if os.path.exists(python_exe):
                log(f"Python安装完成: {python_exe}")
                return True
            else:
                log(f"Python安装失败，返回码: {result.returncode}")
                return False
        except Exception as e:
            log(f"Python安装异常: {e}")
            return False
