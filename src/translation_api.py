# -*- coding: utf-8 -*-
"""
翻译API模块
支持多个翻译引擎，优先级：DeepLX > MyMemory
支持DeepLX多端点自动切换
"""

import time
import requests
from typing import Optional, Tuple, List, Dict


class TranslationAPI:
    """翻译API管理器"""
    
    DEEPLX_ENDPOINTS = [
        "https://dplx.xi-xu.me/translate",
        "https://deeplx.mingming.dev/translate",
        "https://production.deeplx.yibie.workers.dev/translate",
        "https://deeplx-cf.aizaizuori.workers.dev/translate",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.deeplx_endpoints = self.DEEPLX_ENDPOINTS.copy()
        self.endpoint_status: Dict[str, Dict] = {
            url: {'failures': 0, 'last_success': 0, 'available': True}
            for url in self.deeplx_endpoints
        }
        self.max_failures = 3
        self.recovery_interval = 300
        
        self.mymemory_url = "https://api.mymemory.translated.net/get"
        self.mymemory_email = 'REDACTED_EMAIL'
        
        self.request_interval = 1.0
        self.last_request_time = 0
        self.consecutive_failures = 0
    
    def _get_available_endpoints(self) -> List[str]:
        """获取可用端点列表（按失败次数排序）"""
        now = time.time()
        available = []
        
        for url in self.deeplx_endpoints:
            status = self.endpoint_status[url]
            if status['failures'] >= self.max_failures:
                if now - status['last_success'] > self.recovery_interval:
                    status['failures'] = 0
                    status['available'] = True
                    available.append(url)
            else:
                available.append(url)
        
        available.sort(key=lambda x: self.endpoint_status[x]['failures'])
        return available
    
    def _mark_success(self, url: str):
        """标记端点成功"""
        self.endpoint_status[url]['failures'] = 0
        self.endpoint_status[url]['last_success'] = time.time()
        self.endpoint_status[url]['available'] = True
    
    def _mark_failure(self, url: str):
        """标记端点失败"""
        self.endpoint_status[url]['failures'] += 1
        if self.endpoint_status[url]['failures'] >= self.max_failures:
            self.endpoint_status[url]['available'] = False
    
    def translate(self, text: str, source: str, target: str) -> Tuple[str, str]:
        """
        翻译文本
        返回: (翻译结果, 使用的引擎名称)
        """
        if not text or not text.strip():
            return text, 'none'
        
        result = self._call_deeplx(text, source, target)
        if result:
            return result, 'deeplx'
        
        result = self._call_mymemory(text, source, target)
        if result:
            return result, 'mymemory'
        
        return text, 'none'
    
    def _rate_limit(self, after_failure: bool = False):
        """
        请求频率限制
        after_failure: 是否在失败后调用（失败时增加等待时间）
        """
        if after_failure and self.consecutive_failures > 0:
            wait_time = self.request_interval * (2 ** min(self.consecutive_failures - 1, 3))
            time.sleep(wait_time)
        
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _on_success(self):
        """请求成功时重置失败计数"""
        self.consecutive_failures = 0
    
    def _on_failure(self):
        """请求失败时增加失败计数"""
        self.consecutive_failures += 1
    
    def _call_deeplx(self, text: str, source: str, target: str) -> Optional[str]:
        """
        调用DeepLX API（多端点自动切换）
        """
        self._rate_limit()
        
        lang_map = {
            'zh-CN': 'ZH',
            'en': 'EN',
            'zh': 'ZH',
        }
        
        source_lang = lang_map.get(source, source.upper())
        target_lang = lang_map.get(target, target.upper())
        
        payload = {
            'text': text,
            'source_lang': source_lang,
            'target_lang': target_lang,
        }
        
        endpoints = self._get_available_endpoints()
        
        for url in endpoints:
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=15
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    translated = None
                    
                    if 'data' in result:
                        translated = result['data']
                    elif 'translations' in result and result['translations']:
                        translated = result['translations'][0].get('text', '')
                    elif 'text' in result:
                        translated = result['text']
                    
                    if translated and not translated.startswith('http'):
                        self._mark_success(url)
                        self._on_success()
                        return translated
                
                if resp.status_code == 429:
                    self._mark_failure(url)
                    self._on_failure()
                    self._rate_limit(after_failure=True)
                    continue
                    
            except requests.exceptions.Timeout:
                self._mark_failure(url)
                self._on_failure()
                continue
            except requests.exceptions.ConnectionError:
                self._mark_failure(url)
                self._on_failure()
                continue
            except Exception:
                self._mark_failure(url)
                self._on_failure()
                continue
        
        return None
    
    def _call_mymemory(self, text: str, source: str, target: str) -> Optional[str]:
        """
        调用MyMemory API（备用引擎）
        """
        self._rate_limit()
        
        params = {
            'q': text,
            'langpair': f'{source}|{target}',
            'de': self.mymemory_email
        }
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    time.sleep(delay)
                
                resp = self.session.get(
                    self.mymemory_url,
                    params=params,
                    timeout=10
                )
                
                if resp.status_code == 429:
                    retry_after = resp.headers.get('Retry-After')
                    if retry_after:
                        time.sleep(int(retry_after))
                    else:
                        time.sleep(base_delay * (2 ** attempt))
                    continue
                
                result = resp.json()
                
                if result.get('responseStatus') == 200:
                    translated = result['responseData']['translatedText']
                    time.sleep(0.5)
                    return translated
                elif result.get('responseStatus') == 429:
                    continue
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                continue
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                continue
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                continue
        
        return None


_api_instance = None


def get_api() -> TranslationAPI:
    """获取API单例"""
    global _api_instance
    if _api_instance is None:
        _api_instance = TranslationAPI()
    return _api_instance


def translate(text: str, source: str, target: str) -> Tuple[str, str]:
    """
    翻译便捷函数
    返回: (翻译结果, 使用的引擎名称)
    """
    return get_api().translate(text, source, target)


def translate_zh_to_en(text: str) -> Tuple[str, str]:
    """中文→英文翻译"""
    return translate(text, 'zh-CN', 'en')


def translate_en_to_zh(text: str) -> Tuple[str, str]:
    """英文→中文翻译"""
    return translate(text, 'en', 'zh-CN')


if __name__ == "__main__":
    print("=" * 50)
    print("翻译API测试")
    print("=" * 50)
    
    test_cases = [
        ("开团了集合", "zh-CN", "en"),
        ("help me buy a ward", "en", "zh-CN"),
        ("肉山刷新了", "zh-CN", "en"),
    ]
    
    for text, source, target in test_cases:
        result, engine = translate(text, source, target)
        print(f"[{engine}] {source}→{target}: {text} -> {result}")
