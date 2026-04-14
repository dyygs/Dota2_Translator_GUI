import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

def fix_paddle_paths():
    temp_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else None
    if temp_dir:
        paddleocr_tools = os.path.join(temp_dir, 'paddleocr', 'tools')
        os.makedirs(paddleocr_tools, exist_ok=True)
        init_file = os.path.join(paddleocr_tools, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('')

        cython_utility = os.path.join(temp_dir, 'Cython', 'Utility')
        os.makedirs(cython_utility, exist_ok=True)

import types

imghdr = types.ModuleType('imghdr')

from PIL import Image

def test_jpeg(h, f):
    if h[:2] == b'\xff\xd8':
        return 'jpeg'

def test_png(h, f):
    if h[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'

def test_gif(h, f):
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'

def test_bmp(h, f):
    if h[:2] == b'BM':
        return 'bmp'

def test_tiff(h, f):
    if h[:2] in (b'II', b'MM'):
        return 'tiff'

def test_webp(h, f):
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'

imghdr.tests = [test_jpeg, test_png, test_gif, test_bmp, test_tiff, test_webp]

def what(f, h=None):
    if h is None:
        try:
            with Image.open(f) as img:
                fmt = img.format
                if fmt:
                    return fmt.lower()
        except:
            pass
        return None
    else:
        for test in imghdr.tests:
            res = test(h, None)
            if res:
                return res
        return None

imghdr.what = what

sys.modules['imghdr'] = imghdr

fix_paddle_paths()
