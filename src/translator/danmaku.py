# -*- coding: utf-8 -*-
"""
弹幕窗口模块 - 从原版完整移植，仅修改引用方式
"""

import tkinter as tk
import ctypes
import time
import threading
import pyperclip


class StrictModeWindow:
    """严格模式悬浮窗（与原版完全一致）"""
    
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


class DanmakuWindow:
    """弹幕显示窗口（与原版完全一致）"""

    def __init__(self, config, on_position_save, root=None):
        self.config = config
        self.on_position_save = on_position_save
        self.root = root
        self.window = None
        self.messages = []
        self.max_messages = config.get('realtime_settings', {}).get('max_messages', 5)
        self.display_duration = 15.0
        self.is_visible = False
        self.hwnd = None
        self._create_window()

    def _create_window(self):
        self.window = tk.Toplevel()
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-transparentcolor', 'black')
        self.window.configure(bg='black')

        saved_pos = self.on_position_save("__get_danmaku_position__")
        danmaku_width = 375
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
            bg='black',
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

        display_text = f"{original} → {translated}"
        for msg in self.messages:
            if self.canvas.itemcget(msg['text'], 'text') == display_text:
                return

        settings = self.config.get('realtime_settings', {})
        font_size = settings.get('font_size', 16)
        text_color = settings.get('original_color', '#FFFFFF')

        danmaku_width = 375
        max_width = danmaku_width - 20

        msg_id = len(self.messages)

        while len(self.messages) >= 2:
            self._remove_oldest()

        line_height = font_size + 4
        total_chars = len(original) + len(translated) + 3
        chars_per_line = max_width // (font_size - 2)
        estimated_lines = max(1, (total_chars + chars_per_line - 1) // chars_per_line)
        text_height = estimated_lines * line_height + 10

        if len(self.messages) == 0:
            y_base = 20
        else:
            last_msg = self.messages[-1]
            y_base = last_msg.get('y_offset', 20) + last_msg.get('height', 35) + 5

        if y_base + text_height > 280:
            self._remove_oldest()
            if len(self.messages) == 0:
                y_base = 20
            else:
                last_msg = self.messages[-1]
                y_base = last_msg.get('y_offset', 20) + last_msg.get('height', 35) + 5

        display_text = f"{original} → {translated}"

        msg_text = self.canvas.create_text(
            10, y_base + text_height // 2,
            text=display_text,
            fill=text_color,
            font=('Microsoft YaHei UI', font_size - 2),
            anchor=tk.W,
            width=max_width,
            tags='message'
        )

        self.messages.append({
            'id': msg_id,
            'text': msg_text,
            'time': time.time(),
            'height': text_height,
            'y_offset': y_base
        })

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
            y_offset = 20
            for m in self.messages:
                msg_height = m.get('height', 35)
                self.canvas.coords(m['text'], 10, y_offset + msg_height // 2)
                m['y_offset'] = y_offset
                y_offset += msg_height + 5
