import re
import threading
import unittest
from datetime import date
from ceara.planning import interval, distribute, bullets
from ceara.engine import Engine, Stopped

class CurriculumTests(unittest.TestCase):
    def test_week_and_month_boundary(self):
        self.assertEqual(interval('FEVEREIRO\n19 A 20',2026),(date(2026,2,19),date(2026,2,20)))
        self.assertEqual(interval('30 DE MARÇO\nA 03 DE ABRIL',2026),(date(2026,3,30),date(2026,4,3)))
        with self.assertRaises(ValueError): interval('FEVEREIRO 01 A 28',2026)

    def test_two_days_and_exclusions(self):
        entries=distribute(date(2026,2,2),date(2026,2,6),'• Diagnóstico\n→ Naturais\n→ Inteiros\n→ Racionais')
        self.assertEqual([e.day for e in entries],[date(2026,2,4),date(2026,2,5)])
        self.assertIn('Naturais',entries[0].subcontent)
        self.assertIn('Racionais',entries[1].subcontent)
        one=distribute(date(2026,2,2),date(2026,2,6),'• Naturais\n→ Inteiros', [date(2026,2,4)])
        self.assertEqual(len(one),1)
        self.assertIn('Naturais',one[0].subcontent)
        self.assertIn('Inteiros',one[0].subcontent)

    def test_partial_week(self):
        self.assertEqual([e.day for e in distribute(date(2026,2,19),date(2026,2,20),'Revisão')],[date(2026,2,19)])

    def test_explicit_exam_date(self):
        entries=distribute(date(2026,3,2),date(2026,3,6),'→ APLICAÇÃO DA PROVA (04/03)\n• Números reais\n→ Irracionais')
        self.assertIn('PROVA',entries[0].content)
        self.assertNotIn('PROVA',entries[1].subcontent)
        self.assertIn('Irracionais',entries[1].subcontent)

    def test_units_not_split_at_arbitrary_middle(self):
        entries=distribute(date(2026,3,23),date(2026,3,27),'• (UNIDADE 01) Potências\n→ (Capítulo 03) Potências\n• Expoentes\n• Notação científica\n• (UNIDADE 05) Semelhança\n→ (Capítulo 01) Segmentos\n• Razão')
        self.assertIn('Notação científica',entries[0].subcontent)
        self.assertNotIn('Notação científica',entries[1].subcontent)
        self.assertEqual(entries[1].content,'Segmentos')

    def test_wrapped_bullets_and_notes(self):
        self.assertEqual(bullets('• Triângulo\nretângulo\nObs: observação\nnão é conteúdo'),['Triângulo retângulo'])

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        import shutil
        cls.p=sync_playwright().start()
        cls.browser=cls.p.chromium.launch(**({'executable_path':shutil.which('chromium'),'headless':True,'args':['--no-sandbox']} if shutil.which('chromium') else {'channel':'chrome','headless':True}))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()

    def setUp(self):
        self.page=self.browser.new_page(viewport={'width':800,'height':500})
        self.engine=Engine({'year':2026,'grade':9,'period':1,'subject':'MATEMÁTICA'},[],lambda x:None,threading.Event(),threading.Event())
        self.engine.official=lambda page:True

    def tearDown(self):
        self.page.close()

    def test_select_fill_scroll_save_and_exact_period(self):
        self.page.set_content('''<label>Ano Letivo: *</label><select><option>2025</option><option>2026</option></select>
          <div><label>Item: *</label><select><option>8º Ano| Ensino Fundamental | Regular</option><option>9º Ano| Ensino Fundamental | Regular</option></select></div>
          <div><label>Disciplina *</label><select><option>IMERSÃO EM MATEMÁTICA</option><option>MATEMÁTICA</option></select></div>
          <div><label>Período*</label><select><option>1º período</option><option>2º período</option></select></div>
          <input placeholder="CONTEÚDO"><input placeholder="SUBCONTEÚDO">
          <div style="height:1400px"></div><button onclick="document.getElementById('list').innerHTML='<div><div>1º período</div><div><div>'+document.querySelector('[placeholder=CONTEÚDO]').value+'</div><div>'+document.querySelector('[placeholder=SUBCONTEÚDO]').value+'</div></div></div>'">Adicionar</button><div id="list"></div>''')
        self.engine.select(self.page,'Ano Letivo',lambda s:s=='2026')
        self.engine.select(self.page,'Item',lambda s:s.startswith('9'))
        self.engine.select(self.page,'Disciplina',lambda s:s=='MATEMATICA')
        self.engine.select(self.page,'Período',lambda s:s=='1º PERIODO')
        entry=distribute(date(2026,2,19),date(2026,2,20),'Números inteiros')[0]
        self.engine.fill(self.page,'Conteúdo',entry.content)
        self.engine.fill(self.page,'Subconteúdo',entry.subcontent)
        self.assertFalse(self.engine.contains(self.page,entry))
        self.engine.click(self.page,'Adicionar')
        self.assertTrue(self.engine.contains(self.page,entry))
        self.engine.config['period']=2
        self.assertFalse(self.engine.contains(self.page,entry))

    def test_duplicate_button_and_length_stop(self):
        self.page.set_content('<button>Adicionar</button><button>Adicionar</button><input placeholder="CONTEÚDO" maxlength="4">')
        with self.assertRaises(ValueError): self.engine.click(self.page,'Adicionar')
        with self.assertRaises(ValueError): self.engine.fill(self.page,'Conteúdo','Texto longo')
        self.assertEqual(self.page.locator('input').input_value(),'')
        self.engine.stop.set()
        with self.assertRaises(Stopped): self.engine.check()
