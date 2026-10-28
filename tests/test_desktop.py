import contextlib
import threading
import types
import unittest
from unittest.mock import patch

from desktop.engine import AutomationError, bundle, register_month
from desktop.planning import CONTENT, METHOD, lessons


def config(**changes):
    value = {'escola': 'Escola Exemplo', 'turma': 'Turma Exemplo', 'disciplina': 'Matemática',
             'mes': '2028-02', 'semana': {'2': '08:00 - 09:00; 08:00 - 09:00'},
             'excecoes': '8, 15;22', 'conteudo': CONTENT, 'metodologia': METHOD}
    value.update(changes)
    return value


class PlanningTests(unittest.TestCase):
    def test_leap_month_exclusions_and_duplicate_times(self):
        self.assertEqual(lessons(config()), [
            {'data': '2028-02-01', 'horario': '08:00 - 09:00'},
            {'data': '2028-02-29', 'horario': '08:00 - 09:00'},
        ])

    def test_full_date_exclusion(self):
        self.assertEqual(len(lessons(config(excecoes='01/02/2028'))), 4)

    def test_accepts_single_digit_hours_and_deduplicates_after_normalization(self):
        result = lessons(config(semana={'2': '9:20 - 10:20; 09:20 - 10:20'}))
        self.assertEqual(result, [
            {'data': '2028-02-01', 'horario': '09:20 - 10:20'},
            {'data': '2028-02-29', 'horario': '09:20 - 10:20'},
        ])

    def test_accepts_portal_time_separators(self):
        for value in ('9:20 às 10:20', '9:20 – 10:20', '9:20 — 10:20'):
            with self.subTest(value=value):
                self.assertEqual(lessons(config(semana={'2': value}))[0]['horario'], '09:20 - 10:20')

    def test_invalid_dates_and_times_do_not_start_a_plan(self):
        for changes in ({'mes': '2028-13'}, {'excecoes': '30'}, {'excecoes': '01/03/2028'},
                        {'semana': {'2': '09:00 - 08:00'}}, {'semana': {'2': '08:99 - 09:00'}},
                        {'semana': {'2': '9:60 - 10:20'}}, {'semana': {'2': '29:20 - 30:20'}},
                        {'semana': {'2': 'texto 9:20 - 10:20'}}, {'semana': {}}, {'escola': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                lessons(config(**changes))


class RuntimeTests(unittest.TestCase):
    def test_bundle_has_no_extension_runtime_dependency(self):
        source = bundle()
        self.assertIn('desktopAction', source)
        self.assertIn('LoteAulas', source)
        self.assertNotIn('chrome.scripting', source)
        self.assertNotIn('chrome.storage', source)

    def test_stop_before_launch(self):
        stop = threading.Event()
        stop.set()
        with self.assertRaises(AutomationError):
            register_month(config(), 'teste', 'senha-de-teste', stop, lambda text: None)

    def test_browser_errors_never_expose_raw_filled_values(self):
        logs = []
        def fail(**kwargs):
            raise RuntimeError('segredo-nao-exibir')
        @contextlib.contextmanager
        def sdk():
            yield types.SimpleNamespace(chromium=types.SimpleNamespace(launch=fail))
        module = types.ModuleType('playwright.sync_api')
        module.sync_playwright = sdk
        module.Error = RuntimeError
        with patch.dict('sys.modules', {'playwright.sync_api': module}):
            with self.assertRaises(AutomationError) as caught:
                register_month(config(), 'usuario-local', 'segredo-nao-exibir', threading.Event(), logs.append)
        self.assertNotIn('segredo-nao-exibir', str(caught.exception) + ''.join(logs))


if __name__ == '__main__':
    unittest.main()
