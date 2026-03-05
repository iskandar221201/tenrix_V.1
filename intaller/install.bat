@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Tenrix Installer Script (install.bat)
:: ============================================================
:: This script handles:
::   1. Checking/Installing Git
::   2. Checking/Installing Python 3.12
::   3. Cloning the Tenrix repository
::   4. Installing dependencies
::   5. Setting up GTK3 Runtime
:: ============================================================

set "INSTALL_DIR=%LOCALAPPDATA%\Tenrix"
set "REPO_URL=https://github.com/iskandar221201/tenrix_V.1.git"
set "PYTHON_VER=3.12.2"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"

echo [1/5] Checking for Git...
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Git not found. Downloading Git installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile '%TEMP%\git_setup.exe'"
    echo Installing Git silently...
    start /wait "" "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Git.
        exit /b 1
    )
) else (
    echo Git is already installed.
)

echo [2/5] Checking for Python 3.12...
python --version 2>nul | findstr /R "3\.12" >nul
if %ERRORLEVEL% neq 0 (
    echo Python 3.12 not found. Downloading Python...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python_setup.exe'"
    echo Installing Python silently (adding to PATH)...
    start /wait "" "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install Python.
        exit /b 1
    )
    :: Refresh environment variables for the current session
    set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
) else (
    echo Python 3.12 is already installed.
)

echo [3/5] Downloading Tenrix from GitHub...
if exist "%INSTALL_DIR%" (
    echo Repository already exists. Updating...
    cd /d "%INSTALL_DIR%"
    git pull
) else (
    echo Cloning repository...
    git clone "%REPO_URL%" "%INSTALL_DIR%"
)

echo [4/5] Installing dependencies...
cd /d "%INSTALL_DIR%"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo WARNING: Some dependencies failed to install.
)

echo [5/5] Finalizing setup...
:: Create local folder for logs/data if needed
if not exist "%USERPROFILE%\.tenrix" mkdir "%USERPROFILE%\.tenrix"

echo Installation complete! 
echo You can now close this window and follow the Finish button in the installer.
exit /b 0
