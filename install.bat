@echo off
rem Installs the Ilha cursors and applies one scheme. Arguments go straight to install.py (--variant white, --uninstall...).
python "%~dp0install.py" %*
pause
