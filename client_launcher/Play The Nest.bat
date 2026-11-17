@echo off
cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "%~dp0nest_launcher.pyw"
    exit /b 0
)

if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\bin\pythonw.exe" "%~dp0nest_launcher.pyw"
    exit /b 0
)

python "%~dp0nest_launcher.pyw"
if %errorlevel% neq 0 pause
