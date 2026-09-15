@echo off
setlocal
cd /d "%~dp0"

echo Checking Python...
python --version
if errorlevel 1 exit /b 1

echo Checking PyInstaller...
python -m PyInstaller --version
if errorlevel 1 (
    echo PyInstaller is not installed.
    exit /b 1
)

echo.
echo ================================
echo Building AsoloAttendance.exe
echo ================================

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name AsoloAttendance ^
    --exclude-module pygments ^
    --exclude-module IPython ^
    --exclude-module pytest ^
    --exclude-module notebook ^
    --exclude-module setuptools ^
    --exclude-module pkg_resources ^
    "STAFF ATTENDANCE(GENERAL)KIVY.py"

if errorlevel 1 (
    echo.
    echo BUILD FAILED
    exit /b 1
)

if exist "asolo_config.json" (
    copy /Y "asolo_config.json" "dist\asolo_config.json" >nul
)

echo.
echo ================================
echo BUILD COMPLETE
echo ================================
echo dist\AsoloAttendance.exe

endlocal
