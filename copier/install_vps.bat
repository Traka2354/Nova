@echo off
title SonicCopyX — VPS Setup
color 0A

echo ============================================
echo   SonicCopyX Bridge — VPS Instalacija
echo ============================================
echo.

:: Provjeri Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python nije instaliran!
    echo     Preuzmi sa: https://www.python.org/downloads/
    echo     Obavezno klikni "Add Python to PATH" pri instalaciji.
    pause
    exit /b 1
)

echo [OK] Python pronadjen.

:: Instaliraj MetaTrader5 paket
echo.
echo [*] Instaliram MetaTrader5 Python paket...
pip install MetaTrader5 --quiet
if errorlevel 1 (
    echo [!] Greska pri instalaciji. Pokusaj rucno: pip install MetaTrader5
    pause
    exit /b 1
)
echo [OK] MetaTrader5 paket instaliran.

:: Provjeri da li MT5 terminal postoji
set MT5_PATH=%PROGRAMFILES%\MetaTrader 5\terminal64.exe
if not exist "%MT5_PATH%" (
    set MT5_PATH=%PROGRAMFILES(X86)%\MetaTrader 5\terminal64.exe
)
if not exist "%MT5_PATH%" (
    echo.
    echo [!] MT5 terminal nije pronadjen na standardnoj lokaciji.
    echo     Uvjeri se da je MT5 instaliran i prijavljen na tvoj account.
    echo.
)

echo.
echo ============================================
echo   Instalacija zavrsena!
echo ============================================
echo.
echo Sljedeci koraci:
echo.
echo   1. Otvori bridge.py u Notepadu
echo      Postavi MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
echo      (ili ostavi 0/"" ako je MT5 vec prijavljen)
echo.
echo   2. Instaliraj MT4 EA:
echo      Kopiraj SonicCopyX_Receiver_MT4.mq4 u:
echo      MT4 ^> File ^> Open Data Folder ^> MQL4\Experts\
echo.
echo   3. Pokreni bridge dvostrukim klikom na START_BRIDGE.bat
echo.
pause
