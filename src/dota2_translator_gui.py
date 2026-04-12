# -*- coding: utf-8 -*-
"""
Dota 2 中文→英文翻译器 - GUI版本
功能：现代化界面 + 系统托盘 + 自定义触发键 + 严格模式
版本：1.1.1
"""

VERSION = "1.1.1"

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
from PIL import Image, ImageDraw
import ctypes


class Config:
    DEFAULT_CONFIG = {
        "trigger_key": "f6",
        "toggle_hotkey": "ctrl+alt+t",
        "cooldown": 0.2,
        "source_lang": "zh-CN",
        "target_lang": "en",
        "strict_mode_enabled": False,
        "strict_mode_position": ""
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


try:
    from src.词汇表 import ZH_TO_EN, EN_TO_ZH
except ModuleNotFoundError:
    from 词汇表 import ZH_TO_EN, EN_TO_ZH


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
            x = screen_width - 340
            y = screen_height - 80
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
        replaced = text
        placeholders = {}
        counter = 0
        for cn in self._sorted_terms:
            if cn in replaced:
                en = self.terms[cn]
                placeholder = f' XPH{counter}X '
                placeholders[placeholder.strip()] = en
                replaced = replaced.replace(cn, placeholder)
                counter += 1
        return replaced.strip(), placeholders

    def restore_placeholders(self, text: str, placeholders: dict) -> str:
        for placeholder, en in placeholders.items():
            text = text.replace(placeholder, en)
            text = re.sub(r'XPH\s*(\d+)\s*X', lambda m: placeholders.get(f'XPH{m.group(1)}X', en), text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def restore_dota_terms(self, text: str) -> str:
        text = re.sub(r'\beye\b', 'ward', text, flags=re.IGNORECASE)
        text = re.sub(r'\beyes\b', 'ward', text, flags=re.IGNORECASE)
        text = re.sub(r'\bfog\b', 'smoke', text, flags=re.IGNORECASE)
        return text

    def translate(self, text: str) -> str:
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

        text_with_placeholders, placeholders = self.replace_chinese_terms(text)

        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': text_with_placeholders, 'langpair': f'{source_lang}|{target_lang}'}
            resp = self.session.get(url, params=params, timeout=5)
            result = resp.json()

            if result.get('responseStatus') == 200:
                translated = result['responseData']['translatedText']
                if translated and translated != text:
                    translated = self.restore_placeholders(translated, placeholders)
                    if self.mode == 1:
                        translated = self.restore_dota_terms(translated)
                    self.cache[cache_key] = translated
                    return translated
        except:
            pass

        return text


class Dota2TranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Dota 2 中文翻译器 v{VERSION}")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        self.config = Config()
        self.mode = 1
        self.engine = TranslationEngine(mode=1)
        self.enabled = True
        self.is_translating = False
        self.last_time = 0
        self.is_setting_key = False

        self.tray_icon = None
        self.is_minimized = False
        self.strict_mode_window = StrictModeWindow(self.strict_mode_translate, self.config)
        self.strict_mode_enabled = True

        self._create_widgets()
        self._start_keyboard_listener()
        self._create_tray_icon()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="🎮 Dota 2 中文→英文翻译器",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))

        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="● 已启动")
        self.mode_label = tk.StringVar(value="模式: 严格")
        row_status = ttk.Frame(status_frame)
        row_status.pack(fill=tk.X)
        ttk.Label(row_status, text="状态:", font=('', 9, 'bold')).pack(side=tk.LEFT)
        self.status_label = ttk.Label(row_status, textvariable=self.status_var, foreground='green')
        self.status_label.pack(side=tk.LEFT, padx=20)
        ttk.Label(row_status, text="模式:", font=('', 9, 'bold')).pack(side=tk.LEFT)
        self.mode_status_label = ttk.Label(row_status, textvariable=self.mode_label, foreground='blue')
        self.mode_status_label.pack(side=tk.LEFT, padx=5)

        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.pack(fill=tk.X, pady=5)

        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="模式:").pack(side=tk.LEFT, padx=(0,5))
        self.strict_mode_btn = ttk.Button(row1, text="严格", command=self.toggle_strict_mode, width=10)
        self.strict_mode_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="(F6: 非严格翻译发送 | 严格呼出悬浮窗)").pack(side=tk.LEFT, padx=10)

        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="快捷键:").pack(side=tk.LEFT, padx=(0,5))
        self.trigger_key_var = tk.StringVar(value="F6")
        ttk.Button(row2, textvariable=self.trigger_key_var, command=self.start_set_key, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="←点击设置", foreground='gray').pack(side=tk.LEFT, padx=5)
        self.toggle_btn = ttk.Button(row2, text="禁用", command=self.toggle_translation, width=8)
        self.toggle_btn.pack(side=tk.LEFT, padx=20)

        row3 = ttk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=3)
        ttk.Label(row3, text="测试:").pack(side=tk.LEFT, padx=(0,5))
        self.test_input = ttk.Entry(row3, width=25)
        self.test_input.pack(side=tk.LEFT, padx=5)
        self.test_input.insert(0, "帮我买个眼")
        ttk.Button(row3, text="翻译", command=self.test_translation, width=8).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.bottom_status = tk.StringVar(value="就绪 | 按 Ctrl+Alt+T 切换开关")
        ttk.Label(
            main_frame,
            textvariable=self.bottom_status,
            relief=tk.SUNKEN
        ).pack(fill=tk.X, pady=(5, 0))

        self.log("系统启动成功")
        self.log(f"触发键: {self.config.trigger_key.upper()}")
        self.log("等待Dota2聊天框输入...")

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.bottom_status.set(message)

    def toggle_translation(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.status_var.set("● 已启动 | 翻译功能: 已启用")
            self.status_label.config(foreground='green')
            self.log("翻译功能已启用")
        else:
            self.status_var.set("● 已禁用 | 翻译功能: 已禁用")
            self.status_label.config(foreground='red')
            self.log("翻译功能已禁用")

    def toggle_strict_mode(self):
        self.strict_mode_enabled = not self.strict_mode_enabled
        if self.strict_mode_enabled:
            self.strict_mode_btn.config(text="严格")
            self.mode_label.set("模式: 严格")
            self.strict_mode_window.show()
            self.log("严格模式已启用 | F6呼出悬浮窗")
            self.config.set('strict_mode_enabled', True)
        else:
            self.strict_mode_btn.config(text="非严格")
            self.mode_label.set("模式: 非严格")
            self.strict_mode_window.hide()
            self.log("严格模式已禁用 | F6翻译发送")
            self.config.set('strict_mode_enabled', False)

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
        if self.strict_mode_enabled:
            self.strict_mode_window.toggle()

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

    def start_set_key(self):
        self.is_setting_key = True
        self.log("请按下快捷键设置...")

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
            self.log(f"快捷键已设置为: {key_display}")
            self.is_setting_key = False

    def on_key_pressed(self, event):
        if self.is_setting_key:
            if event.event_type == 'down':
                self._handle_key_setting(event)
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

    def test_translation(self):
        test_text = self.test_input.get().strip()
        if not test_text:
            self.log("请输入要翻译的中文")
            return
        result = self.engine.translate(test_text)
        self.log(f"翻译: {test_text} → {result}")

    def save_config(self):
        self.config.save_config()
        self.log("配置已保存")
        messagebox.showinfo("保存成功", "配置已保存到 config.json")

    def _start_keyboard_listener(self):
        keyboard.hook(self.on_key_pressed)
        keyboard.add_hotkey('ctrl+alt+t', self.toggle_translation)

    def _create_tray_icon(self):
        try:
            import pystray

            def create_icon_image():
                image = Image.new('RGB', (64, 64), color=(70, 130, 180))
                dc = ImageDraw.Draw(image)
                dc.rectangle([16, 16, 48, 48], fill='white')
                return image

            def on_show(icon, item):
                self.root.after(0, self.restore_from_tray)

            def on_exit(icon, item):
                self.root.after(0, self.quit_app)

            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", on_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", on_exit)
            )

            self.tray_icon = pystray.Icon(
                "dota2_translator",
                create_icon_image(),
                "Dota 2 翻译器",
                menu
            )

            threading.Thread(target=self.tray_icon.run, daemon=True).start()

        except Exception as e:
            self.log(f"托盘初始化失败: {e}")

    def minimize_to_tray(self):
        self.root.withdraw()
        self.is_minimized = True
        if self.tray_icon:
            self.tray_icon.visible = True

    def restore_from_tray(self):
        self.root.deiconify()
        self.is_minimized = False
        if self.tray_icon:
            self.tray_icon.visible = False

    def _on_closing(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit_app()

    def quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        try:
            keyboard.unhook_all()
        except:
            pass
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = Dota2TranslatorGUI()
    app.run()
