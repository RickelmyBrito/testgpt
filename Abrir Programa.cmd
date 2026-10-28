@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
  if errorlevel 1 (
    echo Instale o Python 3.12 para Windows em https://www.python.org/downloads/windows/
    echo Depois abra este arquivo novamente. O Google Chrome tambem deve estar instalado.
    pause
    exit /b 1
  )
  py -3 -m venv .venv
  if errorlevel 1 goto falha
)
".venv\Scripts\python.exe" -c "import playwright.sync_api" >nul 2>&1
if errorlevel 1 (
  echo Preparando o programa na primeira abertura...
  ".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
  if errorlevel 1 goto falha
)
".venv\Scripts\python.exe" programa.py
if errorlevel 1 goto falha
exit /b 0
:falha
echo Nao foi possivel preparar ou abrir o programa. Verifique o Python e a conexao com a Internet.
pause
exit /b 1
