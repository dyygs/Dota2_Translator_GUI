# -*- coding: utf-8 -*-
"""
Dota2翻译器启动器
负责检查环境并启动主程序
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import ssl
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time

VERSION = "2.2.0"

_main_process = None

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

# 启用Windows长路径支持
def enable_long_path_support():
    """尝试启用Windows长路径支持"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        
        # 获取当前进程
        process_handle = kernel32.GetCurrentProcess()
        
        # 尝试启用长路径（需要Windows 10 1607+）
        # 这是一个尝试，不保证成功
        import platform
        if platform.version().startswith('10.'):
            try:
                ctypes.windll.ntdll.RtlAddEnableExtendedFeatures(process_handle, 0x1)
            except:
                pass
    except:
        pass

enable_long_path_support()

# 获取短路径（8.3格式）
def get_short_path(path):
    """获取短路径格式（8.3格式）"""
    try:
        import ctypes
        # 先确保路径存在
        if os.path.isfile(path):
            pass  # 文件已存在
        elif os.path.isdir(path):
            pass  # 目录已存在
        else:
            # 路径不存在，无法获取短路径
            return path
        
        short_path = ctypes.create_buffer(260)
        result = ctypes.windll.kernel32.GetShortPathNameW(path, short_path, 260)
        if result > 0:
            return short_path.value.decode('utf-8')
    except:
        pass
    return path

# 获取日志文件路径
def get_log_file():
    """获取日志文件路径"""
    return os.path.join(get_app_dir(), "launcher.log")

def log_to_file(msg):
    """同时写入日志文件和console"""
    log_file = get_log_file()
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

# 镜像地址配置
MIRRORS = {
    "pip": [
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
        "https://pypi.mirrors.ustc.edu.cn/simple",
        "https://pypi.doubanio.com/simple",
    ],
    "python": [
        "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe",
        "https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe",
        "https://npm.taobao.org/mirrors/python/3.11.9/python-3.11.9-amd64.exe",
    ],
    "pip_script": [
        "https://mirrors.aliyun.com/pypi/get-pip.py",
        "https://pypi.tuna.tsinghua.edu.cn/simple/get-pip.py",
        "https://pypi.mirrors.ustc.edu.cn/simple/get-pip.py",
    ],
    "paddlepaddle": [
        "https://www.paddlepaddle.org.cn/packages/stable/cpu/",
        "https://mirrors.aliyun.com/pypi/simple",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
    ],
}

# 使用项目目录作为下载目录
def get_app_dir():
    """获取应用目录（exe所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_src_dir():
    """获取源码目录（打包后在_MEIPASS，开发时在项目目录）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后，资源文件在_MEIPASS目录
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        # 如果_MEIPASS不存在，退回到exe目录
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_runtime_dir():
    """获取运行时目录（使用D盘短路径）"""
    return r"D:\Dota2Translator\runtime"

def get_long_path(path):
    """将路径转换为支持长路径的格式（使用\\?\前缀）"""
    if not path:
        return path
    if path.startswith("\\\\?\\"):
        return path
    abs_path = os.path.abspath(path)
    if abs_path[1] == ':':
        return "\\\\?\\" + abs_path
    return abs_path

def get_download_dir():
    """获取下载目录"""
    return r"D:\Dota2Translator\downloads"

def download_with_mirrors(urls, dest_path, log_func=None):
    """使用多个镜像下载文件"""
    # 使用项目目录作为下载目录
    download_dir = get_download_dir()
    os.makedirs(download_dir, exist_ok=True)
    
    filename = os.path.basename(dest_path)
    local_path = os.path.join(download_dir, filename)
    if log_func:
        log_func(f"下载保存目录: {download_dir}")
        log_func(f"文件: {filename}")
    
    last_error = None
    for i, url in enumerate(urls):
        try:
            if log_func:
                log_func(f"尝试镜像 {i+1}/{len(urls)}: {url[:40]}...")
            
            # 创建SSL上下文
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # 下载到当前目录
            def reporthook(block_num, block_size, total_size):
                if log_func and total_size > 0:
                    percent = min(100, int((block_num * block_size * 100) / total_size))
                    if block_num % 20 == 0:  # 每20个块显示一次
                        log_func(f"  下载进度: {percent}%")
            
            urllib.request.urlretrieve(url, local_path, reporthook)
            
            # 移动到目标位置
            if os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(local_path, dest_path)
            
            if log_func:
                log_func(f"下载成功!")
            return True
        except Exception as e:
            last_error = str(e)
            if log_func:
                log_func(f"  失败: {last_error[:50]}")
            continue
    
    if log_func:
        log_func(f"所有镜像都下载失败: {last_error}")
    return False

