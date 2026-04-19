# -*- coding: utf-8 -*-
"""
实时翻译器模块（OCR识别+弹幕显示）
从原版dota2_translator_gui.py完整移植，仅调整引用方式
"""

import os
import time
import threading
import hashlib

class RealtimeTranslator:
    """实时翻译处理器（完整版）"""
    
    def __init__(self, config, engine, realtime_engine, message_callback=None, log_func=None):
        """
        Args:
            config: 配置对象
            engine: 中文→英文翻译引擎
            realtime_engine: 英文→中文翻译引擎
            message_callback: 消息回调函数 (original, translated)
            log_func: 日志回调函数
        """
        self.config = config
        self.engine = engine
        self.realtime_engine = realtime_engine
        self.on_new_message = message_callback or (lambda o, t: None)
        self.log = log_func or (lambda x: None)
        
        self.running = False
        self.thread = None
        self.last_text = ""
        self.last_img_hash = None
        self.ocr_available = False
        self.ocr = None
        # 识别结果缓存（最近10条）
        self.text_cache = []
        self.max_cache_size = 10

    def _clear_cache(self):
        """清空识别结果缓存"""
        self.text_cache = []
        self.last_img_hash = None
        self.last_text = ""
        self.log("[缓存] 已清空")

    def _ensure_ocr_loaded(self):
        """确保OCR模型已加载（与原版完全一致）"""
        if self.ocr is not None:
            return True
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            self.log(f"paddleocr未安装: {e}")
            return False
        except Exception as e:
            self.log(f"加载paddleocr失败: {e}")
            return False

        try:
            from src.environment.python_installer import PythonInstaller
            paddleocr_dir = os.path.join(PythonInstaller.get_data_dir(), "models")
        except Exception:
            paddleocr_dir = os.path.join(os.path.expanduser("~"), "Documents", "Dota2Translator", "models")
        
        os.makedirs(paddleocr_dir, exist_ok=True)

        model_dirs = [
            ("en_PP-OCRv3_det_infer", "inference.pdmodel"),
            ("en_PP-OCRv3_rec_infer", "inference.pdmodel"),
            ("ch_ppocr_mobile_v2.0_cls_infer", "inference.pdmodel"),
        ]

        model_ready = all(
            os.path.exists(os.path.join(paddleocr_dir, dir_name, file_name))
            for dir_name, file_name in model_dirs
        )

        if not model_ready:
            self.log("未检测到OCR模型，即将下载...")
            self.log("下载模型大约需要30MB，请耐心等待...")

            try:
                download_success = True

                if not os.path.exists(os.path.join(paddleocr_dir, "en_PP-OCRv3_det_infer", "inference.pdmodel")):
                    self.log("下载检测模型...")
                    if not self._download_model("det_model"):
                        download_success = False

                if download_success and not os.path.exists(os.path.join(paddleocr_dir, "en_PP-OCRv3_rec_infer", "inference.pdmodel")):
                    self.log("下载识别模型...")
                    if not self._download_model("rec_model"):
                        download_success = False

                if download_success and not os.path.exists(os.path.join(paddleocr_dir, "ch_ppocr_mobile_v2.0_cls_infer", "inference.pdmodel")):
                    self.log("下载方向分类模型...")
                    if not self._download_model("cls_model"):
                        download_success = False

                if download_success:
                    self.log("OCR模型下载完成！")
                else:
                    self.log("部分模型下载失败，请检查网络连接后重试")
                    self.ocr_available = False
                    self._ocr_error = "模型下载失败"
                    return False

            except Exception as download_error:
                self.log(f"模型下载失败: {download_error}")
                self.log("请检查网络连接后重试")
                self.ocr_available = False
                self._ocr_error = str(download_error)
                return False

        try:
            self.log("正在加载OCR模型...")
            os.environ['GLOG_minloglevel'] = '2'
            os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'
            
            det_model_dir = os.path.join(paddleocr_dir, "en_PP-OCRv3_det_infer")
            rec_model_dir = os.path.join(paddleocr_dir, "en_PP-OCRv3_rec_infer")
            cls_model_dir = os.path.join(paddleocr_dir, "ch_ppocr_mobile_v2.0_cls_infer")
            
            self.ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='en',
                det_model_dir=det_model_dir,
                rec_model_dir=rec_model_dir,
                cls_model_dir=cls_model_dir
            )
            self.ocr_available = True
            self.log("OCR模型加载成功")
            return True
        except Exception as e:
            self.ocr_available = False
            self._ocr_error = str(e)
            self.log(f"OCR加载失败: {e}")
            return False

    def _download_model(self, model_type):
        """下载OCR模型"""
        try:
            import urllib.request
            import ssl
            import os
            
            try:
                from src.environment.python_installer import PythonInstaller
                paddleocr_dir = os.path.join(PythonInstaller.get_data_dir(), "models")
            except Exception:
                paddleocr_dir = os.path.join(os.path.expanduser("~"), "Documents", "Dota2Translator", "models")
            
            os.makedirs(paddleocr_dir, exist_ok=True)
            
            model_urls = {
                "det_model": "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_det_infer.tar",
                "rec_model": "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_rec_infer.tar",
                "cls_model": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar"
            }
            
            if model_type not in model_urls:
                self.log(f"未知模型类型: {model_type}")
                return False
            
            url = model_urls[model_type]
            model_dir = os.path.join(paddleocr_dir, model_type.replace("_model", ""))
            tar_path = os.path.join(paddleocr_dir, f"{model_type}.tar")
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            self.log(f"下载 {model_type} 从 {url[:50]}...")
            urllib.request.urlretrieve(url, tar_path)
            
            import tarfile
            with tarfile.open(tar_path, 'r') as tar:
                tar.extractall(paddleocr_dir)
            
            os.remove(tar_path)
            self.log(f"{model_type} 下载完成")
            return True
            
        except Exception as e:
            self.log(f"下载模型失败({model_type}): {e}")
            return False

    def _preprocess_image(self, img_np):
        """图像预处理：提取白色文字、放大、形态学处理（与原版完全一致）"""
        import cv2
        import numpy as np
        
        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif len(img_np.shape) == 3 and img_np.shape[2] == 3:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_np
        
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return mask

    def _check_text_duplicate(self, text):
        """检查文本是否重复"""
        text_lower = text.lower().strip()
        if text_lower == self.last_text:
            return True, text
        self.last_text = text_lower
        return False, text

    def on_realtime_message(self, original: str, translated: str):
        """收到实时翻译消息回调（与原版一致）"""
        if hasattr(self, '_last_translated') and self._last_translated == translated:
            return
        self._last_translated = translated
        self.log(f"实时翻译: {original[:20]}... → {translated[:20]}...")
        self.on_new_message(original, translated)

    def start(self):
        """开始实时翻译（与原版一致）"""
        if self.running:
            return
        if not self._ensure_ocr_loaded():
            if hasattr(self, '_ocr_error'):
                self.log(f"OCR错误: {self._ocr_error}")
            else:
                self.log("OCR不可用，无法开启实时翻译")
            return
        self._clear_cache()
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.log("实时翻译已开启")

    def stop(self):
        """停止实时翻译"""
        self.running = False
        self.log("实时翻译已关闭")

    @property
    def is_running(self):
        return self.running

    def _monitor_loop(self):
        """监控循环（与原版完全一致）"""
        import mss
        import numpy as np
        
        sct = mss.mss()
        
        while self.running:
            try:
                region = self.config.get('capture_region', {})
                if not region or region.get('width', 0) == 0:
                    self.log("[监控] 等待设置识别区域...")
                    time.sleep(1)
                    continue
                
                x = region.get('x', 0)
                y = region.get('y', 0)
                w = region.get('width', 100)
                h = region.get('height', 50)
                
                img = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
                img_np = np.array(img)
                
                img_hash = hashlib.md5(img_np.tobytes()).hexdigest()
                
                if img_hash == self.last_img_hash:
                    time.sleep(1.0)
                    continue
                
                self.last_img_hash = img_hash
                
                try:
                    result = self.ocr.ocr(img_np)
                    
                    texts = []
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) >= 2:
                                text = line[1][0]
                                if text:
                                    texts.append(text)
                    
                    current_text = ' '.join(texts).strip()
                    
                    if current_text and current_text == self.last_text:
                        time.sleep(1.0)
                        continue
                    
                    if current_text:
                        has_english = any('a' <= c.lower() <= 'z' for c in current_text)
                        
                        if has_english:
                            email = self.config.get('email', '')
                            translated = self.realtime_engine.translate(current_text, email if email else None)
                            
                            self.last_text = current_text
                            if translated and translated != current_text:
                                self.log(f"[翻译] {current_text} → {translated}")
                                self.on_new_message(current_text, translated)
                            else:
                                self.log(f"[翻译] {current_text} → (失败) {current_text}")
                                self.on_new_message(current_text, f"(失败) {current_text}")
                except Exception as e:
                    self.log(f"[监控] OCR处理异常: {e}")
                
                interval = 1.0
                time.sleep(interval)
                
            except Exception as e:
                self.log(f"[监控] 异常: {e}")
                time.sleep(1)
