@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ===========================
REM CONFIG
REM ===========================
set APP_NAME=HelpDeskManagerApp

REM --- Versión por parámetro (ej: build_installer.bat 1.0.1)
set VERSION=%1
if "%VERSION%"=="" (
  echo Uso: build_installer.bat ^<VERSION^>
  echo Ejemplo: build_installer.bat 1.0.1
  echo.
  pause
  exit /b 1
)

set SPEC_FILE=Main.spec
set ISS_FILE=installer.iss
set ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe

REM ===========================
REM PRE-CHEQUEOS
REM ===========================
where pyinstaller >nul 2>&1 || (echo ERROR: PyInstaller no esta en PATH. ^(pip install pyinstaller^) & goto :fail)
if not exist "%ISCC_EXE%" (echo ERROR: No se encontro ISCC en "%ISCC_EXE%". Ajusta la ruta. & goto :fail)
if not exist "%SPEC_FILE%" (echo ERROR: No existe %SPEC_FILE%. & goto :fail)
if not exist "%ISS_FILE%"  (echo ERROR: No existe %ISS_FILE%. & goto :fail)

REM ===========================
REM LIMPIEZA
REM ===========================
echo [1/3] Limpiando compilaciones anteriores...
if exist build rd /s /q build
if exist dist rd /s /q dist

REM ===========================
REM PYINSTALLER (.spec)
REM ===========================
echo [2/3] Compilando con PyInstaller...
pyinstaller "%SPEC_FILE%"
if errorlevel 1 goto :fail

REM ===========================
REM INNO SETUP (ISCC)
REM ===========================
echo [3/3] Generando instalador con Inno Setup...
REM Pasamos la version al .iss via /D para que genere HelpDeskManagerApp_Setup_%VERSION%.exe
"%ISCC_EXE%" "/DMyAppVersion=%VERSION%" "%ISS_FILE%"
if errorlevel 1 goto :fail

REM ===========================
REM COMPROBAR SALIDA Y ABRIR CARPETA
REM ===========================
set ROOT_DIR=%~dp0
set OUTPUT_DIR=%ROOT_DIR%Output
set INSTALLER_NAME=%APP_NAME%_Setup_%VERSION%.exe
set INSTALLER_PATH=%OUTPUT_DIR%\%INSTALLER_NAME%

if exist "%INSTALLER_PATH%" (
  echo.
  echo ✅ Instalador generado correctamente:
  echo    "%INSTALLER_PATH%"
  echo.
  echo Abriendo carpeta Output...
  explorer "%OUTPUT_DIR%"
  echo.
  pause
  exit /b 0
) else (
  echo.
  echo ❌ No se encontro el instalador esperado:
  echo    "%INSTALLER_PATH%"
  echo Verifica en installer.iss que:
  echo   - OutputDir sea "Output" (por defecto)
  echo   - OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
  echo   - #define MyAppName "HelpDeskManagerApp"
  echo   - uses MyAppVersion del /DMyAppVersion (ver ejemplo abajo)
  echo.
  pause
  exit /b 1
)

:fail
echo.
echo ❌ Ocurrio un error durante la compilacion.
echo.
pause
exit /b 1
