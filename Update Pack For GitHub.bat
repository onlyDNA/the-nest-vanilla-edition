@echo off
title Update Pack Manifest for GitHub
cd /d "%~dp0"
python "%~dp0tools\build_pack_manifest.py"
pause
