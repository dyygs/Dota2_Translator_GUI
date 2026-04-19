# -*- coding: utf-8 -*-
"""
翻译引擎模块（与原版完全一致）
"""

class TranslationEngine:
    """翻译引擎 - 封装Dota2TranslationSystem"""
    
    def __init__(self, mode=1):
        self.mode = mode
        self._system = None
        self._init_error = None

        try:
            from src.translator.dota2_translation_system import Dota2TranslationSystem
            self._system = Dota2TranslationSystem(mode=mode)
        except Exception as e:
            self._init_error = str(e)
            print(f"[TranslationEngine] 初始化失败: {e}")
            import traceback
            traceback.print_exc()

    def translate(self, text: str, email: str = None) -> str:
        if not text or not text.strip():
            return text

        if self._system:
            try:
                result, _ = self._system.translate(text, email=email)
                return result if result else text
            except Exception as e:
                print(f"[TranslationEngine] 翻译失败: {e}")
                import traceback
                traceback.print_exc()
                return text
        else:
            print(f"[TranslationEngine] 系统未初始化: {self._init_error}")
            return text
