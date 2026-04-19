# -*- coding: utf-8 -*-
"""
区域选择器模块（与原版完全一致）
"""

import tkinter as tk

class RegionSelector:
    def __init__(self, callback):
        self.callback = callback
        self.selection_window = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self._callback_called = False

    def start_selection(self):
        self._callback_called = False
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
        if self.start_x is not None and not self._callback_called:
            x1, y1 = self.start_x, self.start_y
            x2, y2 = event.x, event.y

            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            self._callback_called = True
            if width > 20 and height > 10:
                self.callback({"x": int(x), "y": int(y), "width": int(width), "height": int(height)})
            else:
                self.callback(None)

            try:
                self.selection_window.destroy()
            except:
                pass

    def cancel_selection(self):
        if not self._callback_called:
            self._callback_called = True
            self.callback(None)
        if self.selection_window:
            try:
                self.selection_window.destroy()
            except:
                pass
