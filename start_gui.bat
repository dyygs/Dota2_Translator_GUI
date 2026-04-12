@echo off
chcp 65001 >nul
title Dota 2 中文翻译器 - GUI版
echo ============================================
echo   Dota 2 中文→英文翻译器 (GUI版)
echo   现代化界面 + 系统托盘支持 + 严格模式
echo ============================================
echo.

set PYTHON_EXE=C:\Users\dy\AppData\Local\Programs\Python\Python314\python.exe

if not exist "%PYTHON_EXE%" (
    echo [错误] 未找到Python: %PYTHON_EXE%
    echo 请先安装Python
    pause
    exit /b 1
)

"%PYTHON_EXE%" src\dota2_translator_gui.py
pause
