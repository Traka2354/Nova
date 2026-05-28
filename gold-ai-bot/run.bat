@echo off
REM ============================================================
REM  Gold AI Bot - pokretanje sa auto-restartom (Windows VPS)
REM  Ako bot padne, ceka 10s i ponovo ga pokrece. Zaustavi sa Ctrl+C.
REM ============================================================
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

:loop
echo [%date% %time%] Pokrecem Gold AI Bot...
%PY% bot.py
echo [%date% %time%] Bot se zaustavio (kod %errorlevel%). Restart za 10s...
timeout /t 10 /nobreak >nul
goto loop
