"""Real Playwright regression: no network, portal login, or saved credentials."""
import html
import datetime as dt
import os
from pathlib import Path
import sys
import threading
import unittest

from desktop.engine import AutomationError, ROOT, SCRIPTS, locate_card_action, navigation_source, registration_ready

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

    def install_runtime(self, frame):
        sources = [(ROOT / name).read_text(encoding='utf-8') for name in SCRIPTS]
        frame.evaluate('''sources => {
          const storage=new Map();
          Object.defineProperty(window,'sessionStorage',{value:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)}});
          if(!crypto.randomUUID)crypto.randomUUID=()=>String(Math.random());
          for(const source of sources)(0,eval)(source+'\\n;void 0;');
          setInterval(()=>LoteAulas.run(),100);
        }''', sources)

    def wait_for_month(self, frame):
        frame.wait_for_function("() => /^(Mês concluído|Lote interrompido)/.test(sessionStorage.getItem('assistente-aulas-status')||'')", timeout=25000)
        status = frame.evaluate("() => sessionStorage.getItem('assistente-aulas-status')")
        self.assertTrue(status.startswith('Mês concluído'), status)

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

    def test_actual_footer_next_symbol_reads_all_51_records_in_six_pages(self):
        self.page.set_viewport_size({'width': 650, 'height': 430})
        self.page.set_content('<main></main>')
        self.install_runtime(self.page.main_frame)
        rows = [[(dt.date(2026, 1, 1) + dt.timedelta(days=i)).strftime('%d/%m/%Y'), '09:20 às 10:20', 'Turma Exemplo', 'MATEMÁTICA', 'Aula confirmada'] for i in range(50)]
        rows.append(['31/10/2026', '9:20 às 10:20', 'Turma Exemplo', 'MATEMÁTICA', 'Aula aguardando confirmação'])
        self.page.evaluate('''rows => {
          window.pageClicks=[];window.wrongClicks=0;
            window.skipPage=false;
            function render(index) {
            const main=document.querySelector('main');main.replaceChildren();
            const summary=document.createElement('div');summary.textContent='49 Aulas confirmadas 1 Aulas aguardando confirmação 0 Aulas rejeitadas';main.append(summary);
            const spacer=document.createElement('div');spacer.style.height='1000px';main.append(spacer);
            const table=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr');
            for(const text of ['Data da Aula','Horário (inicial ~ final)','Turma','Componente','Situação']){const cell=document.createElement('th');cell.textContent=text;tr.append(cell);}head.append(tr);table.append(head);
            const body=document.createElement('tbody');for(const row of rows.slice(index*10,index*10+10)){const line=document.createElement('tr');for(const text of row){const cell=document.createElement('td');cell.textContent=text;line.append(cell);}body.append(line);}table.append(body);main.append(table);
            const footer=document.createElement('div');footer.innerHTML='<select><option>10 Registros</option></select> Mostrando '+(index*10+1)+' a '+Math.min(index*10+10,51)+' de 51 registros Página <input type="number" value="'+(index+1)+'"> de 6 <button>Ir</button>';
            footer.querySelector('button').onclick=()=>wrongClicks++;
              function control(text,next){const b=document.createElement('button');b.textContent=text;b.onclick=()=>{const r=b.getBoundingClientRect();pageClicks.push({text,visible:r.top>=0&&r.bottom<=innerHeight+1});render(next+(window.skipPage&&next>index?1:0));};footer.append(b);}
            if(index>0)control('‹ Anterior',index-1);
            if(index<5)control('Próxima ›',index+1);
            const last=document.createElement('button');last.textContent='Última »';last.onclick=()=>wrongClicks++;footer.append(last);main.append(footer);
          }
            window.renderPage=render;render(5);
        }''', rows)
        self.page.evaluate("() => LoteAulas.start({turma:'Turma Exemplo',disciplina:'Matemática',conteudo:'Exemplo',metodologia:'Exemplo'},[{data:'2026-10-31',horario:'09:20 - 10:20'}])")
        self.wait_for_month(self.page.main_frame)
        audit = self.page.evaluate('() => ({clicks:pageClicks,wrong:wrongClicks,done:JSON.parse(sessionStorage.getItem("assistente-aulas-lote-concluido"))})')
        self.assertEqual(audit['wrong'], 0)
        self.assertEqual(len(audit['clicks']), 10)
        self.assertTrue(all(click['visible'] for click in audit['clicks']))
        self.assertEqual(audit['done'][0]['done'], 'já registrado')
        self.page.evaluate("() => {skipPage=true;renderPage(0);LoteAulas.start({turma:'Turma Exemplo',disciplina:'Matemática',conteudo:'Exemplo',metodologia:'Exemplo'},[{data:'2026-10-31',horario:'09:20 - 10:20'}]);}")
        self.page.wait_for_function("() => (sessionStorage.getItem('assistente-aulas-status')||'').startsWith('Lote interrompido')")
        self.assertIn('em sequência', self.page.evaluate("() => sessionStorage.getItem('assistente-aulas-status')"))
        self.assertEqual(self.page.evaluate('() => wrongClicks'), 0)

    def test_month_scrolls_to_add_and_every_save_through_finalization(self):
        self.page.set_viewport_size({'width': 650, 'height': 430})
        self.page.set_content('<iframe style="width:600px;height:380px" srcdoc="<main></main>"></iframe>')
        frame = self.page.frames[1]
        self.install_runtime(frame)
        fixture = (Path(__file__).parent / 'fixtures' / 'registro-conteudo.html').read_text(encoding='utf-8')
        frame.evaluate('''fixture => {
          window.audit=[];window.frequencyChanges=0;
          const main=document.querySelector('main');
          function audit(name,el){const r=el.getBoundingClientRect();window.audit.push({name,visible:r.top>=0&&r.bottom<=innerHeight+1});}
          function spacer(){const el=document.createElement('div');el.style.height='1100px';main.append(el);}
          function confirm(name,next){
            const modal=document.createElement('div');modal.role='alertdialog';modal.style.cssText='position:fixed;top:10px;left:10px;background:white;padding:10px';
            modal.innerHTML='<h2>Atenção</h2><p>Tem certeza que deseja realizar essa ação?</p><button>Não</button><button>Sim</button>';
            const yes=modal.querySelectorAll('button')[1];yes.onclick=()=>{audit('confirmar '+name,yes);modal.remove();next();};document.body.append(modal);
          }
          function list(saved,lazy=false){
            main.replaceChildren();const h=document.createElement('h1');h.textContent='Registro de Aula';main.append(h);
            const summary=document.createElement('div');summary.textContent='0 Aulas confirmadas '+(saved?1:0)+' Aulas aguardando confirmação 0 Aulas rejeitadas';main.append(summary);spacer();
            function details(){
              const add=document.createElement('button');add.innerHTML='<span aria-hidden="true">+</span> Adicionar aula';add.onclick=()=>{audit('adicionar',add);content();};main.append(add);
              const table=document.createElement('table');table.innerHTML='<thead><tr><th>Data da Aula</th><th>Horário (inicial ~ final)</th><th>Turma</th><th>Componente</th><th>Situação</th></tr></thead><tbody>'+(saved?'<tr><td>05/10/2026</td><td>09:20 às 10:20</td><td>Turma Exemplo</td><td>MATEMÁTICA</td><td>Aula aguardando confirmação</td></tr>':'<tr><td colspan="5">Nenhum registro encontrado</td></tr>')+'</tbody>';main.append(table);
            }
            if(lazy){window.onscroll=()=>{if(scrollY>150){window.onscroll=null;setTimeout(details,100);}};}else details();
          }
          const stages=['Plano de aula','Frequência','Recursos didáticos','Atividade'];
          function wizard(index){
            const stage=stages[index];main.innerHTML='<nav aria-label="breadcrumb">Registro de Aula / '+stage+'</nav>';
            if(stage==='Frequência'){const input=document.createElement('input');input.type='checkbox';input.checked=true;input.onchange=()=>frequencyChanges++;main.append(input);}
            spacer();const save=document.createElement('button');save.textContent=index===3?'Salvar e Finalizar':'Salvar e Avançar';
            save.onclick=()=>{audit(stage,save);if(stage==='Frequência')window.frequencyPreserved=main.querySelector('input').checked;confirm(stage,()=>index===3?list(true):wizard(index+1));};main.append(save);
          }
          function content(){
            main.innerHTML='<nav aria-label="breadcrumb">Registro de Aula / Conteúdo</nav>'+fixture;
            function menu(name,label){const trigger=PortalAulas.field(name);trigger.onclick=()=>{const list=document.createElement('div');list.id=trigger.getAttribute('aria-controls');list.role='listbox';const option=document.createElement('div');option.role='option';option.tabIndex=0;option.textContent=label;option.onclick=()=>{trigger.textContent=label;list.remove();};list.append(option);document.body.append(list);};}
            menu('Tipo de Aula','Aula Normal');menu('Horário (inicial ~ final)','9:20 - 10:20');
            const date=PortalAulas.field('Data');date.onclick=()=>{const calendar=document.createElement('div');calendar.id=date.getAttribute('aria-controls');calendar.role='dialog';calendar.innerHTML='<div class="rdp"><div aria-live="polite">outubro 2026</div><button>5</button></div>';calendar.querySelector('button').onclick=()=>{date.textContent='05/10/2026';calendar.remove();};document.body.append(calendar);};
            spacer();const save=document.createElement('button');save.textContent='Salvar e Avançar';save.onclick=()=>{audit('conteúdo',save);window.savedContent=PortalAulas.field('Conteúdo abordado').value;confirm('conteúdo',()=>wizard(0));};main.append(save);
          }
          list(false,true);
        }''', fixture)
        self.assertIsNone(frame.evaluate('() => LoteAulas.tableSnapshot()'))
        self.assertTrue(registration_ready(frame))
        frame.evaluate("() => LoteAulas.start({turma:'Turma Exemplo',disciplina:'Matemática',conteudo:'Conteúdo de exemplo',metodologia:'Metodologia de exemplo'},[{data:'2026-10-05',horario:'09:20 - 10:20'}])")
        self.wait_for_month(frame)
        audit = frame.evaluate('() => ({actions:audit,content:savedContent,frequencyPreserved,frequencyChanges})')
        self.assertEqual([item['name'] for item in audit['actions']], ['adicionar','conteúdo','confirmar conteúdo','Plano de aula','confirmar Plano de aula','Frequência','confirmar Frequência','Recursos didáticos','confirmar Recursos didáticos','Atividade','confirmar Atividade'])
        self.assertTrue(all(item['visible'] for item in audit['actions']), audit['actions'])
        self.assertEqual(audit['content'], 'Conteúdo de exemplo')
        self.assertTrue(audit['frequencyPreserved'])
        self.assertEqual(audit['frequencyChanges'], 0)


if __name__ == '__main__':
    unittest.main()
