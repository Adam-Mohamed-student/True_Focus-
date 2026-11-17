@echo off
echo ========================================
echo Building Doomscroll Blocker Executable
echo ========================================
echo.

REM Use the checked-in specification, including MediaPipe model resources.
cd /d "%~dp0"
echo.
echo Building executable with PyInstaller...
python -m PyInstaller --noconfirm --clean doomscroll.spec

REM Check if build succeeded
if %errorlevel% neq 0 (
    echo.
    echo ❌ Build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ✅ Executable created: dist\DoomscrollBlocker.exe
echo.
echo Press any key to test the executable...
pause > nul

REM Test the executable
start "" "dist\DoomscrollBlocker.exe"

echo.
echo If the app runs successfully, you can now create the installer.
pause
