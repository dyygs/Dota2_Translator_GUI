# -*- coding: utf-8 -*-
"""
Dota2 智能翻译系统 V2.0
独立模块，支持：文本预处理、多级缓存、智能模板、智能路由、多引擎、译后处理、质量评估
"""

import re
import json
import hashlib
from typing import Optional, Tuple, Dict, Any

from src.translation_api import translate as api_translate

class Dota2TranslationSystem:
    """Dota2智能翻译系统"""
    
    def __init__(self, mode: int = 1):
        """
        初始化翻译系统
        mode: 1=中文→英文, 2=英文→中文
        """
        self.mode = mode
        
        # 加载词汇表
        self._load_vocabulary()
        
        # 初始化各模块
        self.cache = {}  # 精确缓存
        self.phrase_cache = {}  # 句式缓存
        self._init_post_processors()
    
    def _load_vocabulary(self):
        """加载词汇表"""
        try:
            from src.词汇表_new import ZH_TO_EN, EN_TO_ZH, PHRASE_TEMPLATES_ZH_TO_EN, PHRASE_TEMPLATES_EN_TO_ZH
            
            if self.mode == 1:
                self.terms = ZH_TO_EN
                self.phrase_templates = PHRASE_TEMPLATES_ZH_TO_EN
            else:
                self.terms = EN_TO_ZH
                self.phrase_templates = PHRASE_TEMPLATES_EN_TO_ZH
            
            # 按长度降序排列
            self._sorted_terms = sorted(self.terms.keys(), key=len, reverse=True)
            self._placeholder_pattern = re.compile(r'\{(\w+)\}')
        except ImportError:
            self.terms = {}
            self.phrase_templates = {}
            self._sorted_terms = []
            self._placeholder_pattern = re.compile(r'\{(\w+)\}')
    
    def _init_post_processors(self):
        """初始化后处理器"""
        # 中文→英文后处理规则
        self.en_post_rules = [
            (r'\beye\b', 'ward'),
            (r'\beyes\b', 'ward'),
            (r'\bfog\b', 'smoke'),
        ]
        
        # 英文→中文后处理规则
        self.zh_post_rules = []
        
        # 荒谬输出黑名单（中译英）
        self.absurd_zh_to_en = [
            'fleshy mountain',
            'meat mountain',
            'meaty mountain',
            'meat hill',
            'buy livelihoods',
            'open a veto',
            'black yellow',
        ]
        
        # 荒谬输出黑名单（英译中）
        self.absurd_en_to_zh = [
            '部队工作人员',
            '庇佑',
        ]
    
    # ==================== 第1步: 文本预处理 ====================
    def preprocess(self, text: str) -> str:
        """
        文本预处理
        - 清洗与规范化
        - 领域检测
        - 上下文关联检查
        """
        if not text or not text.strip():
            return text
        
        # 去除首尾空白
        text = text.strip()
        
        # 统一标点
        text = text.replace('，', ',')
        text = text.replace('。', '.')
        text = text.replace('！', '!')
        text = text.replace('？', '?')
        
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def detect_dota2_context(self, text: str) -> bool:
        """
        Dota2领域检测
        检测文本是否包含Dota2相关词汇
        """
        dota2_keywords = [
            # 英雄
            '英雄', '黑鸟', '蓝猫', '剑圣', '敌法', '虚空', '抄袭', '猛犸', '谜团',
            '白虎', 'pa', 'sf', 'tb', 'od', 'am', 'jugg', 'storm', 'void',
            # 物品
            '眼', '粉', '雾', 'bkb', '跳刀', '否决', '撒旦', '分身', '羊刀', '紫苑',
            'ward', 'dust', 'bkb', 'blink', 'nullifier', 'satanic', 'manta', 'hex', 'orchid',
            # 位置
            '中', '上', '下', '野', 'mid', 'top', 'bot', 'jungle',
            # 动作
            '打', '去', '抓', '推', '守', '买', 'farm', 'gank', 'push', 'defend', 'buy',
            # 其他
            '肉山', '盾', 'tp', '买活', 'roshan', 'aegis', 'buyback', 'tp',
        ]
        
        text_lower = text.lower()
        for keyword in dota2_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    # ==================== 第2步: 多级缓存 ====================
    def _check_cache(self, text: str) -> Optional[str]:
        """精确缓存检查"""
        cache_key = self._get_cache_key(text)
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        return None
    
    def _add_to_cache(self, text: str, result: str):
        """添加到缓存"""
        cache_key = self._get_cache_key(text)
        self.cache[cache_key] = result
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{self.mode}:{text}".encode()).hexdigest()
    
    # ==================== 第3步: 智能模板匹配 ====================
    def _template_match(self, text: str) -> Optional[str]:
        """智能模板匹配"""
        text_lower = text.lower().strip()
        
        # 3.1 精确模板匹配
        if text_lower in self.phrase_templates:
            return self.phrase_templates[text_lower]
        
        # 3.2 占位符模板匹配
        result = self._placeholder_match(text_lower)
        if result:
            return result
        
        return None
    
    def _placeholder_match(self, text: str) -> Optional[str]:
        """占位符模板匹配（按模板长度降序，更具体的模板优先）"""
        # 按模板长度降序排列，确保更具体的模板优先匹配
        sorted_templates = sorted(
            self.phrase_templates.items(),
            key=lambda x: len(x[0].replace('{', '').replace('}', '')),
            reverse=True
        )

        # 统一将中文逗号替换为英文，方便匹配
        text_normalized = text.replace('，', ',')

        for template, translation in sorted_templates:
            placeholders = self._placeholder_pattern.findall(template)

            if not placeholders:
                continue

            # 构建正则
            pattern = template.replace('，', ',')
            for placeholder in placeholders:
                pattern = pattern.replace('{' + placeholder + '}', '(?P<' + placeholder + '>[^,]+)')
            pattern = pattern + '.*$'

            match = re.match(pattern, text_normalized, re.IGNORECASE)
            if match:
                result = translation
                for placeholder in placeholders:
                    matched_value = match.group(placeholder).strip()
                    translated_value = self._translate_term(matched_value)
                    result = result.replace('{' + placeholder + '}', translated_value)
                return result

        return None
    
    def _translate_term(self, term: str) -> str:
        """术语翻译"""
        term_lower = term.lower().strip()
        
        if term_lower in self.terms:
            return self.terms[term_lower]
        
        # 最长匹配优先
        for t in self._sorted_terms:
            if t in term_lower:
                return term_lower.replace(t, self.terms[t])
        
        return term
    
    # ==================== 第4步: 术语智能处理 ====================
    def _term_processing(self, text: str) -> str:
        """术语处理"""
        text_lower = text.lower().strip()
        
        # 精确术语替换
        for term in self._sorted_terms:
            if term in text_lower:
                text_lower = text_lower.replace(term, self.terms[term])
        
        return text_lower
    
    # ==================== 第5步: 智能路由 ====================
    def _smart_route(self, text: str) -> str:
        """
        智能路由（匹配优先级：完整短语 > 句式模板 > 术语替换 > API）
        - 完整短语模板命中 → 直接返回（短路策略）
        - 术语完全覆盖 → 本地翻译
        - API翻译 → 荒谬输出拦截
        """
        # 优先级1：完整短语模板匹配（短路策略）
        template_result = self._template_match(text)
        if template_result:
            return template_result
        
        # 优先级2：术语处理
        term_result = self._term_processing(text)
        if term_result != text.lower():
            # 中译英：检查是否有中文残留
            # 英译中：检查是否有英文残留（非术语部分）
            if self.mode == 1:
                if not self._has_chinese_residue(term_result):
                    return term_result
            else:
                # 英译中：如果术语处理后全是中文，返回结果
                if not self._has_english_residue(term_result):
                    return term_result
        
        # 优先级3：API翻译
        api_result = self._call_api(text)
        
        # 荒谬输出拦截
        if self._is_absurd(api_result):
            # 回退到术语替换结果
            if term_result != text.lower():
                return term_result
            # 最后保底：返回原文
            return text
        
        return api_result
    
    def _has_chinese_residue(self, text: str) -> bool:
        """检查是否有中文残留"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _has_english_residue(self, text: str) -> bool:
        """检查是否有英文残留（英译中时使用）"""
        # 排除常见的中英混合术语（如bkb, tp等）
        allowed_english = {'bkb', 'tp', 'miss', 'gank', 'rosh', 'ult', 'hp', 'mp'}
        words = re.findall(r'[a-zA-Z]+', text.lower())
        for word in words:
            if word not in allowed_english and len(word) > 1:
                return True
        return False
    
    def _is_absurd(self, text: str) -> bool:
        """荒谬输出拦截"""
        text_lower = text.lower().strip()
        if self.mode == 1:
            for phrase in self.absurd_zh_to_en:
                if phrase in text_lower:
                    return True
        else:
            for phrase in self.absurd_en_to_zh:
                if phrase in text_lower:
                    return True
        return False
    
    def _is_simple_text(self, text: str) -> bool:
        """判断是否为简单文本"""
        # 简单文本特征：短且包含Dota2术语
        if len(text) <= 20 and self.detect_dota2_context(text):
            return True
        return False
    
    def _local_translate(self, text: str) -> str:
        """本地翻译"""
        # 模板匹配
        result = self._template_match(text)
        if result:
            return result
        
        # 术语处理
        return self._term_processing(text)
    
    # ==================== 第6步: 多引擎翻译 ====================
    def _call_api(self, text: str) -> str:
        """调用翻译API（优先DeepLX，备用MyMemory）"""
        if self.mode == 1:
            source, target = 'zh-CN', 'en'
        else:
            source, target = 'en', 'zh-CN'
        
        result, engine = api_translate(text, source, target)
        return result
    
    # ==================== 第7步: 译后处理 ====================
    def post_process(self, text: str, original: str) -> str:
        """
        译后处理流水线
        - 风格统一
        - 语法校正
        - 格式规范化
        - 一致性检查
        """
        if not text or text == original:
            return text
        
        if self.mode == 1:
            # 中文→英文后处理
            text = self._en_post_process(text)
        else:
            # 英文→中文后处理
            text = self._zh_post_process(text)
        
        return text
    
    def _en_post_process(self, text: str) -> str:
        """英文后处理"""
        # 应用规则
        for pattern, replacement in self.en_post_rules:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # 首字母大写
        if text:
            text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        return text
    
    def _zh_post_process(self, text: str) -> str:
        """中文后处理"""
        # 应用规则
        for pattern, replacement in self.zh_post_rules:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    # ==================== 第8步: 质量评估 ====================
    def evaluate_quality(self, original: str, translated: str) -> Dict[str, Any]:
        """
        质量评估
        返回置信度评分
        """
        result = {
            'confidence': 0.0,
            'has_chinese': False,
            'is_too_short': False,
            'is_same_as_original': False,
        }
        
        if not translated:
            return result
        
        # 检查是否与原文相同
        if translated.lower().strip() == original.lower().strip():
            result['is_same_as_original'] = True
            result['confidence'] = 0.0
            return result
        
        # 检查是否包含中文字符（中文→英文时）
        if self.mode == 1:
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', translated))
            result['has_chinese'] = has_chinese
        
        # 检查是否过短
        if len(translated) < len(original) * 0.3:
            result['is_too_short'] = True
        
        # 计算置信度
        confidence = 1.0
        if result['has_chinese']:
            confidence -= 0.5
        if result['is_too_short']:
            confidence -= 0.3
        
        result['confidence'] = max(0.0, confidence)
        
        return result
    
    # ==================== 主翻译流程 ====================
    def translate(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        完整翻译流程
        返回: (翻译结果, 质量评估)
        """
        if not text or not text.strip():
            return text, {'confidence': 0.0}
        
        # 第1步: 预处理
        original = text
        text = self.preprocess(text)
        
        # 第2步: 缓存检查
        cached = self._check_cache(text)
        if cached:
            return cached, {'confidence': 1.0, 'from_cache': True}
        
        # 第3-5步: 智能路由（模板→术语→API）
        translated = self._smart_route(text)
        
        # 第6步: 译后处理
        translated = self.post_process(translated, original)
        
        # 第7步: 质量评估
        quality = self.evaluate_quality(original, translated)
        
        # 第8步: 添加到缓存
        if quality['confidence'] > 0.5:
            self._add_to_cache(original, translated)
        
        return translated, quality


def translate_zh_to_en(text: str) -> Tuple[str, Dict[str, Any]]:
    """中文→英文翻译便捷函数"""
    system = Dota2TranslationSystem(mode=1)
    return system.translate(text)


def translate_en_to_zh(text: str) -> Tuple[str, Dict[str, Any]]:
    """英文→中文翻译便捷函数"""
    system = Dota2TranslationSystem(mode=2)
    return system.translate(text)


# 测试
if __name__ == "__main__":
    # 测试中文→英文
    test_cases_zh = [
        "帮我买一个眼",
        "黑鸟去中路了",
        "开bkb打",
        "肉山有盾",
        "tp过来"
    ]
    
    print("=" * 50)
    print("中文→英文 翻译测试")
    print("=" * 50)
    
    for text in test_cases_zh:
        result, quality = translate_zh_to_en(text)
        print(f"原文: {text}")
        print(f"翻译: {result}")
        print(f"质量: {quality}")
        print()
