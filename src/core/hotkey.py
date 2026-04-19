# -*- coding: utf-8 -*-
"""
快捷键管理模块
"""

import keyboard

class HotkeyManager:
    """快捷键管理器"""
    
    def __init__(self, log_func=None):
        """
        Args:
            log_func: 日志回调函数
        """
        self.callbacks = {}
        self.log = log_func or (lambda x: None)
        self._suppressed_keys = set()
    
    def register(self, key_name, callback, suppress=False):
        """
        注册快捷键回调
        
        Args:
            key_name: 按键名称（如 'f6', 'f7'）
            callback: 回调函数
            suppress: 是否抑制按键事件
        """
        self.callbacks[key_name] = {
            'callback': callback,
            'suppress': suppress
        }
        
        if suppress:
            self._suppressed_keys.add(key_name.lower())
    
    def unregister(self, key_name):
        """取消注册快捷键"""
        if key_name in self.callbacks:
            del self.callbacks[key_name]
            self._suppressed_keys.discard(key_name.lower())
    
    def on_key_event(self, event):
        """
        处理按键事件（在keyboard.on_press中使用）
        
        Args:
            event: keyboard.KeyboardEvent对象
            
        Returns:
            bool: 是否应该抑制该按键
        """
        key_name = event.name.lower()
        
        if key_name in self.callbacks:
            callback_info = self.callbacks[key_name]
            try:
                callback_info['callback'](event)
            except Exception as e:
                self.log(f"快捷键处理错误 ({key_name}): {e}")
            
            return callback_info['suppress']
        
        return False
    
    def is_suppressed(self, key_name):
        """检查按键是否被抑制"""
        return key_name.lower() in self._suppressed_keys
    
    def start_listening(self):
        """开始监听键盘事件"""
        keyboard.on_press(self.on_key_event)
    
    def stop_listening(self):
        """停止监听键盘事件"""
        keyboard.unhook_all()
