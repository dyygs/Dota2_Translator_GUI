@echo off
chcp 65001 >nul
title Dota 2 翻译器 - 打包工具

echo ============================================
echo   Dota 2 翻译器 - 打包工具
echo ============================================
echo.

REM 排除不需要的大库，减小体积
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "Dota2Translator" ^
    --distpath dist ^
    --exclude-module=pandas ^
    --exclude-module=torch ^
    --exclude-module=scipy ^
    --exclude-module=sklearn ^
    --exclude-module=matplotlib ^
    --exclude-module=tensorflow ^
    --exclude-module=keras ^
    --exclude-module=flask ^
    --exclude-module=django ^
    --exclude-module=plotly ^
    --exclude-module=seaborn ^
    src/dota2_translator_gui.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ✓ 打包完成
echo ============================================
echo.
echo 输出文件: dist\Dota2Translator.exe
echo.
pause
