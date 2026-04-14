# -*- coding: utf-8 -*-
"""
Dota 2 中文→英文翻译器 - GUI版本
功能：现代化界面 + 系统托盘 + 自定义触发键 + 严格模式 + 实时翻译
版本：1.2.0
"""

VERSION = "2.0.0"

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import keyboard
import pyperclip
import pyautogui
import time
import threading
import requests
import re
import hashlib
import json
import os
import sys
import tempfile
import webbrowser
from PIL import Image, ImageDraw, ImageTk
import ctypes

try:
    from src.词汇表 import ZH_TO_EN, EN_TO_ZH
except ImportError:
    from 词汇表 import ZH_TO_EN, EN_TO_ZH

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class Config:
    DEFAULT_CONFIG = {
        "trigger_key": "f6",
        "toggle_hotkey": "ctrl+alt+t",
        "cooldown": 0.2,
        "source_lang": "zh-CN",
        "target_lang": "en",
        "strict_mode_enabled": False,
        "strict_mode_position": "",
        "realtime_enabled": False,
        "realtime_hotkey": "f7",
        "capture_region": {"x": 718, "y": 732, "width": 611, "height": 25},
        "danmaku_position": {"x": -200, "y": 300},
        "show_region_border": False,
        "realtime_settings": {
            "interval": 3.0,
            "display_duration": 5.0,
            "max_messages": 5,
            "font_size": 16,
            "original_color": "#FFFFFF",
            "translated_color": "#00FF00",
            "bg_alpha": 0.5
        }
    }

    CONFIG_FILE = "config.json"

    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except:
                pass

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value

    @property
    def trigger_key(self) -> str:
        return self.get('trigger_key', 'f6')

    @property
    def realtime_hotkey(self) -> str:
        return self.get('realtime_hotkey', 'f7')

