# -*- coding: utf-8 -*-
"""
外部服务模块
"""
from .translation_api import TranslationAPI
from .qrcode_data import QRCODE_BASE64

# update_checker 只有函数，没有类
from . import update_checker

__all__ = ['TranslationAPI', 'QRCODE_BASE64', 'update_checker']
