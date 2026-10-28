"""Build a portable Windows executable; Chrome is supplied by the user's PC."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'win32':
    raise SystemExit('O executável Windows deve ser compilado no Windows.')
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
           '--name', 'RegistroDeAulas', '--collect-all', 'playwright']
for name in ('portal.js', 'confirmation.js', 'wizard.js', 'fill.js', 'batch.js'):
    command += ['--add-data', str(ROOT / name) + os.pathsep + '.']
command += ['--add-data', str(ROOT / 'desktop' / 'navigation.js') + os.pathsep + 'desktop', str(ROOT / 'programa.py')]
subprocess.run(command, cwd=ROOT, check=True)