class StrictModeWindow:
    WS_EX_NOACTIVATE = 0x08000000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TRANSPARENT = 0x00000020
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, on_translate_callback, config):
        self.on_translate_callback = on_translate_callback
        self.config = config
        self.window = None
        self.entry = None
        self.is_visible = False
        self.hwnd = None
        self._create_window()

    def _create_window(self):
        self.window = tk.Toplevel()
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)
        self.window.configure(bg='#1a1a1a')

        saved_pos = self.on_translate_callback("__get_position__")
        if saved_pos and ',' in saved_pos:
            try:
                x, y = saved_pos.split(',')
                self.window.geometry(f'320x45+{x}+{y}')
            except:
                saved_pos = None

        if not saved_pos or ',' not in str(saved_pos):
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width - 320) // 2
            y = (screen_height - 45) // 2
            self.window.geometry(f'320x45+{x}+{y}')

        self.drag_bar = tk.Label(
            self.window,
            text='═══',
            bg='#4d4d4d',
            fg='#888888',
            font=('Consolas', 6),
            cursor='fleur'
        )
        self.drag_bar.pack(fill=tk.X, padx=1, pady=(1,0))
        self.drag_bar.bind('<Button-1>', self._on_drag_start)
        self.drag_bar.bind('<B1-Motion>', self._on_drag_motion)

        self.entry = tk.Entry(
            self.window,
            font=('Microsoft YaHei UI', 11),
            bg='#2d2d2d',
            fg='#ffffff',
            insertbackground='white',
            relief=tk.FLAT,
            bd=5
        )
        self.entry.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.entry.bind('<Return>', self._on_enter)
        self.entry.bind('<Escape>', self._on_escape)

        self.window.bind('<FocusOut>', self._on_focus_out)
        self.window.withdraw()

    def _on_drag_start(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def _on_drag_motion(self, event):
        deltax = event.x - self.drag_x
        deltay = event.y - self.drag_y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f'+{x}+{y}')

    def _save_position(self):
        geom = self.window.geometry()
        pos = geom.split('+')[1] if '+' in geom else ''
        if pos:
            self.on_translate_callback(f"__save_position__{pos}")
            self.config.save_config()

    def _set_window_flags(self):
        if self.hwnd:
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(self.hwnd, -20)
            ex_style |= self.WS_EX_TOPMOST | self.WS_EX_NOACTIVATE
            user32.SetWindowLongW(self.hwnd, -20, ex_style)
            user32.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW)
            self.window.update()
            self.window.lift()
            self.window.attributes('-topmost', True)

    def _force_topmost(self):
        user32 = ctypes.windll.user32
        if not self.hwnd:
            self.hwnd = user32.GetParent(self.window.winfo_id())
        if self.hwnd:
            user32.SetWindowPos(
                self.hwnd, -1,
                0, 0, 0, 0,
                self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_SHOWWINDOW
            )
            ex_style = user32.GetWindowLongW(self.hwnd, -20)
            ex_style |= self.WS_EX_TOPMOST
            user32.SetWindowLongW(self.hwnd, -20, ex_style)

    def show(self):
        if self.window:
            if not self.is_visible:
                self.window.deiconify()
                self.window.attributes('-topmost', True)
                self.window.lift()
                self._force_topmost()
                self.window.update()
                self.is_visible = True
                self.window.after(10, self._focus_entry)

    def _focus_entry(self):
        if self.is_visible and self.entry:
            self.entry.focus_set()
            self.entry.focus_force()

    def _attach_to_dota2(self):
        user32 = ctypes.windll.user32
        dota_hwnd = user32.FindWindowW(None, "Dota 2")
        if dota_hwnd:
            self._set_window_flags()
        else:
            self._set_window_flags()

    def hide(self):
        if self.window:
            self.window.withdraw()
            self.entry.delete(0, tk.END)
            self.is_visible = False

    def toggle(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def _on_enter(self, event):
        text = self.entry.get().strip()
        if text:
            result = self.on_translate_callback(text)
            if result:
                pyperclip.copy(result)
            self.entry.delete(0, tk.END)
            self.hide()

    def _on_escape(self, event):
        self.hide()

    def _on_focus_out(self, event):
        pass

class RegionSelector:
    def __init__(self, callback):
        self.callback = callback
        self.selection_window = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None

    def start_selection(self):
        self.selection_window = tk.Toplevel()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.3)
        self.selection_window.configure(bg='black')
        self.selection_window.bind('<Button-1>', self.on_mouse_down)
        self.selection_window.bind('<B1-Motion>', self.on_mouse_move)
        self.selection_window.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.selection_window.bind('<Escape>', lambda e: self.cancel_selection())

        self.canvas = tk.Canvas(self.selection_window, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.label = tk.Label(
            self.selection_window,
            text="拖动鼠标框选聊天区域，按 ESC 取消",
            bg='black',
            fg='white',
            font=('Microsoft YaHei UI', 14)
        )
        self.label.place(relx=0.5, rely=0.1, anchor=tk.CENTER)

    def on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_mouse_move(self, event):
        if self.start_x is not None:
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y,
                event.x, event.y,
                outline='red', width=3
            )

    def on_mouse_up(self, event):
        if self.start_x is not None:
            x1, y1 = self.start_x, self.start_y
            x2, y2 = event.x, event.y

            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            if width > 20 and height > 10:
                self.callback({"x": int(x), "y": int(y), "width": int(width), "height": int(height)})
            else:
                self.callback(None)

            self.selection_window.destroy()

    def cancel_selection(self):
        if self.selection_window:
            self.selection_window.destroy()
        self.callback(None)

