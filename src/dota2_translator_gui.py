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


def check_environment_background(app):
    """后台检查环境（与原版完全一致）"""
    import threading
    import urllib.request
    import zipfile
    import subprocess

    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runtime_dir = os.path.join(app_root, "runtime")
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
            except:
                pass

    def check_python():
        """检查Python运行时"""
        log("检查Python运行时...")
        python_path = os.path.join(runtime_dir, "python.exe")
        if not os.path.exists(python_path):
            log("Python运行时不存在，需要下载")
            return False
        try:
            result = subprocess.run([python_path, "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                log(f"Python运行时正常: {result.stdout.strip()}")
                return True
        except Exception as e:
            log(f"Python运行时检查失败: {e}")
            return False
        return False

    def check_pip():
        """检查pip"""
        log("检查pip...")
        pip_path = os.path.join(runtime_dir, "Scripts", "pip.exe")
        if not os.path.exists(pip_path):
            log("pip不存在")
            return False
        log("pip已安装")
        return True

    def check_deps():
        """检查依赖包"""
        log("检查依赖包...")
        deps_to_check = ["paddleocr", "numpy", "PIL", "cv2"]
        missing = []
        for dep in deps_to_check:
            try:
                __import__(dep)
                log(f"  {dep}: OK")
            except:
                log(f"  {dep}: 缺失")
                missing.append(dep)
        return missing

    def download_python():
        """下载Python嵌入版"""
        log("开始下载Python嵌入版...")
        python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        zip_path = os.path.join(runtime_dir, "python.zip")
        try:
            def reporthook(block_num, block_size, total):
                if total > 0:
                    percent = min(100, int((block_num * block_size * 100) / total))
                    if block_num % 50 == 0:
                        log(f"  下载进度: {percent}%")
            urllib.request.urlretrieve(python_url, zip_path, reporthook)
            log("解压Python...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(runtime_dir)
            os.remove(zip_path)
            log("Python下载完成")
            return True
        except Exception as e:
            log(f"下载Python失败: {e}")
            return False

    def install_pip():
        """安装pip"""
        log("开始安装pip...")
        try:
            pip_url = "https://bootstrap.pypa.io/get-pip.py"
            pip_path = os.path.join(runtime_dir, "get-pip.py")
            urllib.request.urlretrieve(pip_url, pip_path)
            result = subprocess.run(
                [os.path.join(runtime_dir, "python.exe"), pip_path],
                capture_output=True, timeout=300
            )
            os.remove(pip_path)
            log("pip安装完成")
            return True
        except Exception as e:
            log(f"安装pip失败: {e}")
            return False

    def install_deps():
        """安装依赖（固定版本）"""
        deps = [
            ("numpy", "numpy==2.4.4"),
            ("opencv-python", "opencv-python==4.6.0.66"),
            ("pillow", "pillow==10.4.0"),
            ("paddlepaddle", "paddlepaddle==2.6.2"),
            ("paddleocr", "paddleocr==2.10.0"),
            ("keyboard", "keyboard==0.13.5"),
            ("pyperclip", "pyperclip==1.8.2"),
            ("pyautogui", "pyautogui==0.9.54"),
            ("requests", "requests==2.33.1"),
            ("mss", "mss==10.1.0"),
            ("pygetwindow", "pygetwindow==0.0.9"),
            ("pytweening", "pytweening==1.2.0"),
        ]
        pip_exe = os.path.join(runtime_dir, "Scripts", "pip.exe")
        for i, (name, pkg) in enumerate(deps):
            version = pkg.split("==")[1] if "==" in pkg else pkg
            log(f"安装 {name}=={version}...")
            try:
                result = subprocess.run(
                    [pip_exe, "install", pkg, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "--no-cache-dir"],
                    capture_output=True, timeout=600
                )
                if result.returncode == 0:
                    log(f"  {name} 安装成功")
                else:
                    log(f"  {name} 安装失败")
            except Exception as e:
                log(f"  {name} 安装异常: {e}")

    def run_check():
        """执行检查"""
        log("=" * 30)
        log("开始环境检查...")
        log("=" * 30)
        if not check_python():
            log("准备下载Python...")
            if not download_python():
                log("无法下载Python，初始化失败")
                return
        if not check_pip():
            log("准备安装pip...")
            if not install_pip():
                log("无法安装pip，初始化失败")
                return
        missing = check_deps()
        if missing:
            log(f"缺少依赖: {', '.join(missing)}")
            log("开始安装依赖...")
            install_deps()
            missing = check_deps()
            if missing:
                log(f"以下依赖仍缺失: {', '.join(missing)}")
            else:
                log("所有依赖安装完成!")
                with open(init_file, 'w') as f:
                    f.write("init_done")
        else:
            log("所有依赖已安装!")
            with open(init_file, 'w') as f:
                f.write("init_done")
        log("环境检查完成!")

    threading.Thread(target=run_check, daemon=True).start()


def main():
    app = Dota2TranslatorGUI()

    # 后台环境检查（与原版一致）
    threading.Thread(target=check_environment_background, args=(app,), daemon=True).start()

    app.root.mainloop()


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
