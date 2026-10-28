"""Real Playwright regression: no network, portal login, or saved credentials."""
import html
import os
import sys
import threading
import unittest

from desktop.engine import AutomationError, locate_card_action, navigation_source

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'Instale requirements-desktop.txt para testar o Playwright real.')
class PlaywrightNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = sync_playwright().start()
        options = {'headless': True}
        if sys.platform == 'win32':
            options['channel'] = 'chrome'
        else:
            options.update(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
        cls.browser = cls.sdk.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.sdk.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    def install(self, frame):
        # This is the exact initializer used by the desktop engine.
        self.assertIs(frame.evaluate(navigation_source()), True)

    def test_initializer_does_not_invoke_card_action_without_arguments(self):
        self.page.set_content('<h2>Escolha seu perfil de acesso</h2><a><i class="material-icons">send</i>Professor(a)</a>')
        self.install(self.page.main_frame)
        self.assertEqual(self.page.evaluate('() => desktopProfileCandidates().length'), 1)
        self.assertIs(self.page.evaluate('() => desktopProfileScreen()'), True)

    def test_native_clicks_advance_profile_school_and_subject(self):
        self.page.set_content('''<main><h2>Escolha seu perfil de acesso</h2>
          <a id="profile" href="#"><i class="material-icons">send</i>Professor(a)</a></main>''')
        self.install(self.page.main_frame)
        self.page.evaluate('''() => {
          window.trusted=[];
          document.querySelector('#profile').onclick=e=>{
            e.preventDefault();trusted.push(e.isTrusted);
            document.querySelector('main').innerHTML='<h2>Lista de Escolas</h2><section><h3>Escola Exemplo</h3><a id="school"><i class="material-icons">open_in_new</i>Abrir</a></section>';
          };
        }''')
        profile = self.page.evaluate_handle('() => desktopProfileAction()').as_element()
        self.assertIsNotNone(profile)
        profile.click()
        self.page.wait_for_function('() => !desktopProfileScreen()')
        self.page.evaluate('''() => {
          document.querySelector('#school').onclick=e=>{
            trusted.push(e.isTrusted);
            document.querySelector('main').innerHTML='<section><h3>Turma B</h3><p>Física</p><a id="wrong">Registro de aulas</a></section><section><h3>Turma B</h3><p>Matemática</p><a id="right"><i class="material-icons">description</i>Registro de aulas</a></section>';
          };
        }''')
        school = self.page.evaluate_handle('(c) => desktopAction(c)', {'title': 'Escola Exemplo', 'action': 'Abrir'}).as_element()
        self.assertIsNotNone(school)
        school.click()
        self.page.evaluate('''() => {
          document.querySelector('#right').onclick=e=>{trusted.push(e.isTrusted);document.querySelector('main').innerHTML='<h1>Registro de Aula</h1>';};
          document.querySelector('#wrong').onclick=()=>{throw Error('Disciplina incorreta');};
        }''')
        subject = self.page.evaluate_handle('(c) => desktopAction(c)', {'title': 'Turma B', 'action': 'Registro de aulas', 'discipline': 'Matemática'}).as_element()
        self.assertIsNotNone(subject)
        subject.click()
        self.assertEqual(self.page.locator('h1').inner_text(), 'Registro de Aula')
        self.assertEqual(self.page.evaluate('() => trusted'), [True, True, True])

    def test_profile_in_child_frame(self):
        markup = '<h2>Escolha seu perfil de acesso</h2><button onclick="document.body.innerHTML=\'<h2>Lista de Escolas</h2>\'">Professor(a)</button>'
        self.page.set_content('<iframe srcdoc="' + html.escape(markup, quote=True) + '"></iframe>')
        frame = self.page.frames[1]
        self.install(frame)
        profile = frame.evaluate_handle('() => desktopProfileAction()').as_element()
        self.assertIsNotNone(profile)
        profile.click()
        frame.wait_for_function('() => !desktopProfileScreen()')
        self.assertEqual(frame.locator('h2').inner_text(), 'Lista de Escolas')

    def test_class_below_viewport_with_div_click_handler(self):
        self.page.set_viewport_size({'width': 800, 'height': 500})
        self.page.set_content('''<h2>Lista de turmas</h2><div style="height:1800px"></div>
          <section><h3>Turma B</h3><p>Matemática</p><div id="row"><span>Registro de aulas</span></div></section>''')
        self.install(self.page.main_frame)
        self.page.evaluate("() => document.querySelector('#row').onclick=e=>window.opened=e.isTrusted")
        self.assertGreater(self.page.locator('#row').bounding_box()['y'], 500)
        action = locate_card_action(self.page.main_frame, 'Turma B', 'Registro de aulas', 'Matemática', scroll=True)
        self.assertIsNotNone(action)
        action.click()
        self.assertIs(self.page.evaluate('() => window.opened'), True)
        self.assertGreater(self.page.evaluate('() => scrollY'), 0)

    def test_lazy_class_loaded_by_scrolling_inside_offscreen_iframe(self):
        markup = '''<h2>Lista de turmas</h2><div id="panel" style="height:180px;overflow-y:auto">
          <section><h3>Turma A</h3><p>Física</p><a>Registro de aulas</a></section>
          <div style="height:1100px"></div></div>'''
        self.page.set_viewport_size({'width': 800, 'height': 500})
        self.page.set_content('<div style="height:1200px"></div><iframe style="height:300px;width:600px" srcdoc="' + html.escape(markup, quote=True) + '"></iframe>')
        frame = self.page.frames[1]
        self.install(frame)
        frame.evaluate('''() => {
          const panel=document.querySelector('#panel');let requested=false;
          panel.onscroll=()=>{
            if(requested || panel.scrollTop+panel.clientHeight<panel.scrollHeight-30)return;
            requested=true;
            setTimeout(()=>{
              panel.insertAdjacentHTML('beforeend','<section><h3>Turma B</h3><p>Matemática</p><div id="target"><span>Registro de aulas</span></div></section>');
              document.querySelector('#target').onclick=e=>window.opened=e.isTrusted;
            },150);
          };
        }''')
        self.assertIsNone(frame.evaluate_handle('(c)=>desktopAction(c)', {'title': 'Turma B', 'action': 'Registro de aulas', 'discipline': 'Matemática'}).as_element())
        logs = []
        action = locate_card_action(frame, 'Turma B', 'Registro de aulas', 'Matemática', scroll=True, log=logs.append)
        self.assertIsNotNone(action)
        action.click()
        self.assertIs(frame.evaluate('() => window.opened'), True)
        self.assertGreater(frame.evaluate("() => document.querySelector('#panel').scrollTop"), 0)
        self.assertGreater(self.page.evaluate('() => scrollY'), 0)
        self.assertTrue(logs)

    def test_missing_class_stops_at_bottom_without_opening_another(self):
        self.page.set_content('<h2>Lista de turmas</h2><section><h3>Turma A</h3><p>Matemática</p><button onclick="window.wrong=true">Registro de aulas</button></section>')
        self.install(self.page.main_frame)
        with self.assertRaisesRegex(AutomationError, 'não foram encontradas'):
            locate_card_action(self.page.main_frame, 'Turma B', 'Registro de aulas', 'Matemática', scroll=True)
        self.assertIsNone(self.page.evaluate('() => window.wrong'))

    def test_cancel_class_search_before_scrolling(self):
        stop = threading.Event()
        stop.set()
        with self.assertRaisesRegex(AutomationError, 'interrompida'):
            locate_card_action(self.page.main_frame, 'Turma B', 'Registro de aulas', 'Matemática', scroll=True, stop=stop)


if __name__ == '__main__':
    unittest.main()
