@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%USERPROFILE%\.pyenv\pyenv-win\versions\3.10.11\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

if "%~1"=="" (
    "%PYTHON_EXE%" "%~dp0UnrealRootNodeReadTimecode.py"
) else (
    "%PYTHON_EXE%" "%~dp0UnrealRootNodeReadTimecode.py" "%~1"
)

echo.
pause
