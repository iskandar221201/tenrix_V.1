@echo off
setlocal enabledelayedexpansion

:: 1. Find Python
set "PY_CMD=python"
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "C:\Program Files\Python312\python.exe" (
        set "PY_CMD=C:\Program Files\Python312\python.exe"
    ) else if exist "C:\ProgramData\miniconda3\python.exe" (
        set "PY_CMD=C:\ProgramData\miniconda3\python.exe"
    )
)

:: 2. Find Tenrix main.py
set "TENRIX_DIR=%LOCALAPPDATA%\Tenrix"
if not exist "%TENRIX_DIR%\main.py" (
    echo [ERROR] Tenrix installation is incomplete.
    echo Please run the installer again.
    echo Folder: %TENRIX_DIR%
    pause
    exit /b 1
)

:: 3. Run
"%PY_CMD%" "%TENRIX_DIR%\main.py" %*
