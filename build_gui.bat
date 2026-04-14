@echo off
chcp 65001 >nul
title Dota 2 翻译器 - GUI版打包工具

echo ============================================
echo   Dota 2 中文翻译器 - GUI版打包工具
echo ============================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python并添加到PATH
    pause
    exit /b 1
)

REM 检查 PyInstaller 是否安装
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [信息] 正在安装PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] 安装PyInstaller失败！
        pause
        exit /b 1
    )
)

echo [信息] 开始打包GUI版本...
echo.

REM 清理旧的构建文件
if exist build (
    echo [清理] 删除旧 build 目录...
    rmdir /s /q build
)
if exist dist (
    echo [清理] 删除旧 dist 目录...
    rmdir /s /q dist
)

REM 执行打包 - GUI版本使用--windowed隐藏控制台
echo [打包] 正在生成 GUI 版本 EXE 文件...
echo.

python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "Dota2Translator" ^
    --icon=NONE ^
    --add-data "src\1.png;." ^
    --add-data "src\词汇表.py;." ^
    --runtime-hook=runtime_hook.py ^
    --collect-all=paddleocr ^
    --collect-all=paddle ^
    --collect-all=Cython ^
    --collect-all=skimage ^
    --collect-all=shapely ^
    --collect-all=imgaug ^
    --collect-all=imageio ^
    --collect-all=lmdb ^
    --collect-all=lxml ^
    --collect-all=opencv ^
    --collect-all=PIL ^
    --collect-all=tqdm ^
    --collect-all=numpy ^
    --collect-all=pyclipper ^
    --collect-all=rapidfuzz ^
    --collect-all=attrdict ^
    --collect-all=beautifulsoup4 ^
    --collect-all=fonttools ^
    --collect-all=fire ^
    --collect-all=premailer ^
    --collect-all=openpyxl ^
    --collect-all=python-docx ^
    --collect-all=pyyaml ^
    --collect-all=visualdl ^
    --collect-all=imghdr ^
    --hidden-import=shutil ^
    --hidden-import=io ^
    --hidden-import=packaging ^
    --hidden-import=collections.abc ^
    --hidden-import=contextlib ^
    --hidden-import=dataclasses ^
    --hidden-import=imghdr ^
    --hidden-import=multiprocessing ^
    src/dota2_translator_gui.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ✓ GUI版本打包成功！
echo ============================================
echo.
echo 输出文件: dist\Dota2Translator.exe
echo.
echo 特性:
echo   • 现代化GUI界面
echo   • 可最小化到系统托盘
echo   • 实时日志显示
echo   • 一键设置触发键
echo   • 严格模式悬浮窗
echo   • 运行时自动下载OCR模型
echo.
pause
