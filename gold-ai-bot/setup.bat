@echo off
REM ============================================================
REM  Gold AI Bot - jednokratni setup na Windows VPS-u
REM ============================================================
cd /d "%~dp0"

echo Kreiram virtualno okruzenje (.venv)...
python -m venv .venv
if errorlevel 1 (
    echo GRESKA: Python nije pronadjen. Instaliraj Python 3.11+ i obelezi "Add to PATH".
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Instaliram zavisnosti...
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    copy .env.example .env >nul
    echo Napravljen .env iz .env.example - POPUNI ga svojim podacima!
)

echo.
echo Gotovo. Koraci:
echo   1) Otvori .env i popuni MT5 podatke + ANTHROPIC_API_KEY
echo   2) U MT5 terminalu ukljuci AutoTrading i dodaj XAUUSD u Market Watch
echo   3) Pokreni run.bat
pause
