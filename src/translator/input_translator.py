# -*- coding: utf-8 -*-
"""
输入翻译器模块（F6触发）
"""

import re

class InputTranslator:
    """输入翻译处理器"""
    
    def __init__(self, engine, realtime_engine, config, log_func=None):
        """
        Args:
            engine: 中文→英文翻译引擎
            realtime_engine: 英文→中文翻译引擎
            config: 配置对象
            log_func: 日志回调函数
        """
        self.engine = engine
        self.realtime_engine = realtime_engine
        self.config = config
        self.log = log_func or (lambda x: None)
    
    def handle_f6_strict(self, text):
        """
        处理严格模式F6
        
        Args:
            text: 输入文本
            
        Returns:
            str: 翻译结果
        """
        if not text or not text.strip():
            return ""
        
        translated = self.engine.translate(text)
        
        import pyperclip
        try:
            pyperclip.copy(translated)
            self.log(f"已复制到剪贴板: {translated}")
        except Exception as e:
            self.log(f"复制失败: {e}")
        
        return translated
    
    def handle_f6_non_strict(self, text):
        """
        处理非严格模式F6
        
        Args:
            text: 输入文本
            
        Returns:
            str: 翻译结果
        """
        if not text or not text.strip():
            return ""
        
        # 检测是否包含中文字符
        if re.search(r'[\u4e00-\u9fff]', text):
            # 包含中文 → 翻译成英文
            translated = self.engine.translate(text)
        else:
            # 不包含中文 → 可能是英文，不翻译或翻译成中文
            translated = text
        
        import pyperclip
        try:
            pyperclip.copy(translated)
            
            import pyautogui
            import time
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.05)
            pyautogui.press('enter')
            
            self.log(f"已发送: {translated}")
        except Exception as e:
            self.log(f"发送失败: {e}")
        
        return translated
    
    def translate(self, text, strict_mode=True):
        """
        统一翻译接口
        
        Args:
            text: 输入文本
            strict_mode: 是否为严格模式
            
        Returns:
            str: 翻译结果
        """
        if strict_mode:
            return self.handle_f6_strict(text)
        else:
            return self.handle_f6_non_strict(text)
