# -*- coding: utf-8 -*-
"""
Dota2翻译器启动器
负责检查环境并启动主程序（子进程模式 + PYTHONPATH注入）
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading

VERSION = "2.3.0"

_main_process = None

def get_app_dir():
    """获取应用目录（exe所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_meipass():
    """获取PyInstaller临时解压目录"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def log_to_file(msg):
    """写入日志文件"""
    log_file = os.path.join(get_app_dir(), "launcher.log")
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

def run_main_program():
    """运行主程序（子进程模式，通过PYTHONPATH注入_MEIPASS）"""
    global _main_process
    
    meipass = get_meipass()
    main_script = os.path.join(meipass, "src", "dota2_translator_gui.py")
    
    log_to_file(f"准备启动主程序: {main_script}")
    log_to_file(f"MEIPASS: {meipass}")
    log_to_file(f"文件是否存在: {os.path.exists(main_script)}")
    
    if not os.path.exists(main_script):
        log_to_file("错误: 主程序文件不存在!")
        return
    
    python_path = None
    try:
        from src.environment.python_installer import PythonInstaller
        python_path = PythonInstaller.find_system_python()
    except Exception as e:
        log_to_file(f"导入PythonInstaller失败: {e}")
    
    if not python_path:
        log_to_file("未找到Python，尝试备用路径...")
        python_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'python.exe')
        if not os.path.exists(python_path):
            python_path = None
    
    if not python_path:
        log_to_file("错误: 未找到Python")
        return
    
    log_to_file(f"使用Python: {python_path}")
    
    error_log = os.path.join(get_app_dir(), "main_error.log")
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = meipass
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        with open(error_log, 'w', encoding='utf-8') as err_file:
            _main_process = subprocess.Popen(
                [python_path, "-u", main_script],
                stderr=err_file,
                stdout=err_file,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo,
                cwd=get_app_dir(),
                env=env
            )
        time.sleep(3)
        poll_result = _main_process.poll()
        if poll_result is not None:
            log_to_file(f"主程序已退出，返回码: {poll_result}")
            if os.path.exists(error_log):
                with open(error_log, 'r', encoding='utf-8') as f:
                    error_content = f.read()
                    if error_content:
                        log_to_file(f"错误输出:\n{error_content[:2000]}")
                        print(f"[启动器] 主程序错误:\n{error_content[:2000]}")
        else:
            log_to_file(f"主程序已成功启动（PID: {_main_process.pid}）")
    except Exception as e:
        log_to_file(f"启动主程序失败: {e}")
        import traceback
        log_to_file(traceback.format_exc())

def main():
    """主函数"""
    global _main_process
    
    log_to_file("=" * 50)
    log_to_file("启动器开始运行 (v{})".format(VERSION))
    log_to_file("=" * 50)
    
    from src.environment.checker import EnvironmentChecker
    
    def update_status(msg, percent=None):
        status_var.set(msg)
        if percent is not None:
            progress['value'] = percent
        root.update_idletasks()
    
    def log_func(msg):
        log_text.insert(tk.END, f"{msg}\n")
        log_text.see(tk.END)
        root.update_idletasks()
    
    def init_thread():
        """初始化线程"""
        try:
            success = EnvironmentChecker.check_and_setup_environment(
                log_func=log_func,
                progress_callback=lambda p: root.after(0, lambda v=p: update_status(status_var.get(), v))
            )
            
            if success:
                update_status("环境就绪，正在启动主程序...", 100)
                time.sleep(0.5)
                root.destroy()
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
                retry_btn = tk.Button(root, text="重试", command=lambda: threading.Thread(target=init_thread, daemon=True).start())
                retry_btn.pack(pady=10)
        except Exception as e:
            log_to_file(f"初始化线程异常: {e}")
            import traceback
            log_to_file(traceback.format_exc())
            update_status(f"初始化异常: {e}", 0)
    
    root = tk.Tk()
    root.title(f"DOTA2翻译小助手 v{VERSION} - 启动器")
    
    window_width = 600
    window_height = 400
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    
    title_label = tk.Label(root, text="DOTA2翻译小助手", font=("Microsoft YaHei", 20, "bold"))
    title_label.pack(pady=20)
    
    status_var = tk.StringVar(value="检查环境中...")
    status_label = tk.Label(root, textvariable=status_var, font=("Microsoft YaHei", 12))
    status_label.pack(pady=10)
    
    progress = ttk.Progressbar(root, mode='determinate', length=500)
    progress.pack(pady=20)
    
    log_text = scrolledtext.ScrolledText(root, height=10, width=70)
    log_text.pack(pady=10)
    
    threading.Thread(target=init_thread, daemon=True).start()
    
    root.mainloop()
    
    log_to_file("启动器窗口关闭，准备启动主程序...")
    run_main_program()
    
    if _main_process is not None:
        log_to_file("等待主程序结束...")
        _main_process.wait()
        log_to_file("主程序已结束")
    
    log_to_file("=" * 50)
    log_to_file("启动器退出")
    log_to_file("=" * 50)

if __name__ == "__main__":
    main()