class DanmakuWindow:
    def __init__(self, config, on_position_save, root=None):
        self.config = config
        self.on_position_save = on_position_save
        self.root = root
        self.window = None
        self.messages = []
        self.max_messages = config.get('realtime_settings', {}).get('max_messages', 5)
        self.display_duration = 15.0  # 显示15秒
        self.is_visible = False
        self.hwnd = None
        self._create_window()

    def _create_window(self):
        self.window = tk.Toplevel()
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-transparentcolor', 'black')  # 黑色透明
        self.window.configure(bg='black')  # 窗口背景黑色（会被透明化）

        saved_pos = self.on_position_save("__get_danmaku_position__")
        danmaku_width = 375  # 宽度变大1/2
        if saved_pos and ',' in saved_pos:
            try:
                x, y = saved_pos.split(',')
                x, y = int(x), int(y)
                screen_width = self.window.winfo_screenwidth()
                if x < 0:
                    x = screen_width + x - danmaku_width
                self.window.geometry(f'{danmaku_width}x300+{x}+{y}')
            except:
                screen_width = self.window.winfo_screenwidth()
                self.window.geometry(f'{danmaku_width}x300+{screen_width - danmaku_width - 20}+300')
        else:
            screen_width = self.window.winfo_screenwidth()
            self.window.geometry(f'{danmaku_width}x300+{screen_width - danmaku_width - 20}+300')

        self.canvas = tk.Canvas(
            self.window,
            bg='black',  # canvas 背景黑色（会被透明化）
            highlightthickness=0,
            width=danmaku_width,
            height=300
        )
        self.canvas.pack()
        self.canvas.tag_bind('message', '<Button-1>', lambda e: None)

        self.drag_bar = tk.Label(
            self.window,
            text='≡',
            bg='#4d4d4d',
            fg='#888888',
            font=('Consolas', 10),
            cursor='fleur'
        )
        self.drag_bar.place(x=0, y=0, width=danmaku_width, height=15)
        self.drag_bar.bind('<Button-1>', self._on_drag_start)
        self.drag_bar.bind('<B1-Motion>', self._on_drag_motion)

        self.window.withdraw()

    def _on_drag_start(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def _on_drag_motion(self, event):
        deltax = event.x - self.drag_x
        deltay = event.y - self.drag_y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f'+{x}+{y}')

    def _save_position(self):
        geom = self.window.geometry()
        pos = geom.split('+')[1] if '+' in geom else ''
        if pos:
            self.on_position_save(f"__save_danmaku_position__{pos}")

    def show(self):
        if self.window:
            self.window.deiconify()
            self.is_visible = True

    def hide(self):
        if self.window:
            self.window.withdraw()
            self.is_visible = False

    def add_message(self, original: str, translated: str):
        if not self.is_visible:
            return

        # 检查是否已经存在相同的消息
        display_text = f"{original} → {translated}"
        for msg in self.messages:
            if self.canvas.itemcget(msg['text'], 'text') == display_text:
                return  # 已存在相同消息，跳过

        settings = self.config.get('realtime_settings', {})
        font_size = settings.get('font_size', 16)
        text_color = settings.get('original_color', '#FFFFFF')
        
        danmaku_width = 375  # 弹幕宽度
        max_width = danmaku_width - 20  # 最大宽度

        msg_id = len(self.messages)
        
        # 最多只显示2条弹幕
        # 有新弹幕时，立刻删除最老的一条
        while len(self.messages) >= 2:
            self._remove_oldest()
        
        # 计算文本高度（自动换行）
        line_height = font_size + 4
        
        # 估算行数
        total_chars = len(original) + len(translated) + 3  # +3 for " → "
        chars_per_line = max_width // (font_size - 2)
        estimated_lines = max(1, (total_chars + chars_per_line - 1) // chars_per_line)
        text_height = estimated_lines * line_height + 10

        # 基于上一条消息的实际高度计算位置
        if len(self.messages) == 0:
            y_base = 20
        else:
            # 从最后一条消息获取高度
            last_msg = self.messages[-1]
            y_base = last_msg.get('y_offset', 20) + last_msg.get('height', 35) + 5  # 5像素间隔

        if y_base + text_height > 280:
            self._remove_oldest()
            # 重新计算位置
            if len(self.messages) == 0:
                y_base = 20
            else:
                last_msg = self.messages[-1]
                y_base = last_msg.get('y_offset', 20) + last_msg.get('height', 35) + 5

        # 灰色背景，最大透明度（更淡）
        bg_color = '#808080'

        # 不显示背景，只显示文字
        
        # 显示格式: 原文 → 翻译（支持自动换行）
        display_text = f"{original} → {translated}"
        
        msg_text = self.canvas.create_text(
            10, y_base + text_height // 2,
            text=display_text,
            fill=text_color,
            font=('Microsoft YaHei UI', font_size - 2),
            anchor=tk.W,
            width=max_width,  # 启用自动换行
            tags='message'
        )

        self.messages.append({
            'id': msg_id,
            'text': msg_text,
            'time': time.time(),
            'height': text_height,
            'y_offset': y_base
        })

        # 启动30秒后自动删除
        threading.Thread(target=self._auto_remove, args=(msg_id,), daemon=True).start()

    def _auto_remove(self, msg_id):
        time.sleep(self.display_duration)
        if self.root:
            self.root.after(0, lambda: self._try_remove_by_id(msg_id))
        else:
            self._try_remove_by_id(msg_id)

    def _try_remove(self, msg_id):
        for i, msg in enumerate(self.messages):
            if i == msg_id:
                self.canvas.delete(msg['text'])
                self.messages[i] = None
                break
        self.messages = [m for m in self.messages if m is not None]

    def _try_remove_by_id(self, msg_id):
        for i, msg in enumerate(self.messages):
            if msg.get('id') == msg_id:
                self.canvas.delete(msg['text'])
                self.messages[i] = None
                break
        self.messages = [m for m in self.messages if m is not None]

    def _remove_oldest(self):
        if self.messages:
            msg = self.messages.pop(0)
            self.canvas.delete(msg['text'])
            # 重新排列剩余消息的位置（使用实际高度）
            y_offset = 20
            for m in self.messages:
                msg_height = m.get('height', 35)
                self.canvas.coords(m['text'], 10, y_offset + msg_height // 2)
                m['y_offset'] = y_offset
                y_offset += msg_height + 5  # 消息之间留5像素间隔

class RealtimeTranslator:
    def __init__(self, config, engine, on_new_message, log_callback):
        self.config = config
        self.engine = engine
        self.on_new_message = on_new_message
        self.log = log_callback
        self.running = False
        self.thread = None
        self.last_text = ""
        self.last_img_hash = None  # 上次截图的hash
        self.ocr_available = False
        self.ocr = None
        self.en_to_zh_engine = TranslationEngine(mode=2)
        # 识别结果缓存（最近10条）
        self.text_cache = []
        self.max_cache_size = 10

    def _clear_cache(self):
        """清空识别结果缓存"""
        self.text_cache = []
        self.last_img_hash = None
        self.last_text = ""
        self.log("[缓存] 已清空")

    def _ensure_ocr_loaded(self):
        if self.ocr is not None:
            return True
        try:
            from paddleocr import PaddleOCR
            import os

            paddleocr_dir = os.path.expanduser("~/.paddleocr")
            model_ready = os.path.exists(os.path.join(paddleocr_dir, "en_PP-OCRv3_det_infer")) or \
                         os.path.exists(os.path.join(paddleocr_dir, "en_PP-OCRv3_rec_infer")) or \
                         os.path.exists(os.path.join(paddleocr_dir, "ocr_v2.0_en_det")) or \
                         os.path.exists(os.path.join(paddleocr_dir, "ocr_v2_en_det")) or \
                         os.path.exists(os.path.join(paddleocr_dir, "det"))

            if not model_ready:
                self.log("未检测到OCR模型，即将下载...")
                self.log("下载模型大约需要30MB，请耐心等待...")
                import urllib.request
                import tarfile

                try:
                    det_url = "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_det_infer.tar"
                    tar_path = os.path.join(tempfile.gettempdir(), "en_PP-OCRv3_det.tar")
                    self.log("下载检测模型...")
                    urllib.request.urlretrieve(det_url, tar_path)
                    extract_dir = paddleocr_dir
                    with tarfile.open(tar_path, 'r') as tar:
                        tar.extractall(extract_dir)
                    os.remove(tar_path)

                    rec_url = "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_rec_infer.tar"
                    rec_tar_path = os.path.join(tempfile.gettempdir(), "en_PP-OCRv3_rec.tar")
                    self.log("下载识别模型...")
                    urllib.request.urlretrieve(rec_url, rec_tar_path)
                    with tarfile.open(rec_tar_path, 'r') as tar:
                        tar.extractall(extract_dir)
                    os.remove(rec_tar_path)

                    cls_url = "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar"
                    cls_tar_path = os.path.join(tempfile.gettempdir(), "angle_cls.tar")
                    self.log("下载方向分类模型...")
                    urllib.request.urlretrieve(cls_url, cls_tar_path)
                    with tarfile.open(cls_tar_path, 'r') as tar:
                        tar.extractall(extract_dir)
                    os.remove(cls_tar_path)

                    self.log("OCR模型下载完成！")
                except Exception as download_error:
                    self.log(f"模型下载失败: {download_error}")
                    self.log("请检查网络连接后重试，或手动下载模型到 ~/.paddleocr 目录")
                    self.ocr_available = False
                    self._ocr_error = str(download_error)
                    return False

            self.log("正在加载OCR模型...")

            self.ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='en',
                use_angle_cls=True,
                show_log=False
            )
            self.ocr_available = True
            self.log("OCR模型加载成功")
            return True
        except Exception as e:
            self.ocr_available = False
            self._ocr_error = str(e)
            self.log(f"OCR加载失败: {e}")
            return False

    def _preprocess_image(self, img_np):
        """图像预处理：提取白色文字、放大、形态学处理"""
        import cv2
        import numpy as np
        
        # 转换为BGR格式（OpenCV默认格式）
        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            # RGBA -> BGR
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif len(img_np.shape) == 3 and img_np.shape[2] == 3:
            # RGB -> BGR
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_np
        
        # 提取白色文字（HSV色彩空间）
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        # 白色的HSV范围
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # 形态学处理：膨胀连接断裂字母
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # 放大2倍
        mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return mask

    def _check_text_duplicate(self, text):
        """检查文本是否重复"""
        text_lower = text.lower().strip()
        if text_lower == self.last_text:
            return True, text
        self.last_text = text_lower
        return False, text

    def on_realtime_message(self, original: str, translated: str):
        # 检查翻译结果是否与上一条相同
        if hasattr(self, '_last_translated') and self._last_translated == translated:
            return
        self._last_translated = translated
        self.log(f"实时翻译: {original[:20]}... → {translated[:20]}...")
        self.danmaku_window.add_message(original, translated)

    def start(self):
        if self.running:
            return
        if not self._ensure_ocr_loaded():
            if hasattr(self, '_ocr_error'):
                self.log(f"OCR错误: {self._ocr_error}")
            else:
                self.log("OCR不可用，无法开启实时翻译")
            return
        # 启动时清空缓存
        self._clear_cache()
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.log("实时翻译已开启")

    def stop(self):
        self.running = False
        self.log("实时翻译已关闭")

    def _monitor_loop(self):
        import mss
        import numpy as np
        
        sct = mss.mss()
        
        while self.running:
            try:
                region = self.config.get('capture_region', {})
                if not region or region.get('width', 0) == 0:
                    self.log("[监控] 等待设置识别区域...")
                    time.sleep(1)
                    continue
                
                x = region.get('x', 0)
                y = region.get('y', 0)
                w = region.get('width', 100)
                h = region.get('height', 50)
                
                img = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
                img_np = np.array(img)
                
                # 计算截图hash
                import hashlib
                img_hash = hashlib.md5(img_np.tobytes()).hexdigest()
                
                # 检查截图是否变化
                if img_hash == self.last_img_hash:
                    time.sleep(1.0)
                    continue
                
                self.last_img_hash = img_hash
                
                try:
                    result = self.ocr.ocr(img_np, cls=True)
                    
                    texts = []
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) >= 2:
                                text = line[1][0]
                                if text:
                                    texts.append(text)
                    
                    current_text = ' '.join(texts).strip()
                    
                    # 文字去重：图片变了但文字和之前翻译过的一样，跳过
                    if current_text and current_text == self.last_text:
                        time.sleep(1.0)
                        continue
                    
                    if current_text:
                        has_english = any('a' <= c.lower() <= 'z' for c in current_text)
                        
                        if has_english:
                            # 获取邮箱配置
                            email = self.config.get('email', '')
                            translated = self.en_to_zh_engine.translate(current_text, email if email else None)
                            
                            # 无论翻译成功还是失败都显示
                            self.last_text = current_text
                            if translated and translated != current_text:
                                self.log(f"[翻译] {current_text} → {translated}")
                                self.on_new_message(current_text, translated)
                            else:
                                # 翻译失败，显示原文
                                self.log(f"[翻译] {current_text} → (失败) {current_text}")
                                self.on_new_message(current_text, f"(失败) {current_text}")
                except Exception as e:
                    self.log(f"[监控] OCR处理异常: {e}")
                
                interval = 1.0  # 固定为1秒
                time.sleep(interval)
                
            except Exception as e:
                self.log(f"[监控] 异常: {e}")
                time.sleep(1)

