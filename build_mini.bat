@echo off
title Dota2 Translator Build Tool

echo ============================================
echo   Dota2 Translator - Launcher Builder
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

REM Clean old builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building...
echo.

python -m PyInstaller --noconfirm --onefile --windowed --name "Dota2Translator" --distpath dist --exclude-module=paddleocr --exclude-module=paddle --exclude-module=paddlepaddle --exclude-module=opencv --exclude-module=cv2 --exclude-module=numpy --exclude-module=PIL --exclude-module=keyboard --exclude-module=pyperclip --exclude-module=pyautogui --exclude-module=requests --exclude-module=mss --exclude-module=torch --exclude-module=tensorflow --exclude-module=scipy --exclude-module=sklearn --exclude-module=pandas --exclude-module=matplotlib --add-data "src;src" launcher.py

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
echo Output: dist\Dota2Translator.exe

for %%A in (dist\Dota2Translator.exe) do (
    set size=%%~zA
)
echo Size: %size% bytes
echo.
pause
