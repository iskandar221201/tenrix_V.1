@echo off
setlocal enabledelayedexpansion

echo DEBUG: Installer starting...

set "INSTALL_DIR=%LOCALAPPDATA%\Tenrix"
set "REPO_URL=https://github.com/iskandar221201/tenrix_V.1.git"
set "PYTHON_VER=3.12.2"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"

echo DEBUG: Variables set. 
echo INSTALL_DIR: "!INSTALL_DIR!"
echo REPO_URL: "!REPO_URL!"
echo PYTHON_URL: "!PYTHON_URL!"
pause

echo [1/5] Checking for Git...
where git >nul 2>nul
if !ERRORLEVEL! == 0 (
    echo Git is already installed.
    goto :git_ready
)

echo Git not found. Downloading Git installer...
pause
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile '%TEMP%\git_setup.exe'"
echo Installing Git silently...
start /wait "" "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to install Git.
    pause
    exit /b 1
)
:: Refresh PATH for the current session to include Git
set "PATH=!PATH!;C:\Program Files\Git\cmd"
pause

:git_ready
echo Git is ready.

echo [2/5] Checking for Python 3.12...
echo DEBUG: Running 'where python'...
pause
where python >nul 2>nul
if !ERRORLEVEL! neq 0 (
    echo DEBUG: Python NOT in PATH.
    goto :download_python
)

echo DEBUG: Python found in PATH. Checking version...
python --version 2>nul | findstr /R "3\.12" >nul
if !ERRORLEVEL! == 0 (
    echo Python 3.12 is already installed.
    goto :python_ready
)

:download_python
echo Python 3.12 not found. Downloading Python...
echo DEBUG: Starting download...
pause
pause
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python_setup.exe'"
echo Installing Python silently (adding to PATH)...
start /wait "" "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to install Python.
    pause
    exit /b 1
)
:: Refresh environment variables for the current session
set "PATH=!PATH!;!LOCALAPPDATA!\Programs\Python\Python312;!LOCALAPPDATA!\Programs\Python\Python312\Scripts"
pause

:python_ready
echo Python is ready.

echo [3/5] Downloading Tenrix from GitHub...
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!"
cd /d "!INSTALL_DIR!"
pause

if exist ".git" (
    echo Repository exists. Fetching latest...
    git fetch origin
    git reset --hard origin/main
    if !ERRORLEVEL! neq 0 (
        git reset --hard origin/master
    )
    goto :repo_ready
)

echo Folder is not a git repository. Cleaning for fresh install...
del /q /s * >nul 2>nul
for /d %%x in (*) do rd /s /q "%%x" >nul 2>nul

echo Initializing local repository...
git clone "!REPO_URL!" .
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to clone repository. Check your internet.
    pause
    exit /b 1
)
pause

:repo_ready
echo [4/5] Installing dependencies...
cd /d "!INSTALL_DIR!"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [WARNING] Some dependencies failed to install.
    pause
)
pause

echo [5/5] Finalizing setup...
if not exist "!USERPROFILE!\.tenrix" mkdir "!USERPROFILE!\.tenrix"

echo.
echo ============================================================
echo   INSTALLATION SUCCESSFUL
echo ============================================================
echo.
echo Tenrix has been installed to: !INSTALL_DIR!
echo.
echo Please follow the Finish button in the installer.
echo.
pause
exit /b 0
