@echo off
:: Dodaje SonicCopyX Bridge u Windows Startup
:: Pokreni jednom kao Administrator

set SCRIPT_DIR=%~dp0
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP%\SonicCopyX_Bridge.bat

echo @echo off > "%SHORTCUT%"
echo cd /d "%SCRIPT_DIR%" >> "%SHORTCUT%"
echo call START_BRIDGE.bat >> "%SHORTCUT%"

echo [OK] Bridge dodan u Windows Startup.
echo      Pokrenuce se automatski kad se VPS restartuje.
echo.
echo Lokacija: %SHORTCUT%
pause
