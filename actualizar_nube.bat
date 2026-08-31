@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ======================================================
echo  ACTUALIZADOR PkmPro - Export + Git Push (Un clic)
echo  Carpeta: %CD%
echo ======================================================
echo.

:: 1. Verificar Python
where python >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] No se encontro Python. Instala Python y marca "Add to PATH"
        pause
        exit /b 1
    )
)

:: 2. Exportar SQL Server -> SQLite
echo [1/4] Exportando SQL Server -> pogo_data.sqlite ...
%PYTHON_CMD% export_to_sqlite.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Fallo export_to_sqlite.py. Revisa que SQL Server LOCALHOST\SQLEXPRESS este corriendo.
    pause
    exit /b 1
)
echo [OK] SQLite generado.
echo.

:: 3. Verificar Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Git. Instala Git for Windows
    pause
    exit /b 1
)

:: 4. Pedir mensaje de commit
set /p COMMIT_MSG=Escribe mensaje para el commit (Enter = usa fecha/hora): 
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=actualizacion datos %date% %time%
)

echo.
echo [2/4] Agregando archivos a Git ...
git add -f pogo_data.sqlite
git add app.py data_loader.py team_builder.py custom_cup.py battle_engine.py moves.py export_to_sqlite.py update_spanish_move_names.py README.md requirements.txt requirements-local.txt sql/
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] git add fallo, continuo...
)

echo.
echo [3/4] Haciendo commit: "%COMMIT_MSG%"
git commit -m "%COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo [INFO] Nada nuevo que commitear o ya commiteado. Sigo con push...
)

echo.
echo [4/4] Subiendo a GitHub (origin main) ...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push rechazado. Posible causa: te faltan cambios del remoto.
    echo Intenta: git pull origin main --allow-unrelated-histories
    echo Y luego vuelve a ejecutar este .bat
    pause
    exit /b 1
)

echo.
echo ======================================================
echo  LISTO! SQLite actualizado y subido a GitHub
echo  Streamlit Cloud se actualizara solo en 1-2 min
echo ======================================================
pause
