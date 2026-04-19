# -*- coding: utf-8 -*-
"""
翻译功能模块
"""
from .engine import TranslationEngine
from .input_translator import InputTranslator
from .realtime_translator import RealtimeTranslator
from .danmaku import DanmakuWindow, StrictModeWindow
from .templates import TranslationTemplates
from .dota2_translation_system import Dota2TranslationSystem, translate_zh_to_en, translate_en_to_zh

__all__ = [
    'TranslationEngine', 'InputTranslator', 'RealtimeTranslator',
    'DanmakuWindow', 'StrictModeWindow', 'TranslationTemplates',
    'Dota2TranslationSystem', 'translate_zh_to_en', 'translate_en_to_zh'
]
