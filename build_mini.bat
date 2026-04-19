@echo off
title Dota2 Translator Build Tool

echo ============================================
echo   Dota2 Translator - Launcher Builder (Modular)
echo ============================================
echo.

REM Check Python (use D: drive Python)
set PYTHON_EXE=D:\Dota2Translator\python\python.exe
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at D:\Dota2Translator\python\python.exe
    pause
    exit /b 1
)
echo Using Python: %PYTHON_EXE%

REM Read version from version.py
for /f "tokens=2 delims==" %%v in ('findstr "VERSION" src\core\version.py') do (
    set VERSION=%%v
)
set VERSION=%VERSION:"=%
echo Version: %VERSION%

REM Clean old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building with modular structure...
echo.

"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name "Dota2Translator_v%VERSION%" --distpath dist --exclude-module=paddleocr --exclude-module=paddle --exclude-module=paddlepaddle --exclude-module=opencv --exclude-module=cv2 --exclude-module=numpy --exclude-module=PIL --exclude-module=keyboard --exclude-module=pyperclip --exclude-module=pyautogui --exclude-module=requests --exclude-module=mss --exclude-module=torch --exclude-module=tensorflow --exclude-module=scipy --exclude-module=sklearn --exclude-module=pandas --exclude-module=matplotlib --add-data "src;src" launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   [OK] Build Complete!
echo ============================================
echo.
echo Output: dist\Dota2Translator_v%VERSION%.exe

for %%A in (dist\Dota2Translator_v%VERSION%.exe) do (
    set size=%%~zA
)
echo Size: %size% bytes
echo.
pause
