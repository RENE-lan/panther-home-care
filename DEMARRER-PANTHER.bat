@echo off
chcp 65001 >nul
title Panther Home Care
cd /d "%~dp0"
color 0B
echo.
echo   ============================================================
echo                  PANTHER HOME CARE - Demarrage
echo   ============================================================
echo.

REM --- 1. Activer l'IA locale illimitee si Ollama est installe ---
where ollama >nul 2>nul
if %errorlevel%==0 (
    echo   [IA] Ollama detecte. Preparation du modele local...
    ollama pull llama3.2
    echo   [IA] Copilote ILLIMITE active ^(100%% local, sans cle^).
) else (
    echo   [IA] Ollama non installe : le Copilote repond aux questions
    echo        de l'agence + calculs. Pour un Copilote ILLIMITE, installez
    echo        Ollama une seule fois : https://ollama.com
)
echo.

REM --- 2. Base de donnees + donnees de demonstration ---
echo   [DB] Preparation de la base de donnees...
py manage.py migrate --skip-checks >nul 2>nul
py manage.py seed_demo >nul 2>nul
echo   [DB] Pret. Comptes : rene / panther123
echo.

REM --- 3. Ouvrir le navigateur puis lancer le serveur ---
echo   ============================================================
echo     Ouverture de http://127.0.0.1:8000/
echo     Connexion : rene / panther123
echo     ^(Laissez cette fenetre ouverte. Fermez-la pour arreter.^)
echo   ============================================================
echo.
start "" http://127.0.0.1:8000/
py manage.py runserver --skip-checks
pause
