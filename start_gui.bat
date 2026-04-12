@echo off
chcp 65001 >nul
title Dota 2 中文翻译器 - GUI版
echo ============================================
echo   Dota 2 中文→英文翻译器 (GUI版)
echo   现代化界面 + 系统托盘支持 + 严格模式
echo ============================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python并添加到PATH
    pause
    exit /b 1
)

echo [信息] 启动翻译器...
python src\dota2_translator_gui.py
pause
