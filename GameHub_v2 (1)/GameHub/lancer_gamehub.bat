@echo off
cd /d "%~dp0"
title GameHub v2.0
if not exist ".venv\Scripts\python.exe" (
    echo Creation de l'environnement Python...
    py -m venv .venv
    if errorlevel 1 python -m venv .venv
    if errorlevel 1 goto error
    echo Installation des dependances...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto error
)
echo Demarrage du suivi automatique des jeux...
start "GameHub - suivi auto" /min "%~dp0.venv\Scripts\python.exe" "%~dp0tracker.py"
echo Demarrage de GameHub dans le navigateur...
.venv\Scripts\python.exe -m streamlit run "%~dp0app.py"
if errorlevel 1 goto error
goto end
:error
echo.
echo Une erreur est arrivee. Verifie que Python est installe et que les dependances ont ete installees, puis relance ce fichier.
pause
:end
