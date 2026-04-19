# -*- coding: utf-8 -*-
"""
Python安装和查找模块
"""

import os
import sys
import subprocess
import ctypes
import platform

# 隐藏控制台窗口的配置
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
    
    @staticmethod
    def get_runtime_dir():
        """获取运行时目录（使用D盘短路径）"""
        return r"D:\Dota2Translator\runtime"
    
    @staticmethod
    def get_download_dir():
        """获取下载目录"""
        return r"D:\Dota2Translator\downloads"
    
    @staticmethod
    def find_system_python():
        """
        查找系统中的Python 3.11.9（动态查找，不硬编码路径）
        
        Returns:
            str|None: Python可执行文件路径，如果未找到返回None
        """
        # 先检查D盘安装的Python
        d_python = r"D:\Dota2Translator\python\python.exe"
        if os.path.exists(d_python):
            try:
                result = subprocess.run([d_python, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                ver_output = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')
                if '3.11.9' in ver_output:
                    return d_python
            except Exception as e:
                pass
        
        # 尝试从PATH中查找
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
                            if '3.11.9' in ver_output:
                                return p
                        except Exception as e:
                            continue
        except Exception as e:
            pass
        
        # 尝试常见路径（使用环境变量）
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if local_app_data:
            for ver in ['Python311', 'Python310', 'Python39']:
                path = os.path.join(local_app_data, 'Programs', 'Python', ver, 'python.exe')
                if os.path.exists(path):
                    try:
                        ver_result = subprocess.run([path, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                        ver_output = ver_result.stdout.decode('utf-8', errors='ignore') + ver_result.stderr.decode('utf-8', errors='ignore')
                        if '3.11.9' in ver_output:
                            return path
                    except Exception as e:
                        continue
        
        return None
    
    @staticmethod
    def install_python(runtime_dir, log_func=None):
        """
        安装Python完整版（包含tkinter）
        
        Args:
            runtime_dir: 运行时目录
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
        
        system_python = PythonInstaller.find_system_python()
        if system_python:
            log(f"发现系统Python: {system_python}")
            return True
        
        log("未发现系统Python，开始安装到D盘...")
        
        d_install_dir = r"D:\Dota2Translator\python"
        d_python_path = os.path.join(d_install_dir, "python.exe")
        
        if os.path.exists(d_python_path):
            log(f"D盘Python已安装: {d_python_path}")
            return True
        
        exe_path = os.path.join(runtime_dir, "python_installer.exe")
        if not os.path.exists(exe_path):
            log("下载Python完整版安装包...")
            
            download_dir = PythonInstaller.get_download_dir()
            os.makedirs(download_dir, exist_ok=True)
            
            last_error = None
            for url in MIRRORS["python"]:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    local_path = os.path.join(download_dir, "python_installer.exe")
                    urllib.request.urlretrieve(url, local_path)
                    
                    if os.path.exists(exe_path):
                        os.remove(exe_path)
                    shutil.move(local_path, exe_path)
                    
                    log("下载成功!")
                    break
                except Exception as e:
                    last_error = str(e)
                    log(f"  失败: {last_error[:50]}")
            else:
                log("Python下载失败，请检查网络连接")
                return False
        
        try:
            log("正在安装Python到D盘...")
            os.makedirs(d_install_dir, exist_ok=True)
            
            result = subprocess.run(
                [exe_path, "/passive", "InstallAllUsers=0", f"TargetDir={d_install_dir}", 
                 "PrependPath=0", "Include_test=0", "Include_pip=1"],
                capture_output=True, timeout=600
            )
            
            if os.path.exists(d_python_path):
                log(f"Python安装完成: {d_python_path}")
                return True
            else:
                log(f"Python安装失败，返回码: {result.returncode}")
                return False
        except Exception as e:
            log(f"Python安装异常: {e}")
            return False
