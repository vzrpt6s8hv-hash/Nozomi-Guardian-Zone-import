@echo off
REM Nozomi Guardian Zone Import Tool - Windows launcher
REM Creates an isolated virtual environment, installs this package and its
REM dependencies into it automatically, then launches the GUI.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo Python was not found on this system.
        echo Please install Python 3 from https://www.python.org/downloads/
        echo During install, make sure to check "Add python.exe to PATH".
        pause
        exit /b 1
    ) else (
        set PYLAUNCHER=py
    )
) else (
    set PYLAUNCHER=python
)

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    %PYLAUNCHER% -m venv .venv
)

if exist ".venv\Scripts\python.exe" (
    set RUNPY=.venv\Scripts\python.exe
) else (
    set RUNPY=%PYLAUNCHER%
)

echo [setup] Installing/upgrading the tool and its dependencies...
%RUNPY% -m pip install --quiet --upgrade pip
%RUNPY% -m pip install --quiet -e .

echo [setup] Launching Nozomi Guardian Zone Import Tool...
%RUNPY% -m nozomi_zone_import_tool

pause
