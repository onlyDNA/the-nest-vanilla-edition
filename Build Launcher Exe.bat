@echo off
title Build Standalone Launcher EXE
cd /d "%~dp0client_launcher"
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "The Nest Launcher" ^
  --icon "%~dp0client_launcher\panel_icon.ico" ^
  --add-data "%~dp0client_launcher\launcher_config.json;." ^
  --add-data "%~dp0client_launcher\nest_logo.png;." ^
  --add-data "%~dp0client_launcher\taskbar_icon.png;." ^
  --add-data "%~dp0client_launcher\panel_icon.ico;." ^
  --distpath "%~dp0release" ^
  --workpath "%~dp0scratch\pyi_build" ^
  --specpath "%~dp0scratch\pyi_build" ^
  "nest_launcher.pyw"
echo.
echo Built: %~dp0release\The Nest Launcher.exe
pause
