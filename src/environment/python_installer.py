# -*- coding: utf-8 -*-
"""
Python安装和查找模块
"""

import os
import sys
import subprocess
import shutil
import winreg

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
    
    PYTHON_VERSION = "3.11.9"
    PYTHON_VERSION_SHORT = "3.11"
    
    @classmethod
    def get_default_python_dir(cls):
        """获取系统默认Python安装目录"""
        return os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Programs', 'Python', f'Python{cls.PYTHON_VERSION_SHORT.replace(".", "")}'
        )
    
    @classmethod
    def get_default_python_exe(cls):
        """获取系统默认Python可执行文件路径"""
        return os.path.join(cls.get_default_python_dir(), 'python.exe')
    
    @classmethod
    def get_data_dir(cls):
        """获取数据目录（始终使用文档目录）"""
        doc_dir = os.path.join(
            os.environ.get('USERPROFILE', ''),
            'Documents', 'Dota2Translator'
        )
        os.makedirs(doc_dir, exist_ok=True)
        return doc_dir
    
    @classmethod
    def get_old_data_dir(cls):
        """获取旧数据目录（D盘，用于迁移）"""
        return r"D:\Dota2Translator"
    
    @classmethod
    def _has_data_files(cls, directory):
        """检查目录是否有数据文件"""
        if not os.path.exists(directory):
            return False
        
        models_dir = os.path.join(directory, 'models')
        config_file = os.path.join(directory, 'config.json')
        
        return os.path.exists(models_dir) or os.path.exists(config_file)
    
    @classmethod
    def get_download_dir(cls):
        """获取下载目录"""
        return os.path.join(cls.get_data_dir(), 'downloads')
    
    @classmethod
    def get_registry_python_path(cls):
        """从注册表获取Python 3.11安装路径"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Python\PythonCore\{cls.PYTHON_VERSION_SHORT}\InstallPath"
            )
            path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            return path
        except FileNotFoundError:
            pass
        except Exception:
            pass
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                rf"SOFTWARE\Python\PythonCore\{cls.PYTHON_VERSION_SHORT}\InstallPath"
            )
            path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            return path
        except FileNotFoundError:
            pass
        except Exception:
            pass
        
        return None
    
    @classmethod
    def is_default_path(cls, path):
        """检查是否是系统默认安装路径"""
        if not path:
            return False
        
        default_dir = cls.get_default_python_dir()
        path_normalized = os.path.normpath(path).lower()
        default_normalized = os.path.normpath(default_dir).lower()
        
        return path_normalized.startswith(default_normalized)
    
    @classmethod
    def is_d_drive_path(cls, path):
        """检查是否是D盘路径"""
        if not path:
            return False
        return os.path.normpath(path).lower().startswith('d:\\')
    
    @classmethod
    def check_python_usable(cls, python_path):
        """检查Python是否可用"""
        if not python_path or not os.path.exists(python_path):
            return False
        
        try:
            result = subprocess.run(
                [python_path, '--version'],
                capture_output=True,
                timeout=5,
                startupinfo=STARTUPINFO
            )
            output = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')
            return f'Python {cls.PYTHON_VERSION_SHORT}' in output
        except Exception:
            return False
    
    @classmethod
    def find_system_python(cls):
        """
        查找系统中的Python 3.11
        
        Returns:
            str|None: Python可执行文件路径，如果未找到返回None
        """
        reg_path = cls.get_registry_python_path()
        
        if reg_path:
            python_exe = os.path.join(reg_path, 'python.exe')
            
            if cls.is_default_path(reg_path):
                if cls.check_python_usable(python_exe):
                    return python_exe
            else:
                return None
        
        default_exe = cls.get_default_python_exe()
        if cls.check_python_usable(default_exe):
            return default_exe
        
        possible_paths = [
            default_exe,
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python311', 'python.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python310', 'python.exe'),
        ]
        
        for python_path in possible_paths:
            if cls.check_python_usable(python_path):
                return python_path
        
        return None
    
    @classmethod
    def uninstall_python(cls, log_func=None):
        """卸载Python 3.11"""
        log = lambda msg: (log_func(msg) if log_func else None)
        
        from .mirrors import MIRRORS
        import urllib.request
        import ssl
        
        download_dir = cls.get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        
        exe_path = os.path.join(download_dir, f"python-{cls.PYTHON_VERSION}-amd64.exe")
        
        if not os.path.exists(exe_path):
            log(f"下载Python {cls.PYTHON_VERSION}安装包...")
            
            for url in MIRRORS["python"]:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    urllib.request.urlretrieve(url, exe_path)
                    log("下载成功!")
                    break
                except Exception as e:
                    log(f"  失败: {str(e)[:50]}")
            else:
                log("Python安装包下载失败")
                return False
        
        log("正在卸载旧版本Python...")
        try:
            result = subprocess.run(
                [exe_path, "/uninstall", "/quiet"],
                capture_output=True,
                timeout=120
            )
            log("卸载完成")
            return True
        except Exception as e:
            log(f"卸载失败: {e}")
            return False
    
    @classmethod
    def install_python(cls, log_func=None):
        """
        安装Python 3.11.9到系统默认目录
        
        Args:
            log_func: 日志回调函数
            
        Returns:
            bool: 是否安装成功
        """
        from .mirrors import MIRRORS
        import urllib.request
        import ssl
        
        log = lambda msg: (log_func(msg) if log_func else None)
        
        default_exe = cls.get_default_python_exe()
        
        if cls.check_python_usable(default_exe):
            log(f"Python {cls.PYTHON_VERSION}已安装: {default_exe}")
            return True
        
        reg_path = cls.get_registry_python_path()
        
        need_uninstall = False
        if reg_path:
            if cls.is_d_drive_path(reg_path):
                log("检测到Python安装在D盘，需要迁移到系统目录")
                need_uninstall = True
            elif not cls.is_default_path(reg_path):
                log("检测到Python安装在非默认位置，需要迁移")
                need_uninstall = True
            else:
                python_exe = os.path.join(reg_path, 'python.exe')
                if not os.path.exists(python_exe):
                    log("检测到Python注册表记录但文件不存在，需要重新安装")
                    need_uninstall = True
        
        if need_uninstall:
            cls.uninstall_python(log)
        
        download_dir = cls.get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        
        exe_path = os.path.join(download_dir, f"python-{cls.PYTHON_VERSION}-amd64.exe")
        
        if not os.path.exists(exe_path):
            log(f"下载Python {cls.PYTHON_VERSION}安装包...")
            
            for url in MIRRORS["python"]:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    urllib.request.urlretrieve(url, exe_path)
                    log("下载成功!")
                    break
                except Exception as e:
                    log(f"  失败: {str(e)[:50]}")
            else:
                log("Python安装包下载失败，请检查网络连接")
                return False
        
        target_dir = cls.get_default_python_dir()
        
        log(f"正在安装Python到 {target_dir}...")
        
        try:
            result = subprocess.run(
                [exe_path, "/quiet", "InstallAllUsers=0", f"TargetDir={target_dir}",
                 "PrependPath=0", "Include_test=0", "Include_pip=1"],
                capture_output=True,
                timeout=600
            )
            
            if cls.check_python_usable(default_exe):
                log(f"Python安装完成: {default_exe}")
                return True
            else:
                log(f"Python安装失败，返回码: {result.returncode}")
                return False
        except Exception as e:
            log(f"Python安装异常: {e}")
            return False
    
    @classmethod
    def migrate_data_from_d_drive(cls, log_func=None):
        """从D盘迁移数据到文档目录"""
        log = lambda msg: (log_func(msg) if log_func else None)
        
        d_dir = r"D:\Dota2Translator"
        doc_dir = os.path.join(
            os.environ.get('USERPROFILE', ''),
            'Documents', 'Dota2Translator'
        )
        
        if not os.path.exists(d_dir):
            return False
        
        if os.path.normpath(cls.get_data_dir()).lower() == os.path.normpath(d_dir).lower():
            return False
        
        log("检测到D盘有数据，正在迁移到文档目录...")
        
        migrated = []
        
        models_src = os.path.join(d_dir, 'models')
        models_dst = os.path.join(doc_dir, 'models')
        if os.path.exists(models_src) and not os.path.exists(models_dst):
            try:
                shutil.copytree(models_src, models_dst)
                migrated.append('models')
                log("  模型文件迁移完成")
            except Exception as e:
                log(f"  模型文件迁移失败: {e}")
        
        config_src = os.path.join(d_dir, 'config.json')
        config_dst = os.path.join(doc_dir, 'config.json')
        if os.path.exists(config_src) and not os.path.exists(config_dst):
            try:
                shutil.copy2(config_src, config_dst)
                migrated.append('config.json')
                log("  配置文件迁移完成")
            except Exception as e:
                log(f"  配置文件迁移失败: {e}")
        
        if migrated:
            log(f"数据迁移完成: {', '.join(migrated)}")
            return True
        
        return False
