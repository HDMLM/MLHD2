cd /d "%~dp0.."
pyinstaller "installer.spec"
move "%cd%\dist\MLHD2-Launcher.exe" "%cd%\tools\Built\MLHD2-Launcher.exe"
rmdir /s /q "%cd%\dist"
rmdir /s /q "%cd%\build"
@echo off
cls
echo Build complete. The built executable is located at: %cd%\tools\Built\MLHD2-Launcher.exe
pause

:: This batch script builds the MLHD2 Launcher executable using PyInstaller.
:: It should be run from the 'tools' directory.
:: The built executable will be placed in the 'tools\Built' directory.
:: Ensure you have PyInstaller installed in your Python environment.
:: Credits: MLHD2 Launcher build script by the MLHD2 development team.