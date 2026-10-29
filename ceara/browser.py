"""Open installed Chrome as a separate process; attach only after manual login.

The debugging endpoint is local only. Never open the user's personal profile,
copy cookies, change webdriver properties, or disable browser protections.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import ProxyHandler, build_opener


def find_chrome():
    candidates = []
    if sys.platform == 'win32':
        for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            if os.environ.get(key):
                candidates.append(Path(os.environ[key]) / 'Google/Chrome/Application/chrome.exe')
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe', 0, winreg.KEY_READ | view) as key:
                            candidates.append(Path(winreg.QueryValue(key, None).strip('"')))
                    except OSError:
                        pass
        except ImportError:
            pass
    for name in ('google-chrome', 'chrome', 'chromium', 'chromium-browser'):
        path = shutil.which(name)
        if path:
            candidates.append(Path(path))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise ValueError('Google Chrome não encontrado. Instale o Chrome e abra o programa novamente.')


def launch_args(executable, profile, port, url):
    if not 1024 <= port <= 65535:
        raise ValueError('Porta local inválida.')
    return [executable, '--remote-debugging-address=127.0.0.1',
            f'--remote-debugging-port={port}', f'--user-data-dir={profile}',
            '--start-maximized', '--no-first-run', '--no-default-browser-check', url]


def local_endpoint(data, port):
    endpoint = data.get('webSocketDebuggerUrl', '')
    parsed = urlparse(endpoint)
    if (parsed.scheme != 'ws' or parsed.hostname != '127.0.0.1' or parsed.port != port
            or parsed.username or parsed.password
            or not re.fullmatch(r'/devtools/browser/[a-zA-Z0-9-]+', parsed.path)
            or parsed.query or parsed.fragment):
        raise ValueError('O Chrome retornou uma conexão local inválida.')
    return endpoint


class ManualChrome:
    def __init__(self):
        self.process = None
        self.profile = None
        self.port = None

    def open(self, url):
        import socket
        executable = find_chrome()
        self.profile = tempfile.mkdtemp(prefix='plano-ce-chrome-')
        # A non-default profile is required by current Chrome for local debugging.
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            self.port = listener.getsockname()[1]
        try:
            self.process = subprocess.Popen(launch_args(executable, self.profile, self.port, url),
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self.close()
            raise ValueError('Não foi possível abrir o Chrome instalado.') from None

    def running(self):
        return self.process is not None and self.process.poll() is None

    def endpoint(self, stop, timeout=15):
        opener = build_opener(ProxyHandler({}))  # Loopback must not go through an external proxy.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if stop.is_set():
                return None
            if not self.running():
                raise ValueError('O Chrome foi fechado. Clique em Iniciar para abrir outra sessão.')
            try:
                with opener.open(f'http://127.0.0.1:{self.port}/json/version', timeout=1) as response:
                    data = json.loads(response.read(65536))
                return local_endpoint(data, self.port)
            except (OSError, json.JSONDecodeError):
                stop.wait(.2)
        raise ValueError('Não consegui conectar ao Chrome local. Feche esta sessão e tente novamente.')

    def close(self):
        # Only terminate the process started here, never other Chrome windows.
        if self.running():
            if sys.platform == 'win32':
                # Gracefully close only windows owned by this Chrome process.
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.WinDLL('user32', use_last_error=True)
                callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
                user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
                @callback_type
                def close_window(hwnd, unused):
                    owner = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                    if owner.value == self.process.pid:
                        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                    return True
                user32.EnumWindows(close_window, 0)
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            if self.running():
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.profile:
            # Chrome may hold files briefly during shutdown, especially on Windows.
            for _ in range(10):
                try:
                    shutil.rmtree(self.profile)
                    self.profile = None
                    break
                except FileNotFoundError:
                    self.profile = None
                    break
                except OSError:
                    time.sleep(.1)
