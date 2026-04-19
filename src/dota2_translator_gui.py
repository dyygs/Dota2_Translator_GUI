# -*- coding: utf-8 -*-
"""
Dota 2 中文→英文翻译器 - GUI版本 (模块化重构版)
功能：现代化界面 + 系统托盘 + 自定义触发键 + 严格模式 + 实时翻译
版本：3.0.1 (UI对齐原版)
"""

import os
import sys
import io
import base64
import time
import threading
import webbrowser
import re

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import keyboard
import pyperclip
import pyautogui
from PIL import Image, ImageTk

from src.core.version import VERSION

# ============================================================
# 导入模块化组件（直接导入，无兼容层）
# ============================================================

# 核心工具
from src.core.config import Config

# 翻译系统
from src.translator.dota2_translation_system import Dota2TranslationSystem
from src.translator.engine import TranslationEngine
from src.translator.input_translator import InputTranslator
from src.translator.realtime_translator import RealtimeTranslator
from src.translator.danmaku import StrictModeWindow, DanmakuWindow

# GUI组件
from src.gui.region_selector import RegionSelector

# 外部服务
from src.services.qrcode_data import QRCODE_BASE64
from src.services.update_checker import check_update_multi_source, download_update, perform_update


def get_resource_path(relative_path):
    """获取资源路径"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_qrcode_path():
    """获取二维码图片路径"""
    if getattr(sys, 'frozen', False):
        paths_to_try = [
            os.path.join(sys._MEIPASS, 'src', '1.png'),
            os.path.join(sys._MEIPASS, '1.png'),
            os.path.join(os.path.dirname(sys.executable), 'src', '1.png'),
            os.path.join(os.path.dirname(sys.executable), '1.png'),
        ]
        for p in paths_to_try:
            if os.path.exists(p):
                return p
        return paths_to_try[0]
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.png')


class Dota2TranslatorGUI:
    """Dota2翻译器主窗口 - 模块化版（UI对齐原版）"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"DOTA2翻译小助手 v{VERSION}")
        
        window_width = 600
        window_height = 650
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)

        self.config = Config()
        self.mode = 1
        self.engine = TranslationEngine(mode=1)
        self.realtime_engine = TranslationEngine(mode=2)
        self.enabled = True
        self.is_translating = False
        self.last_time = 0
        self.is_setting_key = False
        self.is_setting_realtime_key = False

        self.tray_icon = None
        self.is_minimized = False
        self.strict_mode_window = StrictModeWindow(self._strict_mode_translate, self.config)
        self.strict_mode_enabled = self.config.get('strict_mode_enabled', True)

        self.region_selector = None
        self.danmaku_window = DanmakuWindow(self.config, self.handle_danmaku_position, self.root)
        self.realtime_enabled = False
        self.preview_rect = None

        self._create_widgets()
        
        if self.strict_mode_enabled:
            self.mode_toggle_btn.config(text="非严格")
            self.mode_status_var.set("严格")
        else:
            self.mode_toggle_btn.config(text="严格")
            self.mode_status_var.set("非严格")
        
        self._update_email_status()
        
        self.realtime_translator = RealtimeTranslator(
            self.config,
            self.engine,
            self.realtime_engine,
            self.on_realtime_message,
            self.log
        )
        
        self.log("正在预加载 OCR 模型...")
        threading.Thread(target=self._preload_ocr, daemon=True).start()
        
        self._start_keyboard_listener()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 先创建底部栏，确保始终可见
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        ttk.Label(footer_frame, text="GitHub: ", foreground='gray', font=('Microsoft YaHei UI', 8)).pack(side=tk.LEFT, padx=5)
        github_link = ttk.Label(footer_frame, text="https://github.com/dyygs/Dota2_Translator_GUI", foreground='#3498db', cursor='hand2', font=('Microsoft YaHei UI', 8, 'underline'))
        github_link.pack(side=tk.LEFT)
        github_link.bind('<Button-1>', lambda e: webbrowser.open('https://github.com/dyygs/Dota2_Translator_GUI'))

        ttk.Label(footer_frame, text=" | ", foreground='gray').pack(side=tk.LEFT)

        coffee_link = ttk.Label(footer_frame, text="觉得好用？请开发者喝杯咖啡", foreground='#e67e22', cursor='hand2', font=('Microsoft YaHei UI', 8))
        coffee_link.pack(side=tk.LEFT)
        coffee_link.bind('<Button-1>', lambda e: self._show_donate_qrcode())

        # 内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            content_frame,
            text="🎮 DOTA2翻译小助手",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # 状态栏（与原版一致：程序 | 模式 | 实时 | 翻译库 | 邮箱）
        status_frame = ttk.LabelFrame(content_frame, text="状态", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 5))

        status_row = ttk.Frame(status_frame)
        status_row.pack(fill=tk.X)

        ttk.Label(status_row, text="程序:").pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(value="已启动")
        ttk.Label(status_row, textvariable=self.status_var, foreground='green', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        ttk.Label(status_row, text="| 模式:").pack(side=tk.LEFT, padx=5)
        self.mode_status_var = tk.StringVar()
        ttk.Label(status_row, textvariable=self.mode_status_var, foreground='#3498db', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        ttk.Label(status_row, text="| 实时:").pack(side=tk.LEFT, padx=5)
        self.realtime_status_var = tk.StringVar(value="关闭")
        ttk.Label(status_row, textvariable=self.realtime_status_var, foreground='#95a5a6', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        ttk.Label(status_row, text="| 翻译库:").pack(side=tk.LEFT, padx=5)
        ttk.Label(status_row, text="DeepLX", foreground='#9b59b6', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        ttk.Label(status_row, text="| 邮箱:").pack(side=tk.LEFT, padx=5)
        self.email_status_display_var = tk.StringVar(value="未设置")
        ttk.Label(status_row, textvariable=self.email_status_display_var, foreground='#95a5a6', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        # 输入翻译区（与原版一致）
        input_translate_frame = ttk.LabelFrame(content_frame, text="输入翻译", padding="10")
        input_translate_frame.pack(fill=tk.X, pady=5)

        it_row1 = ttk.Frame(input_translate_frame)
        it_row1.pack(fill=tk.X, pady=2)
        ttk.Label(it_row1, text="模式:").pack(side=tk.LEFT, padx=5)
        self.mode_toggle_btn = ttk.Button(it_row1, text="严格", command=self.toggle_strict_mode, width=10)
        self.mode_toggle_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(it_row1, text="功能快捷键:").pack(side=tk.LEFT, padx=15)
        self.trigger_key_var = tk.StringVar(value="F6")
        ttk.Button(it_row1, textvariable=self.trigger_key_var, command=self.start_set_key, width=6).pack(side=tk.LEFT, padx=5)

        # 实时翻译区（与原版一致：3行布局）
        realtime_frame = ttk.LabelFrame(content_frame, text="实时翻译", padding="10")
        realtime_frame.pack(fill=tk.X, pady=5)

        rt_row1 = ttk.Frame(realtime_frame)
        rt_row1.pack(fill=tk.X, pady=2)
        ttk.Label(rt_row1, text="开关快捷键:").pack(side=tk.LEFT, padx=5)
        self.realtime_key_var = tk.StringVar(value="F7")
        ttk.Button(rt_row1, textvariable=self.realtime_key_var, command=self.start_set_realtime_key, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(rt_row1, text="区域:").pack(side=tk.LEFT, padx=15)
        self.region_btn = ttk.Button(rt_row1, text="设置区域", command=self.start_region_selection, width=10)
        self.region_btn.pack(side=tk.LEFT, padx=5)
        self.region_var = tk.StringVar(value="未设置")
        ttk.Label(rt_row1, textvariable=self.region_var, foreground='gray', font=('Microsoft YaHei UI', 8)).pack(side=tk.LEFT, padx=5)

        rt_row2 = ttk.Frame(realtime_frame)
        rt_row2.pack(fill=tk.X, pady=2)
        ttk.Label(rt_row2, text="邮箱(可选):").pack(side=tk.LEFT, padx=5)
        self.email_var = tk.StringVar(value=self.config.get('email', ''))
        self.email_entry = ttk.Entry(rt_row2, textvariable=self.email_var, width=20)
        self.email_entry.pack(side=tk.LEFT, padx=5)
        self.email_btn_var = tk.StringVar(value="保存" if not self.config.get('email') else "清除")
        ttk.Button(rt_row2, textvariable=self.email_btn_var, command=self._toggle_email, width=6).pack(side=tk.LEFT, padx=5)
        self.email_status_var = tk.StringVar(value="未设置" if not self.config.get('email') else "已设置")
        ttk.Label(rt_row2, textvariable=self.email_status_var, foreground='gray', font=('Microsoft YaHei UI', 8)).pack(side=tk.LEFT, padx=5)

        rt_row3 = ttk.Frame(realtime_frame)
        rt_row3.pack(fill=tk.X, pady=2)
        self.show_border_var = tk.BooleanVar(value=self.config.get('show_region_border', False))
        ttk.Checkbutton(rt_row3, text="显示识别区域绿色虚线框", variable=self.show_border_var, command=self._toggle_show_border).pack(side=tk.LEFT, padx=5)

        # 日志区（与原版一致：Consolas字体、正常状态、带时间戳）
        log_frame = ttk.LabelFrame(content_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 同步严格模式状态到UI
        if self.strict_mode_enabled:
            self.mode_toggle_btn.config(text="非严格")
            self.mode_status_var.set("严格")
        else:
            self.mode_toggle_btn.config(text="严格")
            self.mode_status_var.set("非严格")

        # 初始化邮箱状态显示
        self._update_email_status()

        saved_region = self.config.get('capture_region', {})
        if saved_region and saved_region.get('width', 0) > 0:
            self.region_var.set(f"{saved_region['width']}x{saved_region['height']} at ({saved_region['x']}, {saved_region['y']})")

        self.log("UI初始化完成")

    def _update_email_status(self):
        """更新邮箱状态显示"""
        email = self.config.get('email', '')
        if email:
            self.email_status_var.set("已设置")
            self.email_status_display_var.set("已设置")
        else:
            self.email_status_var.set("未设置")
            self.email_status_display_var.set("未设置")

    def log(self, message: str):
        """添加日志（与原版格式一致：[HH:MM:SS] message）"""
        timestamp = time.strftime("%H:%M:%S")
        try:
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
        except:
            pass

    def toggle_strict_mode(self):
        self.strict_mode_enabled = not self.strict_mode_enabled
        if self.strict_mode_enabled:
            self.mode_toggle_btn.config(text="非严格")
            self.mode_status_var.set("严格")
            self.log("严格模式已启用 | 按F6呼出悬浮窗")
            self.config.set('strict_mode_enabled', True)
        else:
            self.mode_toggle_btn.config(text="严格")
            self.mode_status_var.set("非严格")
            self.strict_mode_window.hide()
            self.log("严格模式已禁用 | F6翻译发送")
            self.config.set('strict_mode_enabled', False)

    def start_set_key(self):
        self.is_setting_key = True
        self.log("请按下功能快捷键...")

    def start_set_realtime_key(self):
        self.is_setting_realtime_key = True
        self.log("请按下开关快捷键...")

    def _handle_key_setting(self, event):
        key_name = event.name.lower()
        valid_keys = [
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'space', 'enter', 'tab'
        ]
        if key_name in valid_keys:
            self.config.set('trigger_key', key_name)
            key_display = key_name.upper() if len(key_name) == 1 else key_name
            self.trigger_key_var.set(key_display)
            self.log(f"功能快捷键已设置为: {key_display}")
            self.is_setting_key = False

    def on_key_pressed(self, event):
        if self.is_setting_key:
            if event.event_type == 'down':
                self._handle_key_setting(event)
            return

        if self.is_setting_realtime_key:
            if event.event_type == 'down':
                key_name = event.name.lower()
                valid_keys = [
                    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
                    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                    'space', 'enter', 'tab'
                ]
                if key_name in valid_keys:
                    self.config.set('realtime_hotkey', key_name)
                    key_display = key_name.upper() if len(key_name) == 1 else key_name
                    self.realtime_key_var.set(key_display)
                    self.log(f"开关快捷键已设置为: {key_display}")
                    self.is_setting_realtime_key = False
            return

        if event.name.lower() == self.config.trigger_key.lower():
            if event.event_type != 'up':
                return
            if self.enabled and not self.is_translating:
                current_time = time.time()
                cooldown = self.config.get('cooldown', 0.2)
                if current_time - self.last_time > cooldown:
                    self.last_time = current_time
                    if self.strict_mode_enabled:
                        self.root.after(0, self.toggle_strict_mode_window)
                    else:
                        threading.Thread(target=self.do_translate, daemon=True).start()

        if event.name.lower() == self.config.get('realtime_hotkey', 'f7').lower():
            if event.event_type != 'up':
                return
            self.root.after(0, self.toggle_realtime_translation)

    def do_translate(self):
        try:
            self.is_translating = True
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.03)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.03)

            text = pyperclip.paste()

            if text and re.search(r'[\u4e00-\u9fff]', text):
                translated = self.engine.translate(text)

                if translated and translated != text:
                    pyperclip.copy(translated)
                    time.sleep(0.02)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.02)
                    pyautogui.press('enter')

        except Exception as e:
            self.log(f"错误: {e}")
        finally:
            self.is_translating = False

    def _strict_mode_translate(self, text: str) -> str:
        if text == "__get_position__":
            return self.config.get('strict_mode_position', '')
        if text.startswith("__save_position__"):
            pos = text.replace("__save_position__", "")
            self.config.set('strict_mode_position', pos)
            return ""
        if not text.strip():
            return ""

        result = self.engine.translate(text)
        self.log(f"严格模式翻译: {text} → {result}")
        return result

    def toggle_strict_mode_window(self):
        self.strict_mode_window.toggle()

    def toggle_realtime_translation(self):
        self.realtime_enabled = not self.realtime_enabled
        self.log(f"实时翻译切换: {self.realtime_enabled}")
        if self.realtime_enabled:
            self.danmaku_window.show()
            if self.config.get('show_region_border', False):
                self.show_region_preview()
            self.realtime_translator.start()
            if self.realtime_translator.running:
                self.realtime_status_var.set("开启")
            else:
                self.realtime_enabled = False
                self.danmaku_window.hide()
                self.hide_region_preview()
        else:
            self.danmaku_window.hide()
            self.realtime_translator.stop()
            self.hide_region_preview()
            self.realtime_status_var.set("关闭")
            self.log("实时翻译已关闭")

    def start_region_selection(self):
        self.region_selector = RegionSelector(self.on_region_selected)
        self.region_selector.start_selection()
        self.log("请框选聊天区域...")

    def on_region_selected(self, region):
        if region:
            self.config.set('capture_region', region)
            self.config.save_config()
            self.region_var.set(f"{region['width']}x{region['height']} at ({region['x']}, {region['y']})")
            self.log(f"识别区域已设置: {region['width']}x{region['height']} at ({region['x']}, {region['y']})")
        else:
            self.log("区域设置取消")

    def show_region_preview(self):
        region = self.config.get('capture_region', {})
        if not region or region.get('width', 0) == 0:
            self.log("请先设置识别区域")
            return
        if not hasattr(self, 'preview_window') or not self.preview_window:
            self.preview_window = tk.Toplevel()
            self.preview_window.overrideredirect(True)
            self.preview_window.attributes('-topmost', True)
            self.preview_window.attributes('-transparentcolor', 'black')
            self.preview_window.configure(bg='black')

            self.preview_canvas = tk.Canvas(self.preview_window, bg='black', highlightthickness=0)
            self.preview_canvas.pack(fill=tk.BOTH, expand=True)

            x = region.get('x', 0)
            y = region.get('y', 0)
            w = region.get('width', 100)
            h = region.get('height', 50)
            self.preview_canvas.create_rectangle(2, 2, w-2, h-2, outline='#00FF00', width=2, dash=(5, 3))
        else:
            x = region.get('x', 0)
            y = region.get('y', 0)
            w = region.get('width', 100)
            h = region.get('height', 50)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_rectangle(2, 2, w-2, h-2, outline='#00FF00', width=2, dash=(5, 3))

        self.preview_window.geometry(f'{w}x{h}+{x}+{y}')
        self.preview_window.deiconify()

    def hide_region_preview(self):
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.withdraw()

    def handle_danmaku_position(self, text: str) -> str:
        if text == "__get_danmaku_position__":
            pos = self.config.get('danmaku_position', '')
            if isinstance(pos, dict):
                return f"{pos.get('x', 0)},{pos.get('y', 0)}"
            return pos
        if text.startswith("__save_danmaku_position__"):
            pos = text.replace("__save_danmaku_position__", "")
            self.config.set('danmaku_position', pos)
            self.config.save_config()
            return ""
        return ""

    def on_realtime_message(self, original: str, translated: str):
        self.log(f"实时翻译: {original[:20]}... → {translated[:20]}...")
        self.danmaku_window.add_message(original, translated)

    def _toggle_email(self):
        btn_text = self.email_btn_var.get()

        if btn_text == "保存":
            email = self.email_var.get().strip()
            if not email:
                messagebox.showwarning("提示", "请输入邮箱地址")
                return
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messagebox.showwarning("格式错误", "请输入有效的邮箱地址\n例如: example@domain.com")
                return
            
            self.config.set('email', email)
            self.config.save_config()
            self.email_btn_var.set("清除")
            self.email_status_var.set("已设置")
            self.email_status_display_var.set("已设置")
            self.log(f"邮箱已保存: {email}")
            messagebox.showinfo("保存成功", f"邮箱已保存: {email}\n每日可翻译 50000 字符")
        else:
            self.config.set('email', '')
            self.config.save_config()
            self.email_var.set('')
            self.email_btn_var.set("保存")
            self.email_status_var.set("未设置")
            self.email_status_display_var.set("未设置")
            self.log("邮箱已清除")
            messagebox.showinfo("已清除", "邮箱已清除\n使用免费版（每日 5000 字符）")

    def _toggle_show_border(self):
        show = self.show_border_var.get()
        self.config.set('show_region_border', show)
        self.config.save_config()

        if show:
            self.log("已开启显示识别区域绿色虚线框")
            self.show_region_preview()
        else:
            self.log("已关闭显示识别区域绿色虚线框")
            self.hide_region_preview()

    def _show_donate_qrcode(self):
        try:
            img_data = io.BytesIO(base64.b64decode(QRCODE_BASE64))
            qrcode_window = tk.Toplevel(self.root)
            qrcode_window.title("请开发者喝杯咖啡")

            img = Image.open(img_data)
            w, h = img.size
            max_w, max_h = 280, 350
            ratio = min(max_w / w, max_h / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h))
            photo = ImageTk.PhotoImage(img)

            window_w, window_h = new_w + 20, new_h + 40
            screen_w = qrcode_window.winfo_screenwidth()
            screen_h = qrcode_window.winfo_screenheight()
            x = (screen_w - window_w) // 2
            y = (screen_h - window_h) // 2
            qrcode_window.geometry(f"{window_w}x{window_h}+{x}+{y}")

            label = tk.Label(qrcode_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)

            ttk.Label(qrcode_window, text="感谢您的支持！", font=('Microsoft YaHei UI', 10)).pack(pady=5)
        except Exception as e:
            messagebox.showinfo("提示", f"二维码加载失败: {e}")

    def _preload_ocr(self):
        success = self.realtime_translator._ensure_ocr_loaded()
        if success:
            self.root.after(0, lambda: self.log("OCR 模型预加载完成"))
        else:
            self.root.after(0, lambda: self.log("OCR 模型预加载失败"))

    def _start_keyboard_listener(self):
        keyboard.hook(self.on_key_pressed)
        keyboard.add_hotkey('ctrl+alt+t', self.toggle_translation)

    def toggle_translation(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.status_var.set("已启动 | 翻译功能: 已启用")
            self.log("翻译功能已启用")
        else:
            self.status_var.set("已禁用 | 翻译功能: 已禁用")
            self.log("翻译功能已禁用")

    def _on_closing(self):
        self.quit_app()

    def quit_app(self):
        try:
            keyboard.unhook_all()
        except:
            pass
        if self.realtime_translator:
            self.realtime_translator.stop()
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    def check_for_update(self):
        """后台检查更新"""
        def do_check():
            print(f"[更新检查] 开始检查更新，当前版本: {VERSION}")
            config = {
                'github_owner': 'dyygs',
                'github_repo': 'Dota2_Translator_GUI',
            }
            result = check_update_multi_source(config, VERSION)
            
            print(f"[更新检查] 结果: has_update={result.get('has_update')}, "
                  f"latest_version={result.get('latest_version')}, "
                  f"download_url={result.get('download_url')}, "
                  f"error={result.get('error')}")
            
            if result.get('has_update') and result.get('download_url'):
                print("[更新检查] 发现更新，准备显示对话框")
                self.root.after(0, lambda: self.show_update_dialog(result))
            else:
                print("[更新检查] 无更新或检查失败")
        
        threading.Thread(target=do_check, daemon=True).start()

    def show_update_dialog(self, update_info):
        """显示更新提示对话框"""
        print(f"[更新检查] show_update_dialog 被调用，update_info: {update_info}")
        
        latest_version = update_info.get('latest_version', 'unknown')
        release_notes = update_info.get('release_notes', '暂无更新说明')
        download_url = update_info.get('download_url', '')
        force_update = update_info.get('force_update', False)
        sha256 = update_info.get('sha256', '')
        
        print(f"[更新检查] latest_version={latest_version}, download_url={download_url}, force_update={force_update}")
        
        dialog = tk.Toplevel(self.root)
        dialog.title("发现新版本" if not force_update else "必须更新")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes('-topmost', True)
        dialog.focus_force()
        
        if force_update:
            dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        title_text = f"发现新版本 {latest_version}" if not force_update else f"必须更新到 {latest_version}"
        ttk.Label(frame, text=title_text, font=('Microsoft YaHei', 14, 'bold')).pack(pady=(0, 10))
        ttk.Label(frame, text=f"当前版本: {VERSION}", font=('Microsoft YaHei', 10)).pack()
        
        if force_update:
            ttk.Label(frame, text="此版本包含重要更新，必须更新后才能继续使用", 
                     font=('Microsoft YaHei', 9), foreground='red').pack(pady=(5, 0))
        
        notes_frame = ttk.LabelFrame(frame, text="更新内容", padding="10")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        notes_text = scrolledtext.ScrolledText(notes_frame, height=5, width=45, font=('Microsoft YaHei', 9))
        notes_text.pack(fill=tk.BOTH, expand=True)
        notes_text.insert(tk.END, release_notes[:500] if release_notes else "暂无更新说明")
        notes_text.config(state=tk.DISABLED)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        
        def on_update():
            print(f"[更新检查] 点击了立即更新按钮")
            dialog.destroy()
            self.start_download(download_url, latest_version, sha256, force_update)
        
        def on_ignore():
            print(f"[更新检查] 点击了忽略按钮")
            dialog.destroy()
        
        update_btn = ttk.Button(btn_frame, text="立即更新", command=on_update, width=15)
        update_btn.pack(side=tk.LEFT, padx=15)
        
        if not force_update:
            ignore_btn = ttk.Button(btn_frame, text="忽略", command=on_ignore, width=15)
            ignore_btn.pack(side=tk.LEFT, padx=15)
        
        dialog.update_idletasks()
        
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 350) // 2
        dialog.geometry(f"450x350+{x}+{y}")
        
        dialog.deiconify()
        dialog.lift()
        dialog.update()
        
        print(f"[更新检查] 对话框已创建，按钮已添加，force_update={force_update}")

    def start_download(self, download_url, version, sha256='', force_update=False):
        """开始下载更新"""
        if getattr(sys, 'frozen', False):
            download_dir = os.path.dirname(sys.executable)
        else:
            download_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except Exception:
                download_dir = os.path.expanduser("~\\Downloads")
        
        new_exe_name = f"Dota2Translator_v{version}.exe"
        new_exe_path = os.path.join(download_dir, new_exe_name)
        
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("下载更新")
        progress_dialog.geometry("400x200")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        progress_dialog.attributes('-topmost', True)
        
        progress_dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        progress_dialog.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(progress_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"正在下载 {new_exe_name}...", font=('Microsoft YaHei', 10)).pack(pady=(0, 10))
        
        progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100, length=350)
        progress_bar.pack(pady=5)
        
        status_label = ttk.Label(frame, text="正在连接服务器...", font=('Microsoft YaHei', 9))
        status_label.pack(pady=5)
        
        url_label = ttk.Label(frame, text="准备连接...", font=('Microsoft YaHei', 8), foreground='gray')
        url_label.pack(pady=2)
        
        download_result = {'success': False, 'error': None, 'verified': False}
        
        def safe_update(text, progress=None, url=None):
            def do_update():
                try:
                    status_label.config(text=text)
                    if progress is not None:
                        progress_var.set(progress)
                    if url:
                        url_label.config(text=url[:60] + "...")
                    progress_dialog.update_idletasks()
                    progress_dialog.update()
                except Exception as e:
                    with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                        f.write(f"[UI更新错误] {e}\n")
            try:
                self.root.after(0, do_update)
            except Exception as e:
                with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                    f.write(f"[after错误] {e}\n")
        
        def progress_callback(downloaded, total, current_url=None):
            try:
                percent = (downloaded / total) * 100 if total > 0 else 0
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                url_text = current_url[:50] + "..." if current_url else None
                safe_update(f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB ({percent:.0f}%)", percent, url_text)
            except Exception as e:
                with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                    f.write(f"[进度回调错误] {e}\n")
        
        def do_download():
            try:
                safe_update("正在连接下载服务器...", 0)
                with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                    f.write(f"[下载] 开始下载: {download_url}\n")
                    f.write(f"[下载] 保存到: {new_exe_path}\n")
                
                result = download_update(download_url, new_exe_path, progress_callback, sha256)
                
                download_result['success'] = result.get('success', False)
                download_result['verified'] = result.get('verified', False)
                download_result['error'] = result.get('error')
                
                with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                    f.write(f"[下载] 结果: success={download_result['success']}, error={download_result['error']}\n")
                
            except Exception as e:
                download_result['success'] = False
                download_result['error'] = str(e)
                with open(os.path.join(PythonInstaller.get_data_dir(), "download.log"), "a", encoding="utf-8") as f:
                    f.write(f"[下载] 异常: {e}\n")
                print(f"[下载] 异常: {e}")
            
            self.root.after(0, lambda: on_download_complete(progress_dialog, download_result, new_exe_path, version, force_update))
        
        threading.Thread(target=do_download, daemon=True).start()

    def on_download_complete(self, dialog, result, new_exe_path, version, force_update=False):
        """下载完成处理"""
        dialog.destroy()
        
        if result['success'] and result.get('verified', True):
            if force_update:
                confirm = True
            else:
                confirm = messagebox.askyesno(
                    "下载完成",
                    f"新版本已下载到:\n{new_exe_path}\n\n是否立即更新？\n（程序将自动关闭并更新）",
                    parent=self.root
                )
            
            if confirm:
                current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
                perform_update(new_exe_path, current_exe, restart=True)
                self.root.after(500, self.quit_app)
            else:
                messagebox.showinfo("提示", f"新版本已保存到:\n{new_exe_path}\n\n您可以稍后手动更新。", parent=self.root)
        else:
            error_msg = result.get('error', '未知错误')
            if not result.get('verified', True):
                error_msg = "文件校验失败，可能文件已损坏"
            
            if force_update:
                retry = messagebox.askyesno(
                    "下载失败",
                    f"{error_msg}\n\n是否重试？\n选择\"否\"将打开下载页面手动下载。",
                    parent=self.root
                )
            else:
                retry = messagebox.askyesno(
                    "下载失败",
                    f"下载失败: {error_msg}\n\n是否重试？\n选择\"否\"将打开下载页面。",
                    parent=self.root
                )
            
            if retry:
                config = {
                    'github_owner': 'dyygs',
                    'github_repo': 'Dota2_Translator_GUI',
                }
                update_info = check_update_multi_source(config, VERSION)
                if update_info.get('download_url'):
                    self.start_download(
                        update_info['download_url'], 
                        update_info.get('latest_version', VERSION),
                        update_info.get('sha256', ''),
                        force_update
                    )
            else:
                webbrowser.open("https://github.com/dyygs/Dota2_Translator_GUI/releases/latest")


def check_environment_background(app):
    """后台检查环境"""
    import threading
    import subprocess

    from src.environment.python_installer import PythonInstaller
    from src.environment.dependency_manager import DependencyManager
    
    python_dir = PythonInstaller.get_python_dir()
    app_root = PythonInstaller.get_app_dir()
    init_file = os.path.join(app_root, "init_done.txt")

    log_text = None
    for widget in app.root.winfo_children():
        if isinstance(widget, scrolledtext.ScrolledText):
            log_text = widget
            break

    def log(msg):
        print(f"[环境检查] {msg}")
        if log_text:
            try:
                log_text.insert(tk.END, f"[环境检查] {msg}\n")
                log_text.see(tk.END)
                app.root.update()
            except Exception:
                pass

    def check_python():
        """检查Python"""
        log("检查Python...")
        python_path = PythonInstaller.find_system_python()
        if python_path:
            try:
                result = subprocess.run([python_path, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    log(f"Python正常: {result.stdout.strip()} ({python_path})")
                    return True
            except Exception as e:
                log(f"Python检查失败: {e}")
                return False
        log("Python未安装")
        return False

    def check_pip():
        """检查pip"""
        log("检查pip...")
        if DependencyManager.check_pip_module():
            log("pip已安装")
            return True
        log("pip未安装")
        return False

    def check_deps():
        """检查依赖包"""
        log("检查依赖包...")
        deps_to_check = ["paddleocr", "numpy", "PIL", "cv2"]
        missing = []
        for dep in deps_to_check:
            if DependencyManager.check_dependency_installed(dep):
                log(f"  {dep}: OK")
            else:
                log(f"  {dep}: 缺失")
                missing.append(dep)
        return missing

    def run_check():
        """执行检查"""
        log("=" * 30)
        log("开始环境检查...")
        log(f"应用目录: {app_root}")
        log(f"Python目录: {python_dir}")
        log("=" * 30)
        
        if not check_python():
            log("Python未安装，请运行launcher.exe安装Python")
            return
        
        if not check_pip():
            log("pip未安装，正在安装...")
            if not DependencyManager.install_pip(log):
                log("pip安装失败")
                return
        
        missing = check_deps()
        if missing:
            log(f"缺少依赖: {', '.join(missing)}")
            log("开始安装依赖...")
            success, skipped, installed = DependencyManager.check_and_install_dependencies(log_func=log)
            if success:
                log(f"依赖安装完成: {skipped}个已存在, {installed}个新安装")
                with open(init_file, 'w') as f:
                    f.write("init_done")
            else:
                log("依赖安装失败，请运行launcher.exe")
        else:
            log("所有依赖已安装!")
            with open(init_file, 'w') as f:
                f.write("init_done")
        log("环境检查完成!")

    threading.Thread(target=run_check, daemon=True).start()


def main():
    import traceback
    
    def log_error(msg):
        """写入错误日志"""
        try:
            log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main_error.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except:
            pass
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """全局异常处理"""
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_error(f"未捕获的异常:\n{error_msg}")
        print(f"[ERROR] {error_msg}")
        
        try:
            messagebox.showerror(
                "程序错误",
                f"程序发生错误:\n{str(exc_value)}\n\n详细信息已记录到 main_error.log"
            )
        except:
            pass
    
    sys.excepthook = handle_exception
    
    try:
        app = Dota2TranslatorGUI()

        # 后台环境检查（与原版一致）
        threading.Thread(target=check_environment_background, args=(app,), daemon=True).start()
        
        # 启动时检查更新（后台静默）
        app.root.after(2000, app.check_for_update)

        app.root.mainloop()
    except Exception as e:
        error_msg = traceback.format_exc()
        log_error(f"主程序崩溃:\n{error_msg}")
        try:
            messagebox.showerror(
                "程序崩溃",
                f"程序发生严重错误:\n{str(e)}\n\n详细信息已记录到 main_error.log"
            )
        except:
            pass


if __name__ == "__main__":
    # 单实例检测 - 防止崩溃后无限重启（与原版完全一致）
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "Dota2Translator.lock")

    if os.path.exists(lock_file):
        import time
        try:
            with open(lock_file, 'r') as f:
                old_pid = int(f.read().strip())
            import subprocess
            result = subprocess.run(['tasklist', '/FI', f'PID eq {old_pid}'], capture_output=True, text=True)
            if str(old_pid) not in result.stdout:
                try:
                    os.remove(lock_file)
                except:
                    pass
            else:
                print(f"[警告] 程序已在运行 (PID: {old_pid})，请勿重复启动")
                input("按回车键退出...")
                sys.exit(1)
        except Exception as e:
            print(f"[警告] 锁文件异常: {e}")

    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
    except:
        pass

    main()
