@echo off
:: Tenrix CLI Wrapper
:: Registered to PATH by tenrix-install.exe
:: Allows user to run: tenrix -v / tenrix -h / tenrix run

python "%LOCALAPPDATA%\Tenrix\main.py" %*
