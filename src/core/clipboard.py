# -*- coding: utf-8 -*-
"""
剪贴板管理模块
"""

import pyperclip

class ClipboardManager:
    """剪贴板管理器"""
    
    @staticmethod
    def copy(text):
        """
        复制文本到剪贴板
        
        Args:
            text: 要复制的文本
        """
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"复制到剪贴板失败: {e}")
            return False
    
    @staticmethod
    def paste():
        """
        从剪贴板粘贴文本
        
        Returns:
            str|None: 剪贴板内容，失败返回None
        """
        try:
            return pyperclip.paste()
        except Exception as e:
            print(f"从剪贴板读取失败: {e}")
            return None
    
    @staticmethod
    def clear():
        """清空剪贴板"""
        try:
            pyperclip.copy('')
            return True
        except Exception as e:
            print(f"清空剪贴板失败: {e}")
            return False
