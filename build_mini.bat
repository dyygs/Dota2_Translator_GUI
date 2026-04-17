@echo off
chcp 65001 >nul
title Dota 2 翻译器 - 启动器打包工具

echo ============================================
echo   Dota 2 翻译器 - 启动器打包工具 (轻量版)
echo ============================================
echo.
echo 说明：
echo   - 只打包 launcher.py（不包含运行时依赖）
echo   - 启动器会自动检测/下载/安装 Python 和依赖
echo   - 最终 exe 大小约 10MB
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11.9
    pause
    exit /b 1
)

REM 清理旧的构建文件
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo 开始打包...
echo.

python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "Dota2Translator" ^
    --distpath dist ^
    --exclude-module=paddleocr ^
    --exclude-module=paddle ^
    --exclude-module=paddlepaddle ^
    --exclude-module=opencv ^
    --exclude-module=cv2 ^
    --exclude-module=numpy ^
    --exclude-module=PIL ^
    --exclude-module=keyboard ^
    --exclude-module=pyperclip ^
    --exclude-module=pyautogui ^
    --exclude-module=requests ^
    --exclude-module=mss ^
    --exclude-module=torch ^
    --exclude-module=tensorflow ^
    --exclude-module=scipy ^
    --exclude-module=sklearn ^
    --exclude-module=pandas ^
    --exclude-module=matplotlib ^
    --add-data "src;src" ^
    launcher.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ✓ 打包完成！
echo ============================================
echo.
echo 输出文件: dist\Dota2Translator.exe

REM 显示文件大小
for %%A in (dist\Dota2Translator.exe) do (
    set size=%%~zA
)
echo 文件大小: %size% bytes
echo.
pause
