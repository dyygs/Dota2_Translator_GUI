@echo off
chcp 65001 >nul
title Dota 2 翻译器 - GUI版打包工具
echo ============================================
echo   Dota 2 中文翻译器 - GUI版打包工具
echo ============================================
echo.

REM 检查 PyInstaller 是否安装
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 PyInstaller，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] 安装失败！请手动执行: pip install pyinstaller
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

pyinstaller --noconfirm --onefile --windowed ^
    --name "Dota2_Translator_GUI" ^
    --icon=NONE ^
    --add-data "config.example.json;." ^
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
echo 输出文件: dist\Dota2_Translator_GUI.exe
echo.
echo 特性:
echo   • 现代化GUI界面
echo   • 可最小化到系统托盘
echo   • 实时日志显示
echo   • 一键设置触发键
echo.
pause