class TranslationEngine:
    def __init__(self, mode=1):
        self.cache = {}
        self.session = requests.Session()
        self.mode = mode
        if mode == 1:
            self.terms = ZH_TO_EN
        else:
            self.terms = EN_TO_ZH
        self._sorted_terms = sorted(self.terms.keys(), key=len, reverse=True)

    def replace_chinese_terms(self, text: str) -> tuple:
        return text, {}

    def restore_placeholders(self, text: str, placeholders: dict) -> str:
        return text

    def restore_dota_terms(self, text: str) -> str:
        text = re.sub(r'\beye\b', 'ward', text, flags=re.IGNORECASE)
        text = re.sub(r'\beyes\b', 'ward', text, flags=re.IGNORECASE)
        text = re.sub(r'\bfog\b', 'smoke', text, flags=re.IGNORECASE)
        return text

    def apply_dota_terms_zh(self, translated: str, original: str) -> str:
        """英译中后处理：将英文术语替换为中文"""
        try:
            from 词汇表 import EN_TO_ZH

            # 合并原文和翻译结果，确保所有词都被处理
            combined_text = f"{original} {translated}".lower()

            # 使用EN_TO_ZH词汇表替换（按长度从长到短，避免短词先替换）
            for en_term, cn_term in sorted(EN_TO_ZH.items(), key=lambda x: len(x[0]), reverse=True):
                if en_term in combined_text:
                    translated = re.sub(r'\b' + re.escape(en_term) + r'\b', cn_term, translated, flags=re.IGNORECASE)
                    # 同时也在原文中替换（用于后面检查）
                    original = re.sub(r'\b' + re.escape(en_term) + r'\b', cn_term, original, flags=re.IGNORECASE)


        except Exception as e:
            pass

        return translated

    def translate(self, text: str, email: str = None) -> str:
        if not text.strip():
            return text

        if self.mode == 1:
            has_chinese = re.search(r'[\u4e00-\u9fff]', text) is not None
            if not has_chinese:
                return text
            source_lang, target_lang = 'zh-CN', 'en'
        else:
            has_english = re.search(r'[a-zA-Z]', text) is not None
            if not has_english:
                return text
            source_lang, target_lang = 'en', 'zh-CN'

        cache_key = hashlib.md5(f"{self.mode}:{text}".encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 先检查词汇表是否有直接匹配
        if self.mode == 2:  # 英译中模式
            text_lower = text.lower().strip()
            if text_lower in self.terms:
                direct_translation = self.terms[text_lower]
                self.cache[cache_key] = direct_translation
                return direct_translation

        text_with_placeholders, placeholders = self.replace_chinese_terms(text)

        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': text_with_placeholders, 'langpair': f'{source_lang}|{target_lang}'}
            # 如果提供了邮箱，添加到请求参数中
            if email:
                params['de'] = email
            resp = self.session.get(url, params=params, timeout=10)
            result = resp.json()

            if result.get('responseStatus') == 200:
                # 从matches中选择最佳翻译（优先选择完整翻译且非原文的）
                matches = result.get('matches', [])
                best_translation = None

                for match in matches:
                    translation = match.get('translation', '')
                    segment = match.get('segment', '')
                    # 只选择segment与原文相同的完整翻译
                    if translation and segment.lower() == text_with_placeholders.lower():
                        if translation.lower() != text_with_placeholders.lower():
                            best_translation = translation
                            break

                # 如果没有找到合适的翻译，使用responseData中的翻译
                if not best_translation:
                    best_translation = result['responseData']['translatedText']

                # 检查翻译是否完整（对于英译中，检查是否包含中文；对于中译英，检查是否有有效翻译）
                if best_translation:
                    if self.mode == 2:  # 英译中
                        has_chinese = re.search(r'[\u4e00-\u9fff]', best_translation) is not None
                        too_short = len(best_translation) < len(text) * 0.5
                        if too_short or not has_chinese:
                            translated = text
                        else:
                            translated = best_translation
                    else:  # 中译英
                        if len(best_translation) < 1:
                            translated = text
                        else:
                            translated = best_translation
                else:
                    translated = text

                # 无论API返回什么，都进行词汇表后处理
                translated = self.restore_placeholders(translated, placeholders)
                if self.mode == 1:
                    translated = self.restore_dota_terms(translated)
                else:
                    # 英译中：术语词典后处理
                    translated = self.apply_dota_terms_zh(translated, text)

                # 如果翻译结果与原文相同，尝试词汇表替换
                if translated.lower() == text.lower().strip():
                    text_lower = text.lower().strip()
                    if text_lower in self.terms:
                        translated = self.terms[text_lower]

                self.cache[cache_key] = translated
                return translated
            else:
                pass  # API错误静默处理
        except Exception as e:
            pass

        return text

class Dota2TranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"DOTA2翻译小助手 v{VERSION}")
        self.root.geometry("600x550")
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
        self.strict_mode_window = StrictModeWindow(self.strict_mode_translate, self.config)
        self.strict_mode_enabled = self.config.get('strict_mode_enabled', False)

        self.region_selector = None
        self.danmaku_window = DanmakuWindow(self.config, self.handle_danmaku_position, self.root)
        self.realtime_enabled = False
        self.preview_rect = None

        self._create_widgets()
        
        # 同步严格模式状态到UI
        if self.strict_mode_enabled:
            self.mode_toggle_btn.config(text="非严格")
            self.mode_status_var.set("严格")
        else:
            self.mode_toggle_btn.config(text="严格")
            self.mode_status_var.set("非严格")
        
        # 初始化邮箱状态显示
        self._update_email_status()
        
        self.realtime_translator = RealtimeTranslator(
            self.config,
            self.realtime_engine,
            self.on_realtime_message,
            self.log
        )
        
        # 预加载 OCR 模型（后台运行）
        self.log("正在预加载 OCR 模型...")
        threading.Thread(target=self._preload_ocr, daemon=True).start()
        
        self._start_keyboard_listener()
    
    def _preload_ocr(self):
        """后台预加载 OCR 模型"""
        success = self.realtime_translator._ensure_ocr_loaded()
        if success:
            self.root.after(0, lambda: self.log("OCR 模型预加载完成"))
        else:
            self.root.after(0, lambda: self.log("OCR 模型预加载失败"))
    
    def _update_email_status(self):
        """更新邮箱状态显示"""
        email = self.config.get('email', '')
        if email:
            self.email_status_var.set("已设置")
            self.email_status_display_var.set("已设置")
        else:
            self.email_status_var.set("未设置")
            self.email_status_display_var.set("未设置")

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="🎮 DOTA2翻译小助手",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0,10))

        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="5")
        status_frame.pack(fill=tk.X, pady=(0,5))
        
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
        ttk.Label(status_row, text="MyMemory", foreground='#9b59b6', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(status_row, text="| 邮箱:").pack(side=tk.LEFT, padx=5)
        self.email_status_display_var = tk.StringVar(value="未设置")
        ttk.Label(status_row, textvariable=self.email_status_display_var, foreground='#95a5a6', font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)

        input_translate_frame = ttk.LabelFrame(main_frame, text="输入翻译", padding="10")
        input_translate_frame.pack(fill=tk.X, pady=5)
        
        it_row1 = ttk.Frame(input_translate_frame)
        it_row1.pack(fill=tk.X, pady=2)
        ttk.Label(it_row1, text="模式:").pack(side=tk.LEFT, padx=5)
        self.mode_toggle_btn = ttk.Button(it_row1, text="严格", command=self.toggle_strict_mode, width=10)
        self.mode_toggle_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(it_row1, text="功能快捷键:").pack(side=tk.LEFT, padx=15)
        self.trigger_key_var = tk.StringVar(value="F6")
        ttk.Button(it_row1, textvariable=self.trigger_key_var, command=self.start_set_key, width=6).pack(side=tk.LEFT, padx=5)

        realtime_frame = ttk.LabelFrame(main_frame, text="实时翻译", padding="10")
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

        # 测试栏已隐藏
        # test_frame = ttk.LabelFrame(main_frame, text="测试", padding="10")
        # test_frame.pack(fill=tk.X, pady=5)
        
        # test_row = ttk.Frame(test_frame)
        # test_row.pack(fill=tk.X)
        # self.test_input = ttk.Entry(test_row, width=30)
        # self.test_input.pack(side=tk.LEFT, padx=5)
        # self.test_input.insert(0, "帮我买个眼")
        # ttk.Button(test_row, text="翻译", command=self.test_translation, width=8).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(footer_frame, text="GitHub: ", foreground='gray', font=('Microsoft YaHei UI', 8)).pack(side=tk.LEFT, padx=5)
        github_link = ttk.Label(footer_frame, text="https://github.com/dyygs/Dota2_Translator_GUI", foreground='#3498db', cursor='hand2', font=('Microsoft YaHei UI', 8, 'underline'))
        github_link.pack(side=tk.LEFT)
        github_link.bind('<Button-1>', lambda e: webbrowser.open('https://github.com/dyygs/Dota2_Translator_GUI'))
        
        ttk.Label(footer_frame, text=" | ", foreground='gray').pack(side=tk.LEFT)
        
        coffee_link = ttk.Label(footer_frame, text="觉得好用？请开发者喝杯咖啡", foreground='#e67e22', cursor='hand2', font=('Microsoft YaHei UI', 8))
        coffee_link.pack(side=tk.LEFT)
        coffee_link.bind('<Button-1>', lambda e: self._show_donate_qrcode())

        
        saved_region = self.config.get('capture_region', {})
        if saved_region and saved_region.get('width', 0) > 0:
            self.region_var.set(f"{saved_region['width']}x{saved_region['height']} at ({saved_region['x']}, {saved_region['y']})")

    def toggle_mode(self):
        self.log("模式切换功能测试中...")
        # 暂时禁用模式切换
        # self.mode = 2 if self.mode == 1 else 1
        # self.engine = TranslationEngine(mode=self.mode)
        # if self.mode == 1:
        #     self.mode_var.set("模式: 中→英")
        #     self.log("已切换到模式1: 中文→英文")
        # else:
        #     self.mode_var.set("模式: 英→中")
        #     self.log("已切换到模式2: 英文→中文")

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
            # F7 快捷键处理在内部完成，不需要额外日志
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

    def strict_mode_translate(self, text: str) -> str:
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

    def test_translation(self):
        test_text = self.test_input.get().strip()
        if not test_text:
            self.log("请输入要翻译的中文")
            return
        result = self.engine.translate(test_text)
        self.log(f"翻译: {test_text} → {result}")

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
        self.log(f"on_region_selected被调用: {region}")
        if region:
            self.config.set('capture_region', region)
            self.config.save_config()
            self.region_var.set(f"{region['width']}x{region['height']}")
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

    def save_config(self):
        self.config.save_config()
        self.log("配置已保存")
        messagebox.showinfo("保存成功", "配置已保存到 config.json")

    def _toggle_email(self):
        """切换邮箱状态：根据按钮文字决定操作"""
        btn_text = self.email_btn_var.get()
        
        if btn_text == "保存":
            # 保存邮箱
            email = self.email_var.get().strip()
            if email:
                self.config.set('email', email)
                self.config.save_config()
                self.email_btn_var.set("清除")
                self.email_status_var.set("已设置")
                self.email_status_display_var.set("已设置")
                self.log(f"邮箱已保存: {email}")
                messagebox.showinfo("保存成功", f"邮箱已保存: {email}\n每日可翻译 50000 字符")
            else:
                messagebox.showwarning("提示", "请输入邮箱地址")
        else:
            # 清除邮箱
            self.config.set('email', '')
            self.config.save_config()
            self.email_var.set('')
            self.email_btn_var.set("保存")
            self.email_status_var.set("未设置")
            self.email_status_display_var.set("未设置")
            self.log("邮箱已清除")
            messagebox.showinfo("已清除", "邮箱已清除\n使用免费版（每日 5000 字符）")

    def _toggle_show_border(self):
        """切换显示识别区域边框"""
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
        """显示捐赠二维码"""
        qrcode_path = get_resource_path('1.png')
        
        if os.path.exists(qrcode_path):
            qrcode_window = tk.Toplevel(self.root)
            qrcode_window.title("请开发者喝杯咖啡")
            
            img = Image.open(qrcode_path)
            w, h = img.size
            max_w, max_h = 280, 350
            ratio = min(max_w / w, max_h / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h))
            photo = ImageTk.PhotoImage(img)
            
            qrcode_window.geometry(f"{new_w + 20}x{new_h + 40}")
            
            label = tk.Label(qrcode_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            
            ttk.Label(qrcode_window, text="感谢您的支持！", font=('Microsoft YaHei UI', 10)).pack(pady=5)
        else:
            messagebox.showinfo("提示", "二维码图片不存在")

    def _start_keyboard_listener(self):
        keyboard.hook(self.on_key_pressed)
        keyboard.add_hotkey('ctrl+alt+t', self.toggle_translation)

    def toggle_translation(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.status_var.set("已启动 | 翻译功能: 已启用")
            self.status_label.config(foreground='green')
            self.log("翻译功能已启用")
        else:
            self.status_var.set("已禁用 | 翻译功能: 已禁用")
            self.status_label.config(foreground='red')
            self.log("翻译功能已禁用")

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

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

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Dota2TranslatorGUI()
    app.run()