def check_python_installed(runtime_dir):
    """检查Python是否已安装"""
    return find_system_python() is not None

def check_pip_module(runtime_dir):
    """检查pip模块是否可用"""
    python_path = find_system_python()
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

def check_pip_installed(runtime_dir):
    """检查pip是否已安装且可用"""
    return check_pip_module(runtime_dir)

def check_dependency_installed(runtime_dir, pkg_name):
    """检查依赖是否已安装"""
    python_path = find_system_python()
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

def find_system_python():
    """查找系统中的Python 3.11.9（动态查找，不硬编码路径）"""
    # 先检查D盘安装的Python
    d_python = r"D:\Dota2Translator\python\python.exe"
    if os.path.exists(d_python):
        # 检查版本
        try:
            result = subprocess.run([d_python, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
            ver_output = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')
            if '3.11.9' in ver_output:
                return d_python
        except Exception as e:
            log(f"检查D盘Python版本失败: {e}")
            pass
    
    # 尝试从PATH中查找
    try:
        result = subprocess.run(['where', 'python'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
        if result.returncode == 0:
            paths = result.stdout.decode('utf-8', errors='ignore').strip().split('\n')
            for p in paths:
                p = p.strip()
                if p and os.path.exists(p):
                    # 检查版本是否为3.11.9
                    try:
                        ver_result = subprocess.run([p, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                        ver_output = ver_result.stdout.decode('utf-8', errors='ignore') + ver_result.stderr.decode('utf-8', errors='ignore')
                        if '3.11.9' in ver_output:
                            return p
                    except Exception as e:
                        log(f"检查PATH中Python版本失败: {e}")
                        continue
    except Exception as e:
        log(f"从PATH查找Python失败: {e}")
        pass
    
    # 尝试常见路径（使用环境变量）
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        for ver in ['Python311', 'Python310', 'Python39']:
            path = os.path.join(local_app_data, 'Programs', 'Python', ver, 'python.exe')
            if os.path.exists(path):
                # 检查版本
                try:
                    ver_result = subprocess.run([path, '--version'], capture_output=True, timeout=5, startupinfo=STARTUPINFO)
                    ver_output = ver_result.stdout.decode('utf-8', errors='ignore') + ver_result.stderr.decode('utf-8', errors='ignore')
                    if '3.11.9' in ver_output:
                        return path
                except Exception as e:
                    log(f"检查C盘Python版本失败 ({ver}): {e}")
                    continue

    return None

def install_python(runtime_dir, log):
    """安装Python完整版（包含tkinter）"""
    # 先检查系统是否已有Python
    system_python = find_system_python()
    if system_python:
        log(f"发现系统Python: {system_python}")
        return True
    
    log("未发现系统Python，开始安装到D盘...")
    
    # D盘安装目录
    d_install_dir = r"D:\Dota2Translator\python"
    d_python_path = os.path.join(d_install_dir, "python.exe")
    
    # 检查是否已安装到D盘
    if os.path.exists(d_python_path):
        log(f"D盘Python已安装: {d_python_path}")
        return True
    
    # 下载安装包
    exe_path = os.path.join(runtime_dir, "python_installer.exe")
    if not os.path.exists(exe_path):
        log("下载Python完整版安装包...")
        if not download_with_mirrors(MIRRORS["python"], exe_path, log):
            log("Python下载失败，请检查网络连接")
            return False
    
    try:
        log("正在安装Python到D盘...")
        os.makedirs(d_install_dir, exist_ok=True)
        
        # 安装到D盘指定目录
        result = subprocess.run(
            [exe_path, "/passive", "InstallAllUsers=0", f"TargetDir={d_install_dir}", 
             "PrependPath=0", "Include_test=0", "Include_pip=1"],
            capture_output=True, timeout=600
        )
        
        # 检查安装是否成功
        if os.path.exists(d_python_path):
            log(f"Python安装完成: {d_python_path}")
            return True
        else:
            log(f"Python安装失败，返回码: {result.returncode}")
            return False
    except Exception as e:
        log(f"Python安装异常: {e}")
        return False

def enable_pip_module(runtime_dir, log):
    """启用pip模块（修改pth文件）"""
    pth_file = os.path.join(runtime_dir, "python311._pth")
    try:
        if os.path.exists(pth_file):
            with open(pth_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # 取消注释 import site
            if '#import site' in content:
                content = content.replace('#import site', 'import site')
                with open(pth_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                log("已启用site模块")
                return True
            elif 'import site' in content:
                log("site模块已启用")
                return True
    except Exception as e:
        log(f"修改pth文件失败: {e}")
    return False

def install_pip(runtime_dir, log):
    """安装pip"""
    python_path = find_system_python()
    if not python_path:
        log("Python未安装，无法安装pip")
        return False
    
    # 检查 pip 模块是否可用
    if check_pip_module(runtime_dir):
        log("pip模块可用")
        return True
    
    # pip 模块不可用，需要安装
    log("安装pip...")
    pip_script = os.path.join(runtime_dir, "get-pip.py")
    
    if not download_with_mirrors(MIRRORS["pip_script"], pip_script, log):
        log("pip安装脚本下载失败")
        return False
    
    try:
        result = subprocess.run([python_path, pip_script], capture_output=True, timeout=300, startupinfo=STARTUPINFO)
        if result.returncode != 0:
            log(f"pip安装失败: {result.stderr.decode('utf-8', errors='ignore')[:200]}")
            return False
        else:
            log("pip安装完成")
            # 再次检查 pip 模块是否可用
            if check_pip_module(runtime_dir):
                return True
            else:
                log("pip模块仍不可用")
                return False
    except Exception as e:
        log(f"pip安装异常: {e}")
        return False
    finally:
        if os.path.exists(pip_script):
            os.remove(pip_script)

def install_dependency(runtime_dir, name, pkg, mirror, log, env):
    """安装单个依赖（使用 python -m pip 避免路径问题）"""
    python_path = find_system_python()
    if not python_path:
        return False, "Python not found"
    
    try:
        # 使用 python -m pip 而不是直接调用 pip.exe
        result = subprocess.run(
            [python_path, "-m", "pip", "install", pkg, "-i", mirror, "--no-cache-dir", "--trusted-host", mirror.split("://")[1].split("/")[0]],
            capture_output=True, timeout=600, env=env,
            startupinfo=STARTUPINFO
        )
        if result.returncode == 0:
            return True, ""
        else:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            return False, stderr[:500]
    except Exception as e:
        return False, str(e)[:200]

def get_check_result_file():
    """获取检查结果缓存文件路径"""
    return r"D:\Dota2Translator\check_result.txt"

def save_check_result(success, python_path=""):
    """保存检查结果"""
    result_file = get_check_result_file()
    try:
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(f"success={success}\n")
            f.write(f"python={python_path}\n")
            f.write(f"time={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except:
        pass

def load_check_result():
    """加载检查结果"""
    result_file = get_check_result_file()
    if not os.path.exists(result_file):
        return None
    try:
        result = {}
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    result[key] = value
        return result
    except:
        return None

def check_and_setup_environment(log_func=None):
    """检查并设置环境（逐项检查）"""
    app_root = get_app_dir()
    runtime_dir = get_runtime_dir()
    
    def log(msg):
        log_to_file(msg)
        print(f"[环境检查] {msg}")
        if log_func:
            log_func(msg)
    
    log(f"项目目录: {app_root}")
    log(f"运行时目录: {runtime_dir}")
    
    # 确保运行时目录存在
    os.makedirs(runtime_dir, exist_ok=True)
    
    # 1. 检查/安装 Python
    if not check_python_installed(runtime_dir):
        log("Python未安装，开始安装...")
        if not install_python(runtime_dir, log):
            log("Python安装失败")
            return False
    else:
        log("Python已安装")
    
    # 2. 检查/安装 pip
    if not check_pip_installed(runtime_dir):
        log("pip未安装，开始安装...")
        if not install_pip(runtime_dir, log):
            log("pip安装失败")
            return False
    else:
        log("pip已安装")
    
    # 3. 检查/安装依赖
    deps = [
        ("numpy", "numpy<2.0.0"),
        ("cv2", "opencv-python<=4.6.0.66"),
        ("PIL", "pillow>=9.0.0"),
        ("paddle", "paddlepaddle==2.6.2"),
        ("paddleocr", "paddleocr>=2.7.0,<3.0.0"),
        ("keyboard", "keyboard==0.13.5"),
        ("pyperclip", "pyperclip==1.8.2"),
        ("pyautogui", "pyautogui==0.9.54"),
        ("requests", "requests>=2.32.0"),
        ("mss", "mss>=9.0.0"),
    ]
    
    # 设置环境变量
    python_path = os.path.join(runtime_dir, "python.exe")
    log(f"Python路径: {python_path}")
    
    env = os.environ.copy()
    # 使用系统临时目录避免长路径问题
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp(prefix="dota2_")
    env["TEMP"] = temp_dir
    env["TMP"] = temp_dir
    log(f"临时目录: {temp_dir}")

    try:
        # 逐项检查并安装依赖
        total_deps = len(deps)
        installed_count = 0
        skipped_count = 0

        for idx, (module_name, pkg_name) in enumerate(deps):
            progress = f"[{idx+1}/{total_deps}]"
            log(f"检查依赖 {progress} {pkg_name}...")

            # 检查是否已安装
            if check_dependency_installed(runtime_dir, module_name):
                log(f"  {pkg_name} 已安装，跳过")
                skipped_count += 1
                continue

            log(f"  {pkg_name} 未安装，正在安装 {progress}...")

            # 选择合适的镜像
            if pkg_name == "paddlepaddle":
                mirror_list = MIRRORS["paddlepaddle"]
            else:
                mirror_list = MIRRORS["pip"]

            # 尝试多个镜像安装
            installed = False
            last_error = ""
            for mirror in mirror_list:
                success, error = install_dependency(runtime_dir, module_name, pkg_name, mirror, log, env)
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
                log("=" * 50)
                log(f"环境初始化失败: {pkg_name} 安装失败")
                log("=" * 50)
                return False

        # 总结
        log("=" * 50)
        log(f"依赖检查完成: {skipped_count}个已存在, {installed_count}个新安装, {total_deps}个总计")
        log("=" * 50)

        log("环境初始化完成!")
        log_to_file("环境初始化完成!")

        # 保存检查结果
        python_path = find_system_python()
        save_check_result(True, python_path or "")

        return True
    finally:
        # 清理临时目录
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                log(f"临时目录已清理: {temp_dir}")
            except Exception as e:
                log(f"清理临时目录失败: {e}")

def run_main_program():
    """运行主程序"""
    global _main_process
    src_dir = get_src_dir()
    log_to_file(f"src_dir: {src_dir}")
    log_to_file(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
    
    main_script = os.path.join(src_dir, "src", "dota2_translator_gui.py")
    
    log_to_file(f"准备启动主程序: {main_script}")
    log_to_file(f"主程序文件存在: {os.path.exists(main_script)}")
    
    if not os.path.exists(main_script):
        log_to_file(f"错误: 主程序文件不存在!")
        return
    
    python_path = find_system_python()
    log_to_file(f"Python路径: {python_path}")
    
    if not python_path:
        log_to_file(f"错误: 未找到Python，请重新运行安装程序")
        return
    
    error_log = os.path.join(get_app_dir(), "main_error.log")
    
    try:
        log_to_file(f"正在启动主程序...")
        with open(error_log, 'w', encoding='utf-8') as err_file:
            _main_process = subprocess.Popen(
                [python_path, main_script],
                stderr=err_file,
                stdout=err_file,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        time.sleep(2)
        poll_result = _main_process.poll()
        if poll_result is not None:
            log_to_file(f"主程序已退出，返回码: {poll_result}")
            if os.path.exists(error_log):
                with open(error_log, 'r', encoding='utf-8') as f:
                    error_content = f.read()
                    if error_content:
                        log_to_file(f"错误输出: {error_content[:1000]}")
        else:
            log_to_file(f"主程序已启动（进程ID: {_main_process.pid}）")
    except Exception as e:
        log_to_file(f"启动主程序失败: {e}")

def main():
    """主函数"""
    global _main_process  # 声明使用全局变量
    
    # 写入启动日志
    log_to_file("=" * 50)
    log_to_file("启动器开始运行")
    log_to_file("=" * 50)
    
    # 检查缓存，如果上次成功就直接启动
    cached_result = load_check_result()
    if cached_result and cached_result.get('success') == 'True':
        python_path = cached_result.get('python', '')
        if python_path and os.path.exists(python_path):
            log_to_file(f"使用缓存的Python: {python_path}")
            src_dir = get_src_dir()
            main_script = os.path.join(src_dir, "src", "dota2_translator_gui.py")
            if os.path.exists(main_script):
                error_log = os.path.join(get_app_dir(), "main_error.log")
                try:
                    with open(error_log, 'w', encoding='utf-8') as err_file:
                        _main_process = subprocess.Popen(
                            [python_path, main_script],
                            stderr=err_file,
                            stdout=err_file,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    time.sleep(2)
                    poll_result = _main_process.poll()
                    if poll_result is not None:
                        log_to_file(f"主程序已退出，返回码: {poll_result}")
                        if os.path.exists(error_log):
                            with open(error_log, 'r', encoding='utf-8') as f:
                                error_content = f.read()
                                if error_content:
                                    log_to_file(f"错误输出: {error_content[:1000]}")
                    else:
                        log_to_file(f"主程序已启动（使用缓存，进程ID: {_main_process.pid}）")
                    
                    # 等待主程序结束，避免临时文件清理失败
                    if _main_process is not None and _main_process.poll() is None:
                        log_to_file("等待主程序结束...")
                        _main_process.wait()
                        log_to_file("主程序已结束")
                    return
                except Exception as e:
                    log_to_file(f"启动失败，重新检查: {e}")
    
    # 创建启动窗口
    root = tk.Tk()
    root.title(f"DOTA2翻译小助手 v{VERSION} - 启动器")
    root.geometry("600x400")
    root.resizable(False, False)
    root.attributes('-topmost', True)  # 保持窗口在最前台
    
    # 标题
    title_label = tk.Label(root, text="DOTA2翻译小助手", font=("Microsoft YaHei", 20, "bold"))
    title_label.pack(pady=20)
    
    # 状态标签
    status_var = tk.StringVar(value="检查环境中...")
    status_label = tk.Label(root, textvariable=status_var, font=("Microsoft YaHei", 12))
    status_label.pack(pady=10)
    
    # 进度条
    progress = ttk.Progressbar(root, mode='determinate', length=500)
    progress.pack(pady=20)
    
    # 日志文本框
    log_text = scrolledtext.ScrolledText(root, height=10, width=70)
    log_text.pack(pady=10)
    
    def log_func(msg):
        log_text.insert(tk.END, f"{msg}\n")
        log_text.see(tk.END)
        root.update()
    
    def update_status(msg, percent=None):
        status_var.set(msg)
        if percent is not None:
            progress['value'] = percent
        root.update()
    
    def init_thread():
        """初始化线程"""
        update_status("检查环境中...", 10)
        
        success = check_and_setup_environment(log_func)
        
        if success:
            update_status("环境就绪，启动主程序...", 100)
            time.sleep(1)
            root.quit()  # 使用 quit 而不是 destroy，这样可以在 mainloop 后继续执行
        else:
            update_status("环境初始化失败", 0)
            log_func("=" * 50)
            log_func("初始化失败!")
            log_func("请检查:")
            log_func("1. 网络连接是否正常")
            log_func("2. 是否有管理员权限")
            log_func("3. 磁盘空间是否充足")
            log_func("=" * 50)
            log_func("请截图此窗口发送给开发者")
            # 保持窗口不关闭
            retry_btn = tk.Button(root, text="重试", command=lambda: threading.Thread(target=init_thread, daemon=True).start())
            retry_btn.pack(pady=10)
    
    # 启动初始化线程
    threading.Thread(target=init_thread, daemon=True).start()
    
    root.mainloop()
    
    # mainloop 结束后，在主线程中运行主程序
    run_main_program()
    
    # 等待主程序结束
    if _main_process is not None:
        try:
            log_to_file("等待主程序结束...")
            _main_process.wait(timeout=300)  # 最多等待5分钟
            log_to_file(f"主程序已结束，返回码: {_main_process.returncode}")
        except subprocess.TimeoutExpired:
            log_to_file("等待超时，强制退出")
        except Exception as e:
            log_to_file(f"等待主程序时出错: {e}")
    else:
        log_to_file("未启动主程序，启动器退出")
    
    log_to_file("=" * 50)
    log_to_file("启动器退出")
    log_to_file("=" * 50)

if __name__ == "__main__":
    main()
