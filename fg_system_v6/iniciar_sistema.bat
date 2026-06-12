@echo off
title F^&G Sistema Contable
color 0B
cls

REM ── Ir a la carpeta donde está este .bat ──
cd /d "%~dp0"

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
echo  ║        Sistema Contable — Iniciando...                 ║
echo  ║                                                        ║
echo  ╚════════════════════════════════════════════════════════╝
echo.

REM ──────────────────────────────────
REM  Verificar que el venv existe
REM ──────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Entorno virtual no encontrado.
    echo.
    echo  Ejecute primero:  instalar.bat
    echo.
    pause
    exit /b 1
)

REM ──────────────────────────────────
REM  Activar venv
REM ──────────────────────────────────
echo  Activando entorno virtual...
call venv\Scripts\activate.bat

REM ──────────────────────────────────
REM  Verificar que Flask esta instalado
REM ──────────────────────────────────
python -c "import flask" 2>NUL
if errorlevel 1 (
    echo.
    echo  [AVISO] Flask no encontrado. Instalando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

REM ──────────────────────────────────
REM  Iniciar servidor
REM ──────────────────────────────────
echo.
echo  Iniciando servidor en http://127.0.0.1:5000
echo  El navegador se abrira automaticamente.
echo.
echo  Para cerrar el sistema use el boton "Apagar Servidor"
echo  dentro de la aplicacion.
echo.
echo  ─────────────────────────────────────────────────────

python main.py

echo.
echo  ─────────────────────────────────────────────────────
echo  Servidor cerrado.
echo.
pause
