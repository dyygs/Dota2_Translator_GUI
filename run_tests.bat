@echo off
chcp 65001 >nul
title Unit Tests

echo ============================================
echo   Running Unit Tests
echo ============================================
echo.

python run_tests.py

if errorlevel 1 (
    echo.
    echo [FAILED] Some tests failed!
) else (
    echo.
    echo [SUCCESS] All tests passed!
)

echo.
pause
