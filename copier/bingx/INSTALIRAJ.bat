@echo off
title SonicCopyX — Instalacija
color 0A
cd /d "%~dp0"

echo Instaliram potrebne pakete...
echo.
pip install MetaTrader5 requests

echo.
echo ============================================
echo   Instalacija gotova!
echo ============================================
echo.
echo Sljedeci koraci:
echo.
echo  1. Otvori config.py u Notepadu
echo  2. Unesi MT5 login, password, server
echo  3. Unesi BingX API Key i Secret Key
echo     (BingX - Account - API Management)
echo  4. Pokreni START.bat
echo.
echo VAZNO: Na BingX API-u ukljuci dozvolu za:
echo   [x] Perpetual Trading
echo   [ ] Withdrawal  <- OVO NIKAD NE UKLJUCUJ
echo.
pause
