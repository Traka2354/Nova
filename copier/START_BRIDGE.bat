@echo off
title SonicCopyX Bridge — AKTIVAN
color 0A

:start
echo ============================================
echo   SonicCopyX Bridge — POKRENUT
echo   Zaustavi: zatvori ovaj prozor ili Ctrl+C
echo ============================================
echo.
python bridge.py
echo.
echo [!] Bridge se ugasio. Restartuje za 5 sekundi...
timeout /t 5 /nobreak >nul
goto start
