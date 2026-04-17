@echo off
echo Building lightweight package with minimal dependencies...
echo.

REM 创建临时虚拟环境
python -m venv build_env

REM 激活虚拟环境并安装最小依赖
call build_env\Scripts\activate.bat
pip install pyinstaller

REM 只安装GUI必需的依赖
pip install keyboard pyperclip pyautogui requests mss pillow

REM 使用虚拟环境中的Python打包
build_env\Scripts\python -m PyInstaller --noconfirm --onefile --windowed --name Dota2Translator --distpath dist src/dota2_translator_gui.py

REM 清理虚拟环境
deactivate
rmdir /s /q build_env

echo.
echo Build complete: dist\Dota2Translator.exe
echo.
pause
