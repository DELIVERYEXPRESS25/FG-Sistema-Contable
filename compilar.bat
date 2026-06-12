@echo off
title F^&G Sistema Contable — Compilador
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
echo  ║        Sistema Contable — Compilador .EXE              ║
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
echo.

REM ──────────────────────────────────
REM  Instalar PyInstaller si no esta
REM ──────────────────────────────────
echo  Verificando PyInstaller...
python -c "import PyInstaller" 2>NUL
if errorlevel 1 (
    echo  Instalando PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo.
        echo  [ERROR] No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)
echo  [OK] PyInstaller disponible.
echo.

REM ──────────────────────────────────
REM  Verificar icono .ico
REM ──────────────────────────────────
echo  Verificando icono...
set ICON_PARAM=
for %%f in (*.ico) do (
    set ICON_PARAM=--icon=%%f
    echo  [OK] Icono encontrado: %%f
    goto ICON_DONE
)
echo  [AVISO] No se encontro .ico — compile.py generara uno automaticamente.
:ICON_DONE
echo.

REM ──────────────────────────────────
REM  Compilar con compile.py
REM ──────────────────────────────────
echo  ════════════════════════════════════════════════════════
echo   Compilando... esto puede tardar unos minutos.
echo  ════════════════════════════════════════════════════════
echo.

python compile.py

if errorlevel 1 (
    echo.
    echo  [ERROR] La compilacion fallo.
    echo.
    echo  Consejos:
    echo    - Cierre cualquier otra instancia del sistema.
    echo    - Ejecute este archivo como Administrador.
    echo    - Revise los mensajes de error arriba.
    echo.
    pause
    exit /b 1
)

echo.
echo  ╔════════════════════════════════════════════════════════╗
echo  ║                                                        ║
echo  ║   COMPILACION EXITOSA                                  ║
echo  ║                                                        ║
echo  ║   Resultado:  dist\FG_Sistema_Contable\               ║
echo  ║                  FG_Sistema_Contable.exe               ║
echo  ║                                                        ║
echo  ║   El .exe incluye todo lo necesario.                   ║
echo  ║   El navegador se abre automaticamente al iniciarlo.   ║
echo  ║   Para cerrar use "Apagar Servidor" en la web.        ║
echo  ║                                                        ║
echo  ╚════════════════════════════════════════════════════════╝
echo.
pause
