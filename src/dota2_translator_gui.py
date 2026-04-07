# -*- coding: utf-8 -*-
"""
Dota 2 中文→英文翻译器 - GUI版本
功能：现代化界面 + 系统托盘 + 自定义触发键
"""

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


class Config:
    DEFAULT_CONFIG = {
        "trigger_key": "f6",
        "toggle_hotkey": "ctrl+alt+t",
        "cooldown": 0.2,
        "source_lang": "zh-CN",
        "target_lang": "en"
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
        self.root.title("Dota 2 中文翻译器")
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
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=('Microsoft YaHei UI', 11),
            foreground='green'
        )
        self.status_label.pack(anchor='w')

        self.trigger_key_var = tk.StringVar(value=f"触发键: {self.config.trigger_key.upper()}")
        ttk.Label(status_frame, textvariable=self.trigger_key_var).pack(anchor='w')

        self.mode_var = tk.StringVar(value="模式: 中→英")
        ttk.Label(status_frame, textvariable=self.mode_var).pack(anchor='w')

        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.pack(fill=tk.X, pady=5)

        btn_frame1 = ttk.Frame(control_frame)
        btn_frame1.pack(fill=tk.X, pady=5)

        self.toggle_btn = ttk.Button(
            btn_frame1,
            text="禁用翻译",
            command=self.toggle_translation,
            width=15
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5)

        self.set_key_btn = ttk.Button(
            btn_frame1,
            text="设置触发键",
            command=self.start_set_key,
            width=15
        )
        self.set_key_btn.pack(side=tk.LEFT, padx=5)

        self.mode_btn = ttk.Button(
            btn_frame1,
            text="切换模式",
            command=self.toggle_mode,
            width=15
        )
        self.mode_btn.pack(side=tk.LEFT, padx=5)

        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=5)

        ttk.Label(btn_frame2, text="测试输入:").pack(side=tk.LEFT, padx=2)
        self.test_input = ttk.Entry(btn_frame2, width=25)
        self.test_input.pack(side=tk.LEFT, padx=5)
        self.test_input.insert(0, "帮我买个眼")

        ttk.Button(
            btn_frame2,
            text="测试翻译",
            command=self.test_translation,
            width=10
        ).pack(side=tk.LEFT, padx=5)

        btn_frame3 = ttk.Frame(control_frame)
        btn_frame3.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame3,
            text="最小化到托盘",
            command=self.minimize_to_tray,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame3,
            text="保存配置",
            command=self.save_config,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        self.key_hint_label = ttk.Label(
            control_frame,
            text="",
            font=('Microsoft YaHei UI', 9),
            foreground='blue'
        )
        self.key_hint_label.pack(anchor='w', pady=5)

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
            self.status_var.set("● 已启动")
            self.status_label.config(foreground='green')
            self.toggle_btn.config(text="禁用翻译")
            self.log("翻译功能已启用")
        else:
            self.status_var.set("● 已禁用")
            self.status_label.config(foreground='red')
            self.toggle_btn.config(text="启用翻译")
            self.log("翻译功能已禁用")

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
        self.set_key_btn.config(state='disabled')
        self.key_hint_label.config(text="请按下您想使用的触发键（如 F7、空格等）...")
        self.log("等待按键输入...")

    def on_key_pressed(self, event):
        if self.is_setting_key:
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
                self.trigger_key_var.set(f"触发键: {key_display}")
                self.key_hint_label.config(text=f"✓ 触发键已设置为: {key_display}")
                self.log(f"触发键已设置为: {key_display}")
                self.is_setting_key = False
                self.set_key_btn.config(state='normal')
            return

        if event.name.lower() == self.config.trigger_key.lower():
            if self.enabled and not self.is_translating:
                current_time = time.time()
                cooldown = self.config.get('cooldown', 0.2)
                if current_time - self.last_time > cooldown:
                    self.last_time = current_time
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
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = Dota2TranslatorGUI()
    app.run()
