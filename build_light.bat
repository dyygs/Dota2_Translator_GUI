@echo off
echo Building with virtual environment...
echo.

REM 创建虚拟环境（如果不存在）
if not exist build_env\Scripts\python.exe (
    echo Creating virtual environment...
    python -m venv build_env
)

REM 安装必要依赖
echo Installing dependencies...
build_env\Scripts\pip.exe install pyinstaller keyboard pyperclip pyautogui requests mss pillow

REM 打包 - 排除paddleocr等大库
echo Building...
build_env\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name Dota2Translator --distpath dist --add-data "src;src" --exclude-module=paddleocr --exclude-module=paddle --exclude-module=paddlepaddle --exclude-module=opencv-python --exclude-module=numpy --collect-all keyboard --collect-all pyperclip --collect-all pyautogui --collect-all requests --collect-all mss --collect-all PIL launcher.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete: dist\Dota2Translator.exe
echo.
pause
