@echo off
title SonicCopyX — MT5 to BingX AKTIVAN
color 0A
cd /d "%~dp0"

:start
echo ============================================
echo   SonicCopyX MT5 → BingX Copier
echo   Zaustavi: Ctrl+C ili zatvori prozor
echo ============================================
echo.
python copier.py
echo.
echo [!] Copier se ugasio. Restartuje za 5s...
timeout /t 5 /nobreak >nul
goto start
