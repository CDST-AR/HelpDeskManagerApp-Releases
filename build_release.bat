@echo off
setlocal ENABLEDELAYEDEXPANSION

rem =========================
rem Parámetros y defaults
rem =========================
if "%~1"=="" (
  echo Uso: build_release.bat VERSION [RELEASES_DIR] [--launcher] [--open]
  echo Ej:  build_release.bat 1.1.8 "C:\tmp\releases" --launcher --open
  exit /b 1
)
set "VERSION=%~1"
set "RELEASES_DIR=%~2"
if "%RELEASES_DIR%"=="" set "RELEASES_DIR=C:\tmp\releases"

set "FLAG_LAUNCHER=0"
set "FLAG_OPEN=0"
for %%A in (%3 %4 %5 %6) do (
  if /I "%%~A"=="--launcher" set "FLAG_LAUNCHER=1"
  if /I "%%~A"=="--open"     set "FLAG_OPEN=1"
)

rem =========================
rem Config del proyecto
rem =========================
set "APP_NAME=HelpDeskManagerApp"
set "MAIN_PY=Main.py"
set "ICON_FILE=ico.ico"
set "MAIN_EXE=%APP_NAME%.exe"
set "LAUNCHER_NAME=HelpDeskLauncher"
set "LAUNCHER_PY=launcher.py"

rem =========================
rem Detectar Python
rem =========================
set "PY="
py -3.11 -V >nul 2>&1 && (set "PY=py -3.11")
if not defined PY py -3.10 -V >nul 2>&1 && (set "PY=py -3.10")
if not defined PY python  -V >nul 2>&1 && (set "PY=python")
if not defined PY (
  echo ERROR: Python no encontrado. Instala Python 3.10+ o agrega 'py'/'python' al PATH.
  exit /b 1
)

rem =========================
rem Preparar directorios
rem =========================
if not exist "%RELEASES_DIR%" mkdir "%RELEASES_DIR%" 2>nul

rem =========================
rem Limpiar builds previos
rem =========================
echo [1/6] Limpiando build/dist...
if exist build rd /s /q build
if exist dist  rd /s /q dist
if exist __pycache__ rd /s /q __pycache__ 2>nul

rem =========================
rem Sanitizar entorno (backports)
rem =========================
echo [2/6] Quitando backports conflictivos...
%PY% -m pip uninstall -y pathlib  >nul 2>&1
%PY% -m pip uninstall -y pathlib2 >nul 2>&1

rem =========================
rem Asegurar PyInstaller
rem =========================
echo [3/6] Preparando PyInstaller...
%PY% -m pip install -U pip wheel setuptools >nul 2>&1
%PY% -m pip show pyinstaller >nul 2>&1 || %PY% -m pip install -U pyinstaller

rem =========================
rem Compilar APP (ONEDIR)
rem =========================
echo [4/6] Compilando %APP_NAME%...
if exist "%ICON_FILE%" (
  %PY% -m PyInstaller -y --name "%APP_NAME%" --noconsole --add-data "%ICON_FILE%;." "%MAIN_PY%"
) else (
  %PY% -m PyInstaller -y --name "%APP_NAME%" --noconsole "%MAIN_PY%"
)
if errorlevel 1 goto :fail

set "APP_DIST=%CD%\dist\%APP_NAME%"
if not exist "%APP_DIST%\%MAIN_EXE%" (
  echo ERROR: No se genero "%APP_DIST%\%MAIN_EXE%".
  goto :fail
)

rem =========================
rem Crear ZIP de la app
rem =========================
echo [5/6] Empaquetando ZIP...
set "ZIP_NAME=%APP_NAME%-%VERSION%.zip"
set "ZIP_PATH=%RELEASES_DIR%\%ZIP_NAME%"

rem Compress-Archive desde PowerShell (no afecta ExecutionPolicy por ser -Command)
powershell -NoProfile -Command "Compress-Archive -Path '%APP_DIST%\*' -DestinationPath '%ZIP_PATH%' -Force" || goto :fail

rem =========================
rem SHA256 y latest.json
rem =========================
echo [6/6] Calculando SHA-256 y escribiendo latest.json...
set "SHA256="
for /f "tokens=1 delims= " %%H in ('certutil -hashfile "%ZIP_PATH%" SHA256 ^| findstr /R "^[0-9A-F]"') do (
  set "SHA256=%%H"
  goto :havedigest
)
:havedigest
if not defined SHA256 (
  echo ERROR: No se pudo obtener SHA-256 de "%ZIP_PATH%".
  goto :fail
)

> "%RELEASES_DIR%\latest.json" (
  echo {
  echo   "version": "%VERSION%",
  echo   "filename": "%ZIP_NAME%",
  echo   "sha256": "%SHA256%",
  echo   "main_exe": "%MAIN_EXE%"
  echo }
)

echo.
echo ✅ Release generado:
echo    ZIP: "%ZIP_PATH%"
echo    SHA: %SHA256%
echo    JSON: "%RELEASES_DIR%\latest.json"
echo.

rem =========================
rem (Opcional) Compilar Launcher
rem =========================
if "%FLAG_LAUNCHER%"=="1" (
  echo [Extra] Compilando launcher...
  %PY% -m PyInstaller -y --name "%LAUNCHER_NAME%" --noconsole "%LAUNCHER_PY%"
  if errorlevel 1 goto :fail
  echo    Launcher: "%CD%\dist\%LAUNCHER_NAME%\%LAUNCHER_NAME%.exe"
  echo.
)

if "%FLAG_OPEN%"=="1" explorer "%RELEASES_DIR%"
exit /b 0

:fail
echo.
echo ❌ Ocurrio un error.
exit /b 1
    