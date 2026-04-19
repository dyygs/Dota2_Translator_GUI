# -*- coding: utf-8 -*-
"""
截图工具模块
"""

import mss
import mss.tools

class ScreenshotTool:
    """截图工具"""
    
    @staticmethod
    def capture_region(region):
        """
        截取指定区域
        
        Args:
            region: 区域字典 {'x': int, 'y': int, 'width': int, 'height': int}
            
        Returns:
            PIL.Image或None: 截图对象
        """
        try:
            with mss.mss() as sct:
                monitor = {
                    "left": region['x'],
                    "top": region['y'],
                    "width": region['width'],
                    "height": region['height']
                }
                screenshot = sct.grab(monitor)
                
                from PIL import Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                return img
        except Exception as e:
            print(f"截图失败: {e}")
            return None
    
    @staticmethod
    def capture_fullscreen():
        """
        截取全屏
        
        Returns:
            PIL.Image或None: 截图对象
        """
        try:
            with mss.mss() as sct:
                if len(sct.monitors) < 2:
                    print("未检测到显示器")
                    return None
                screenshot = sct.grab(sct.monitors[1])
                
                from PIL import Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                return img
        except Exception as e:
            print(f"全屏截图失败: {e}")
            return None
    
    @staticmethod
    def save_screenshot(image, filepath):
        """
        保存截图到文件
        
        Args:
            image: PIL.Image对象
            filepath: 保存路径
            
        Returns:
            bool: 是否成功
        """
        try:
            image.save(filepath)
            return True
        except Exception as e:
            print(f"保存截图失败: {e}")
            return False
