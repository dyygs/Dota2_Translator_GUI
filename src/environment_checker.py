# -*- coding: utf-8 -*-
"""
环境检查与自动修复模块
功能：检查Python运行时、依赖包、OCR模型文件完整性，并提供自动修复能力
"""

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import tarfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable
from enum import Enum


class CheckLevel(Enum):
    """检查级别"""
    CRITICAL = 1    # 关键：Python运行时、核心依赖
    IMPORTANT = 2   # 重要：OCR模型
    NORMAL = 3      # 普通：可选组件


class CheckResult(Enum):
    """检查结果"""
    OK = "ok"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    REPAIR_FAILED = "repair_failed"


class EnvironmentChecker:
    """环境检查与自动修复器"""

    CORE_DEPENDENCIES = [
        "paddleocr",
        "opencv_python",
        "numpy",
        "PIL",
        "paddlepaddle",
    ]

    PIP_PACKAGES = {
        "paddleocr": "paddleocr==2.7.34",
        "paddlepaddle": "paddlepaddle==2.6.2",
        "opencv-python": "opencv-python<=4.6.0.66",
        "numpy": "numpy<2.0.0",
        "pillow": "pillow>=9.0.0",
        "keyboard": "keyboard==0.13.5",
        "pyperclip": "pyperclip==1.8.2",
        "pyautogui": "pyautogui==0.9.54",
        "requests": "requests>=2.32.0",
        "mss": "mss>=9.0.0",
    }

    PIP_MIRRORS = [
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
        "https://pypi.mirrors.ustc.edu.cn/simple",
        "https://pypi.doubanio.com/simple",
    ]

    MODEL_FILES = {
        "det_model": {
            "files": ["en_PP-OCRv3_det_infer.pdmodel", "en_PP-OCRv3_det_infer.pdiparams"],
            "urls": [
                "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_det_infer.tar",
                "https://gitee.com/paddlepaddle/PaddleOCR/releases/download/v3.0.0-beta0/en_PP-OCRv3_det_infer.tar",
            ],
            "md5": None,
            "description": "OCR检测模型"
        },
        "rec_model": {
            "files": ["en_PP-OCRv3_rec_infer.pdmodel", "en_PP-OCRv3_rec_infer.pdiparams"],
            "urls": [
                "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_rec_infer.tar",
                "https://gitee.com/paddlepaddle/PaddleOCR/releases/download/v3.0.0-beta0/en_PP-OCRv3_rec_infer.tar",
            ],
            "md5": None,
            "description": "OCR识别模型"
        },
        "cls_model": {
            "files": ["ch_PP-OCRv3_cls_infer.pdmodel", "ch_PP-OCRv3_cls_infer.pdiparams"],
            "urls": [
                "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
                "https://gitee.com/paddlepaddle/PaddleOCR/releases/download/v3.0.0-beta0/ch_ppocr_mobile_v2.0_cls_infer.tar",
            ],
            "md5": None,
            "description": "OCR方向分类模型"
        }
    }

    def __init__(self, app_root: str = None, log_callback: Callable = None):
        self.app_root = app_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_callback = log_callback or self._default_log
        self.check_results: Dict[str, Dict] = {}
        self.repair_actions: List[Dict] = []
        self._current_mirror_index = 0
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger("EnvironmentChecker")
        self.logger.setLevel(logging.DEBUG)

        log_dir = os.path.join(self.app_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "environment_check.log")

        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _default_log(self, message: str):
        print(f"[Environment] {message}")
        self.logger.info(message)

    def log(self, message: str, level: str = "info"):
        self.log_callback(message)
        getattr(self.logger, level)(message)

    def get_python_exe_path(self) -> Optional[str]:
        """获取Python运行时路径"""
        possible_paths = [
            r"D:\Dota2Translator\python\python.exe",
            os.path.join(self.app_root, "runtime", "python.exe"),
            os.path.join(self.app_root, "runtime", "python3.exe"),
            os.path.join(self.app_root, "python.exe"),
            sys.executable,
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def get_pip_path(self) -> Optional[str]:
        """获取pip路径"""
        possible_paths = [
            os.path.join(self.app_root, "runtime", "Scripts", "pip.exe"),
            os.path.join(self.app_root, "runtime", "Scripts", "pip3.exe"),
            os.path.join(self.app_root, "Scripts", "pip.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def check_python_runtime(self) -> Tuple[CheckResult, str]:
        """检查Python运行时"""
        self.log("检查Python运行时...")

        python_path = self.get_python_exe_path()

        if not python_path:
            msg = f"Python运行时未找到 (预期路径: {os.path.join(self.app_root, 'runtime')})"
            self.log(f"[错误] {msg}", "error")
            return CheckResult.MISSING, msg

        try:
            result = subprocess.run(
                [python_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                self.log(f"[OK] Python运行时正常: {version}")
                return CheckResult.OK, f"Python {version}"
        except Exception as e:
            msg = f"Python运行时不可用: {str(e)}"
            self.log(f"[错误] {msg}", "error")
            return CheckResult.CORRUPTED, msg

        return CheckResult.MISSING, "Python运行时检查失败"

    def check_dependency(self, module_name: str) -> Tuple[CheckResult, str]:
        """检查单个依赖包"""
        try:
            __import__(module_name)
            return CheckResult.OK, f"{module_name} 可用"
        except ImportError as e:
            return CheckResult.MISSING, f"{module_name} 导入失败: {str(e)}"
        except Exception as e:
            err_msg = str(e)
            if "DLL" in err_msg or "failed" in err_msg.lower():
                return CheckResult.MISSING, f"{module_name} DLL加载失败"
            return CheckResult.CORRUPTED, f"{module_name} 异常: {err_msg[:100]}"

    def check_dependencies(self) -> Dict[str, Tuple[CheckResult, str]]:
        """检查所有核心依赖"""
        results = {}

        for dep in self.CORE_DEPENDENCIES:
            try:
                result, message = self.check_dependency(dep)
                results[dep] = (result, message)

                if result == CheckResult.OK:
                    self.log(f"[OK] {message}")
                else:
                    self.log(f"[{result.value.upper()}] {message}", "warning")
            except Exception as e:
                self.log(f"[错误] 检查 {dep} 时异常: {str(e)[:50]}", "error")
                results[dep] = (CheckResult.MISSING, f"检查失败: {str(e)[:50]}")

        return results

    def get_paddleocr_model_dir(self) -> str:
        """获取PaddleOCR模型目录"""
        model_dir = r"D:\Dota2Translator\models"
        return model_dir

    def check_model_file(self, model_key: str) -> Tuple[CheckResult, List[str]]:
        """检查单个模型组"""
        model_info = self.MODEL_FILES[model_key]
        model_dir = self.get_paddleocr_model_dir()
        missing_files = []

        for filename in model_info["files"]:
            file_path = os.path.join(model_dir, filename)
            if not os.path.exists(file_path):
                missing_files.append(filename)
                self.log(f"[缺失] {model_info['description']}: {filename}", "warning")
            else:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    missing_files.append(filename)
                    self.log(f"[损坏] {model_info['description']}: {filename} (空文件)", "error")

        if not missing_files:
            return CheckResult.OK, []
        elif missing_files == model_info["files"]:
            return CheckResult.MISSING, missing_files
        else:
            return CheckResult.CORRUPTED, missing_files

    def check_ocr_models(self) -> Dict[str, Tuple[CheckResult, List[str]]]:
        """检查所有OCR模型"""
        results = {}

        for model_key in self.MODEL_FILES:
            result, missing = self.check_model_file(model_key)
            results[model_key] = (result, missing)

        return results

    def verify_model_md5(self, file_path: str, expected_md5: str = None) -> bool:
        """验证文件MD5"""
        if expected_md5 is None:
            return True

        if not os.path.exists(file_path):
            return False

        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5_hash.update(chunk)
            actual_md5 = md5_hash.hexdigest()
            return actual_md5 == expected_md5
        except Exception as e:
            self.log(f"MD5校验失败: {str(e)}", "error")
            return False

    def download_with_retry(self, urls: List[str], dest_file: str, description: str,
                            progress_callback: Callable = None) -> bool:
        """使用多镜像重试下载"""
        import urllib.request
        import ssl

        last_error = None

        for i, url in enumerate(urls):
            mirror_name = url.split('/')[2] if len(url.split('/')) > 2 else f"镜像{i+1}"
            self.log(f"尝试从 {mirror_name} 下载 {description}...", "info")

            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                def reporthook(block_num, block_size, total_size):
                    if progress_callback and total_size > 0:
                        percent = min(100, int((block_num * block_size * 100) / total_size))
                        progress_callback(percent)

                urllib.request.urlretrieve(url, dest_file, reporthook if progress_callback else None)
                self.log(f"{description} 下载成功", "info")
                return True

            except Exception as e:
                last_error = str(e)
                self.log(f"{mirror_name} 下载失败: {last_error}", "warning")
                if os.path.exists(dest_file):
                    try:
                        os.remove(dest_file)
                    except:
                        pass
                continue

        self.log(f"所有镜像均下载失败: {last_error}", "error")
        return False

    def download_model(self, model_key: str, progress_callback: Callable = None) -> bool:
        """下载单个模型"""
        model_info = self.MODEL_FILES[model_key]
        model_dir = self.get_paddleocr_model_dir()

        os.makedirs(model_dir, exist_ok=True)

        urls = model_info["urls"]
        description = model_info["description"]

        self.log(f"开始下载 {description}...", "info")

        temp_file = os.path.join(tempfile.gettempdir(), f"paddleocr_model_{model_key}.tar")

        success = self.download_with_retry(urls, temp_file, description, progress_callback)

        if success:
            try:
                with tarfile.open(temp_file, 'r') as tar:
                    tar.extractall(model_dir)
                os.remove(temp_file)
                self.log(f"{description} 解压完成", "info")
                return True
            except Exception as e:
                self.log(f"{description} 解压失败: {str(e)}", "error")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False

        return False

    def get_pip_install_command(self, package: str) -> List[str]:
        """获取pip安装命令（使用国内镜像）"""
        python_path = self.get_python_exe_path() or sys.executable
        pip_path = self.get_pip_path()

        mirror = self.PIP_MIRRORS[self._current_mirror_index]

        if pip_path:
            cmd = [pip_path, "install", "--no-cache-dir", "-i", mirror]
        else:
            cmd = [python_path, "-m", "pip", "install", "--no-cache-dir", "-i", mirror]

        if "==" in package:
            cmd.append(package)
        else:
            cmd.append(f"{package}")

        return cmd

    def repair_dependency(self, module_name: str, user_confirm: Callable = None) -> bool:
        """修复单个依赖包"""
        package = self.PIP_PACKAGES.get(module_name, module_name)
        self.log(f"尝试安装依赖: {package}...", "info")

        if user_confirm:
            confirmed = user_confirm(f"需要安装 {package}，是否继续？")
            if not confirmed:
                self.log("用户取消安装", "warning")
                return False

        python_path = self.get_python_exe_path() or sys.executable

        for mirror in self.PIP_MIRRORS:
            mirror_name = mirror.split('/')[2]
            self.log(f"尝试使用 {mirror_name} 安装...", "info")

            try:
                cmd = [python_path, "-m", "pip", "install", "--no-cache-dir", "-i", mirror, package]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode == 0:
                    self.log(f"{package} 安装成功", "info")
                    return True
                else:
                    self.log(f"{mirror_name} 安装失败: {result.stderr[:200]}", "warning")

            except subprocess.TimeoutExpired:
                self.log(f"{mirror_name} 安装超时", "warning")
            except Exception as e:
                self.log(f"{mirror_name} 安装异常: {str(e)}", "warning")
                continue

        self.log(f"所有镜像均安装失败", "error")
        return False

    def repair_all_dependencies(self, user_confirm: Callable = None) -> bool:
        """安装所有缺失的依赖"""
        self.log("开始安装依赖包...", "info")

        installed_any = False
        failed_packages = []

        for dep in self.CORE_DEPENDENCIES:
            result, _ = self.check_dependency(dep)
            if result != CheckResult.OK:
                if self.repair_dependency(dep, user_confirm):
                    installed_any = True
                else:
                    failed_packages.append(dep)

        if failed_packages:
            self.log(f"以下依赖安装失败: {', '.join(failed_packages)}", "error")
            return False

        return True

    def repair_model(self, model_key: str, user_confirm: Callable = None) -> bool:
        """修复单个模型组"""
        model_info = self.MODEL_FILES[model_key]
        description = model_info["description"]

        if user_confirm:
            confirmed = user_confirm(f"需要重新下载 {description}（约30MB），是否继续？")
            if not confirmed:
                self.log("用户取消下载", "warning")
                return False

        return self.download_model(model_key)

    def repair_all_models(self, user_confirm: Callable = None) -> bool:
        """修复所有模型"""
        all_success = True

        for model_key in self.MODEL_FILES:
            result, _ = self.check_model_file(model_key)
            if result != CheckResult.OK:
                if not self.repair_model(model_key, user_confirm):
                    all_success = False

        return all_success

    def run_full_check(self) -> Dict[str, Dict]:
        """运行完整检查"""
        self.log("=" * 50)
        self.log("开始环境检查...")
        self.log("=" * 50)

        results = {
            "python_runtime": {"result": self.check_python_runtime()[0], "message": self.check_python_runtime()[1]},
            "dependencies": self.check_dependencies(),
            "ocr_models": self.check_ocr_models()
        }

        self.check_results = results
        return results

    def get_summary(self) -> Tuple[int, int, int]:
        """获取检查摘要"""
        ok_count = 0
        warning_count = 0
        error_count = 0

        if self.check_results.get("python_runtime", {}).get("result") == CheckResult.OK:
            ok_count += 1
        else:
            error_count += 1

        for dep, (result, _) in self.check_results.get("dependencies", {}).items():
            if result == CheckResult.OK:
                ok_count += 1
            else:
                warning_count += 1

        for model_key, (result, _) in self.check_results.get("ocr_models", {}).items():
            if result == CheckResult.OK:
                ok_count += 1
            else:
                error_count += 1

        return ok_count, warning_count, error_count

    def auto_repair(self, user_confirm: Callable = None) -> bool:
        """自动修复所有问题"""
        self.log("=" * 50)
        self.log("开始自动修复...")
        self.log("=" * 50)

        all_success = True

        python_result, _ = self.check_python_runtime()
        if python_result != CheckResult.OK:
            self.log("Python运行时损坏，请重新安装应用程序", "error")
            return False

        for dep, (result, _) in self.check_results.get("dependencies", {}).items():
            if result != CheckResult.OK:
                if not self.repair_dependency(dep, user_confirm):
                    all_success = False

        for model_key, (result, _) in self.check_results.get("ocr_models", {}).items():
            if result != CheckResult.OK:
                if not self.repair_model(model_key, user_confirm):
                    all_success = False

        return all_success

    def generate_report(self) -> str:
        """生成检查报告"""
        lines = []
        lines.append("=" * 50)
        lines.append("环境检查报告")
        lines.append("=" * 50)

        python_result = self.check_results.get("python_runtime", {})
        lines.append(f"\nPython运行时: {python_result.get('result', 'unknown').value} - {python_result.get('message', '')}")

        lines.append("\n依赖包:")
        for dep, (result, message) in self.check_results.get("dependencies", {}).items():
            lines.append(f"  {dep}: {result.value} - {message}")

        lines.append("\nOCR模型:")
        for model_key, (result, missing) in self.check_results.get("ocr_models", {}).items():
            model_desc = self.MODEL_FILES[model_key]["description"]
            lines.append(f"  {model_desc}: {result.value} (缺失: {', '.join(missing) if missing else '无'})")

        ok, warn, err = self.get_summary()
        lines.append(f"\n总计: {ok} 正常, {warn} 警告, {err} 错误")

        return "\n".join(lines)


def quick_check() -> Tuple[bool, str]:
    """快速检查入口"""
    checker = EnvironmentChecker()
    results = checker.run_full_check()

    ok, warn, err = checker.get_summary()

    if err > 0:
        return False, f"发现 {err} 个错误，需要修复"
    elif warn > 0:
        return True, f"发现 {warn} 个警告"
    else:
        return True, "环境检查通过"


if __name__ == "__main__":
    checker = EnvironmentChecker()

    print(checker.generate_report())

    ok, warn, err = checker.get_summary()

    if err > 0 or warn > 0:
        print("\n是否自动修复? (y/n)")
        choice = input().lower()
        if choice == 'y':
            checker.auto_repair()
