@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-ce\Scripts\python.exe" (
  py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
  if errorlevel 1 (
    echo Instale Python 3.12 para Windows e Google Chrome. Depois tente novamente.
    pause
    exit /b 1
  )
  py -3 -m venv .venv-ce
  if errorlevel 1 goto falha
)
".venv-ce\Scripts\python.exe" -c "import playwright.sync_api, pdfplumber" >nul 2>&1
if errorlevel 1 (
  ".venv-ce\Scripts\python.exe" -m pip install -r requirements-ceara.txt
  if errorlevel 1 goto falha
)
".venv-ce\Scripts\python.exe" programa_ceara.py
if errorlevel 1 goto falha
exit /b 0
:falha
echo Nao foi possivel preparar ou abrir o programa. Confira Python e Internet.
pause
exit /b 1
