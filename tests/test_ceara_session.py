"""Local-only browser session regression; no government login or credentials."""
import json
import shutil
import threading
import unittest
from unittest.mock import MagicMock, patch
from ceara.browser import ManualChrome, launch_args, local_endpoint
from ceara.engine import Engine, PORTAL


class SessionTests(unittest.TestCase):
    def engine(self, log=lambda x:None):
        return Engine({}, [], log, threading.Event(), threading.Event())

    def test_launch_uses_installed_chrome_and_separate_profile(self):
        args = launch_args('C:/Google/chrome.exe', 'C:/Temp/Perfil com espaços', 32123, PORTAL)
        self.assertIn('--remote-debugging-address=127.0.0.1', args)
        self.assertIn('--remote-debugging-port=32123', args)
        self.assertIn('--user-data-dir=C:/Temp/Perfil com espaços', args)
        self.assertEqual(args[-1], PORTAL)
        self.assertFalse(any(x in ' '.join(args) for x in ('--enable-automation','--disable-web-security','AutomationControlled')))
        with self.assertRaises(ValueError):
            launch_args('chrome','profile',80,PORTAL)

    def test_debug_endpoint_only_accepts_own_local_port(self):
        good='ws://127.0.0.1:32123/devtools/browser/abc-123'
        self.assertEqual(local_endpoint({'webSocketDebuggerUrl':good},32123),good)
        for bad in [good.replace('127.0.0.1','example.com'), good.replace('32123','32124'),
                    good.replace('ws:','wss:'),good+'?token=x', good.replace('127.0.0.1','user@127.0.0.1')]:
            with self.assertRaises(ValueError):
                local_endpoint({'webSocketDebuggerUrl':bad},32123)

    def test_connect_only_after_continue_and_can_retry_incomplete_login(self):
        events=[]
        e=self.engine()
        manual=MagicMock()
        manual.running.return_value=True
        manual.endpoint.return_value='ws://127.0.0.1:32123/devtools/browser/test'
        sdk=MagicMock()
        sdk.__enter__.return_value=sdk
        browser=MagicMock()
        sdk.chromium.connect_over_cdp.side_effect=lambda *a,**k:events.append('connect') or browser
        e.authenticated_page=MagicMock(side_effect=[None,MagicMock()])
        def log(msg):
            if msg.startswith('Chrome aberto'):
                self.assertNotIn('connect',events)
                events.append('manual login')
                e.resume.set()
            elif msg.startswith('Login ainda'):
                events.append('retry')
                e.resume.set()
        e.log=log
        e.teaching_plan=lambda page:events.append('fill') or e.stop.set()
        with patch('ceara.browser.ManualChrome',return_value=manual), patch('playwright.sync_api.sync_playwright',return_value=sdk):
            e.run()
        self.assertEqual(events,['manual login','connect','retry','fill'])
        sdk.chromium.connect_over_cdp.assert_called_once()
        sdk.chromium.launch.assert_not_called()
        browser.new_context.assert_not_called()
        manual.close.assert_called_once()

    def test_stop_before_launch_and_no_close_of_personal_browser(self):
        e=self.engine()
        e.stop.set()
        with patch('ceara.browser.ManualChrome') as cls:
            e.run()
        cls.return_value.open.assert_not_called()
        cls.return_value.close.assert_called_once()

    def test_authenticated_tab_selection_rejects_login_screen_and_ambiguity(self):
        e=self.engine()
        def page(url,ready):
            p=MagicMock(url=url)
            p.get_by_text.return_value.count.return_value=int(ready)
            return p
        browser=MagicMock()
        login=page('https://sso.acesso.gov.br/login',False)
        landing=page(PORTAL,False)
        portal=page(PORTAL+'index',True)
        browser.contexts=[MagicMock(pages=[login,landing])]
        self.assertIsNone(e.authenticated_page(browser))
        browser.contexts[0].pages.append(portal)
        self.assertIs(e.authenticated_page(browser),portal)
        browser.contexts[0].pages.append(page(PORTAL+'other',True))
        with self.assertRaises(ValueError):
            e.authenticated_page(browser)


class ExistingBrowserTests(unittest.TestCase):
    def test_attach_reuses_existing_tab_and_session(self):
        from playwright.sync_api import sync_playwright
        import sys
        executable=shutil.which('chromium') or None
        if sys.platform!='win32' and not executable:
            self.skipTest('Chrome/Chromium não instalado.')
        original=launch_args
        def local_args(exe,profile,port,url):
            args=original(exe,profile,port,url)
            if sys.platform!='win32':
                args[1:1]=['--headless=new','--no-sandbox']
            return args
        chrome=ManualChrome()
        try:
            with patch('ceara.browser.launch_args',side_effect=local_args):
                chrome.open('about:blank')
            endpoint=chrome.endpoint(threading.Event())
            with sync_playwright() as sdk:
                browser=sdk.chromium.connect_over_cdp(endpoint)
                self.assertEqual(len(browser.contexts),1)
                context=browser.contexts[0]
                self.assertEqual(len(context.pages),1)
                context.add_cookies([{'name':'test-session','value':'synthetic-only','url':PORTAL}])
                context.pages[0].set_content('<title>Portal de teste local</title><h1>Sessão existente</h1>')
                context.pages[0].evaluate('window.manualSessionMarker=42')
            # Stopping Playwright disconnects, rather than closing the externally started Chrome.
            self.assertTrue(chrome.running())
            with sync_playwright() as sdk:
                browser=sdk.chromium.connect_over_cdp(endpoint)
                context=browser.contexts[0]
                self.assertEqual(len(context.pages),1)
                self.assertEqual(context.pages[0].title(),'Portal de teste local')
                self.assertEqual(context.pages[0].evaluate('window.manualSessionMarker'),42)
                self.assertEqual(context.cookies(PORTAL)[0]['value'],'synthetic-only')
                self.assertIsNone(context.pages[0].viewport_size)
        finally:
            chrome.close()
        self.assertFalse(chrome.running())
        self.assertIsNone(chrome.profile)
