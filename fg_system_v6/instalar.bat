@echo off
title F^&G Sistema Contable — Instalador
color 0B
cls

echo.
echo  ╔════════════════════════════════════════════════════════╗
echo  ║                                                        ║
echo  ║          ██████╗  ^&  ██████╗                            ║
echo  ║         ██╔════╝     ██╔════╝                           ║
echo  ║         ██║          ██║                                ║
echo  ║         ██║          ██║                                ║
echo  ║         ██║          ██║                                ║
echo  ║         ╚═════════════════════                          ║
echo  ║                                                        ║
echo  ║        Sistema Contable — Instalador                   ║
echo  ║                                                        ║
echo  ╚════════════════════════════════════════════════════════╝
echo.

REM ── Ir a la carpeta donde está este .bat ──
cd /d "%~dp0"

REM ──────────────────────────────────
REM  1 / 4  Verificar Python
REM ──────────────────────────────────
echo  [1/4] Verificando Python...
python --version 2>NUL
if errorlevel 1 (
    echo.
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo  Por favor instale Python 3.9 o superior:
    echo      https://www.python.org/downloads/
    echo.
    echo  Asegurese de marcar "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python encontrado.
echo.

REM ──────────────────────────────────
REM  2 / 4  Crear entorno virtual
REM ──────────────────────────────────
echo  [2/4] Creando entorno virtual (venv)...
if exist "venv\Scripts\activate.bat" (
    echo  [OK] Entorno virtual ya existe — se reutiliza.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo  [ERROR] No se pudo crear el entorno virtual.
        echo  Posible causa: Python instalado sin el modulo venv.
        echo.
        pause
        exit /b 1
    )
    echo  [OK] Entorno virtual creado.
)
echo.

REM ──────────────────────────────────
REM  3 / 4  Activar venv
REM ──────────────────────────────────
echo  [3/4] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b 1
)
echo  [OK] Entorno virtual activo.
echo.

REM ──────────────────────────────────
REM  4 / 4  Instalar dependencias
REM ──────────────────────────────────
echo  [4/4] Instalando dependencias (requirements.txt)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudieron instalar las dependencias.
    echo  Verifique su conexion a internet e intente de nuevo.
    echo.
    pause
    exit /b 1
)
echo.

REM ──────────────────────────────────
REM  LISTO
REM ──────────────────────────────────
echo  ╔════════════════════════════════════════════════════════╗
echo  ║                                                        ║
echo  ║   INSTALACION COMPLETADA                               ║
echo  ║                                                        ║
echo  ║   Para iniciar el sistema ejecute:                     ║
echo  ║       iniciar_sistema.bat                              ║
echo  ║                                                        ║
echo  ║   Para compilar a .exe ejecute:                        ║
echo  ║       compilar.bat                                     ║
echo  ║                                                        ║
echo  ╚════════════════════════════════════════════════════════╝
echo.
pause
