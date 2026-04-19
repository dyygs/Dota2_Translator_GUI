# -*- coding: utf-8 -*-
"""
依赖包管理模块
"""

import os
import sys
import subprocess

from .mirrors import MIRRORS
from .python_installer import PythonInstaller, STARTUPINFO

class DependencyManager:
    """依赖包管理器"""
    
    DEPENDENCIES = [
        ("numpy", "numpy==2.4.4"),
        ("cv2", "opencv-python==4.6.0.66"),
        ("PIL", "pillow==10.4.0"),
        ("paddle", "paddlepaddle==2.6.2"),
        ("paddleocr", "paddleocr==2.10.0"),
        ("keyboard", "keyboard==0.13.5"),
        ("pyperclip", "pyperclip==1.8.2"),
        ("pyautogui", "pyautogui==0.9.54"),
        ("requests", "requests==2.33.1"),
        ("mss", "mss==10.1.0"),
        ("pygetwindow", "pygetwindow==0.0.9"),
        ("pytweening", "pytweening==1.2.0"),
    ]
    
    @staticmethod
    def check_pip_module():
        """检查pip模块是否可用"""
        python_path = PythonInstaller.find_system_python()
        if not python_path:
            return False
        try:
            result = subprocess.run(
                [python_path, "-c", "import pip"],
                capture_output=True, timeout=10,
                startupinfo=STARTUPINFO
            )
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def check_dependency_installed(pkg_name):
        """检查依赖是否已安装"""
        python_path = PythonInstaller.find_system_python()
        if not python_path:
            return False
        try:
            result = subprocess.run(
                [python_path, "-c", f"import {pkg_name}"],
                capture_output=True, timeout=10,
                startupinfo=STARTUPINFO
            )
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def install_pip(runtime_dir, log_func=None):
        """安装pip"""
        import shutil
        import urllib.request
        import ssl
        
        python_path = PythonInstaller.find_system_python()
        if not python_path:
            log_func("Python未安装，无法安装pip") if log_func else None
            return False
        
        if DependencyManager.check_pip_module():
            log_func("pip模块可用") if log_func else None
            return True
        
        log_func("安装pip...") if log_func else None
        pip_script = os.path.join(runtime_dir, "get-pip.py")
        
        download_dir = PythonInstaller.get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        
        for url in MIRRORS["pip_script"]:
            try:
                local_path = os.path.join(download_dir, "get-pip.py")
                urllib.request.urlretrieve(url, local_path)
                
                if os.path.exists(pip_script):
                    os.remove(pip_script)
                shutil.move(local_path, pip_script)
                
                result = subprocess.run([python_path, pip_script], capture_output=True, timeout=300, startupinfo=STARTUPINFO)
                if result.returncode != 0:
                    log_func(f"pip安装失败: {result.stderr.decode('utf-8', errors='ignore')[:200]}") if log_func else None
                    return False
                else:
                    log_func("pip安装完成") if log_func else None
                    if DependencyManager.check_pip_module():
                        return True
                    else:
                        log_func("pip模块仍不可用") if log_func else None
                        return False
            except Exception as e:
                log_func(f"pip安装异常: {e}") if log_func else None
                continue
            finally:
                if os.path.exists(pip_script):
                    os.remove(pip_script)
        
        return False
    
    @staticmethod
    def install_dependency(name, pkg, mirror, env=None, log_func=None):
        """安装单个依赖"""
        python_path = PythonInstaller.find_system_python()
        if not python_path:
            return False, "Python not found"
        
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", pkg, "-i", mirror, "--no-cache-dir", 
                 "--trusted-host", mirror.split("://")[1].split("/")[0]],
                capture_output=True, timeout=600, env=env or os.environ.copy(),
                startupinfo=STARTUPINFO
            )
            if result.returncode == 0:
                return True, ""
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                return False, stderr[:500]
        except Exception as e:
            return False, str(e)[:200]
    
    @staticmethod
    def check_and_install_dependencies(log_func=None, progress_callback=None):
        """
        检查并安装所有依赖
        
        Args:
            log_func: 日志回调函数
            progress_callback: 进度回调函数(percent, 50-90范围)
            
        Returns:
            tuple: (成功与否, 已跳过数, 新安装数)
        """
        runtime_dir = PythonInstaller.get_runtime_dir()
        log = lambda msg: (log_func(msg) if log_func else None)
        
        total_deps = len(DependencyManager.DEPENDENCIES)
        installed_count = 0
        skipped_count = 0
        
        for idx, (module_name, pkg_name) in enumerate(DependencyManager.DEPENDENCIES):
            progress = f"[{idx+1}/{total_deps}]"
            log(f"检查依赖 {progress} {pkg_name}...")
            
            dep_progress = 50 + int((idx / total_deps) * 40)
            if progress_callback:
                progress_callback(dep_progress)

            if DependencyManager.check_dependency_installed(module_name):
                log(f"  {pkg_name} 已安装，跳过")
                skipped_count += 1
                continue

            log(f"  {pkg_name} 未安装，正在安装 {progress}...")

            if pkg_name == "paddlepaddle":
                mirror_list = MIRRORS["paddlepaddle"]
            else:
                mirror_list = MIRRORS["pip"]

            installed = False
            last_error = ""
            for mirror in mirror_list:
                success, error = DependencyManager.install_dependency(module_name, pkg_name, mirror, log_func=log_func)
                if success:
                    log(f"  {pkg_name} 安装成功 {progress}")
                    installed = True
                    installed_count += 1
                    break
                else:
                    last_error = error
                    log(f"  {mirror[:25]}... 失败: {error[:80]}")

            if not installed:
                log(f"  {pkg_name} 安装失败: {last_error[:150]}")
                return False, skipped_count, installed_count

        return True, skipped_count, installed_count
