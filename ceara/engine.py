"""Bounded, sequential portal automation. An uncertain save is never retried."""
import re
import time
from urllib.parse import urlparse
from .planning import normal

PORTAL = 'https://professor.seduc.ce.gov.br/'

class Stopped(Exception):
    pass

class Engine:
    def __init__(self, config, entries, log, stop, resume):
        self.config, self.entries, self.log = config, entries, log
        self.stop, self.resume = stop, resume

    def check(self):
        if self.stop.is_set():
            raise Stopped()

    def official(self, page):
        url = urlparse(page.url)
        return url.scheme == 'https' and url.hostname == 'professor.seduc.ce.gov.br'

    def click(self, page, text):
        self.check()
        if not self.official(page):
            raise ValueError('A automação só altera o portal oficial da SEDUC-CE.')
        pattern = re.compile(r'^\s*[+\s]*' + text + r'\s*$', re.I)
        candidates = page.get_by_role('button', name=pattern).or_(page.get_by_role('link', name=pattern))
        targets = [x for x in candidates.all() if x.is_visible()]
        if len(targets) != 1:
            # Icon fonts sometimes contribute decorative words to accessible names.
            targets = [x for x in page.locator('a,button,input[type=submit]').all()
                       if x.is_visible() and re.fullmatch(text, x.evaluate("e=>{let c=e.cloneNode(true);c.querySelectorAll('i,svg').forEach(x=>x.remove());return (c.textContent||c.value||'').trim()}"), re.I)]
        if len(targets) != 1:
            raise ValueError(f'Não encontrei um único botão {text}. Envie o HTML dessa tela para ajustar o programa.')
        targets[0].scroll_into_view_if_needed()
        targets[0].click()
        page.wait_for_timeout(500)

    def select(self, page, field, wanted):
        self.check()
        if not self.official(page):
            raise ValueError('Página fora do portal oficial.')
        index = page.evaluate(r'''name => {
          const n=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/gi,'').toLowerCase();
          const selects=[...document.querySelectorAll('select')];
          const labels=[...document.querySelectorAll('label')].filter(x=>n(x.textContent)===n(name));
          if(labels.length!==1)return -1;
          const l=labels[0];let e=l.htmlFor?document.getElementById(l.htmlFor):null;
          if(!e&&l.nextElementSibling?.tagName==='SELECT')e=l.nextElementSibling;
          if(!e){let p=l.parentElement;for(let i=0;p&&i<3;i++,p=p.parentElement){let ss=p.querySelectorAll('select');if(ss.length===1){e=ss[0];break}}}
          return selects.indexOf(e);
        }''', field)
        if index < 0:
            raise ValueError(f'Campo {field} não identificado. Preciso do HTML dessa tela para ajustar o seletor.')
        control = page.locator('select').nth(index)
        control.wait_for(state='attached')
        options = control.locator('option').evaluate_all('(xs)=>xs.map(x=>({text:x.textContent,value:x.value}))')
        matches = [o for o in options if wanted(normal(o['text']))]
        if len(matches) != 1:
            raise ValueError(f'A opção escolhida para {field} está ausente ou ambígua.')
        control.select_option(value=matches[0]['value'])
        page.wait_for_timeout(500)

    def fill(self, page, field, value):
        self.check()
        inputs = page.get_by_label(re.compile('^'+field+r'\s*\*?$', re.I))
        if inputs.count() != 1:
            inputs = page.get_by_placeholder(re.compile('^'+field+'$', re.I))
        if inputs.count() != 1:
            raise ValueError(f'Campo {field} não identificado.')
        inputs.scroll_into_view_if_needed()
        limit = inputs.get_attribute('maxlength')
        if limit and int(limit) >= 0 and len(value) > int(limit):
            raise ValueError(f'{field} excede o limite do portal; texto não foi truncado nem enviado.')
        inputs.fill(value)
        if inputs.input_value() != value:
            raise ValueError(f'O portal não manteve o texto de {field}.')

    def contains(self, page, entry):
        # Period-scoped pair, excluding enclosing containers with multiple cards.
        return page.evaluate(r'''({period,content,sub})=>{
          const n=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toUpperCase();
          const nodes=[...document.querySelectorAll('div,section,article,li')];
          const pair=e=>{const t=n(e.textContent);return t.includes(n(content))&&t.includes(n(sub))};
          const cards=nodes.filter(e=>pair(e)&&![...e.children].some(c=>pair(c)));
          return cards.some(card=>{let p=card;while(p&&p!==document.body){
            const heads=[...p.querySelectorAll('h1,h2,h3,h4,h5,div,span,section')].filter(e=>!e.children.length).map(e=>n(e.textContent)).filter(t=>/^\d+[º°]? PERIODO$/.test(t));
            if(heads.length)return heads.length===1&&new RegExp('^'+period+'[º°]? PERIODO$').test(heads[0]);p=p.parentElement;
          }return false});
        }''', {'period':self.config['period'], 'content':entry.content, 'sub':entry.subcontent})

    def search(self, page):
        self.select(page, 'Ano Letivo', lambda s:s==str(self.config['year']))
        self.select(page, 'Item', lambda s:bool(re.match(str(self.config['grade'])+r'[º°]?\s*ANO\s*\|\s*ENSINO FUNDAMENTAL\s*\|\s*REGULAR$',s)))
        self.select(page, 'Disciplina', lambda s:s==normal(self.config['subject']))
        self.click(page, 'Buscar')
        page.wait_for_function(r"() => /Nenhum item encontrado|[1-4][º°]?\s*período/i.test(document.body.innerText)", timeout=15000)
        # Pagination cannot be silently ignored while checking for duplicates.
        if page.locator('.pagination').count() and page.locator('.pagination').inner_text().strip():
            raise ValueError('A lista usa paginação ainda não mapeada. Lote interrompido antes de adicionar.')
        if not page.get_by_text('Plano de Ensino', exact=True).count():
            raise ValueError('A busca não retornou a lista de planos.')

    def teaching_plan(self, page):
        """Continue from an authenticated portal tab, including an already-open plan."""
        if not self.official(page):
            raise ValueError('Volte ao Professor Online após concluir o login.')
        if not page.get_by_text(re.compile(r'^Buscar plano de ensino$', re.I)).count():
            self.click(page, 'Diário Online')
            self.click(page, 'Plano de ensino')
        self.search(page)
        for i, entry in enumerate(self.entries, 1):
            self.check()
            if self.contains(page, entry):
                self.log(f'{i}/{len(self.entries)}: {entry.day:%d/%m} já cadastrado; pulado.')
                continue
            self.click(page, 'Adicionar')
            self.select(page, 'Período', lambda s:bool(re.fullmatch(str(self.config['period'])+r'[º°]?\s*(?:PERIODO|BIMESTRE)',s)))
            self.fill(page, 'Conteúdo', entry.content)
            self.fill(page, 'Subconteúdo', entry.subcontent)
            self.click(page, 'Adicionar')
            deadline = time.monotonic()+20
            found = False
            while time.monotonic()<deadline:
                self.check()
                if self.contains(page, entry):
                    found = True
                    break
                page.wait_for_timeout(300)
            if not found:
                raise ValueError('Não confirmei o último cadastro na lista. Não vou reenviar; confira o portal antes de reiniciar.')
            self.log(f'{i}/{len(self.entries)}: {entry.day:%d/%m} salvo e conferido.')
        self.log('Plano concluído. O Chrome ficará aberto para consulta.')

    def authenticated_page(self, browser):
        pages = [page for context in browser.contexts for page in context.pages if self.official(page)]
        ready = [page for page in pages if
                 page.get_by_text(re.compile(r'^Diário Online$', re.I)).count() or
                 page.get_by_text(re.compile(r'^Buscar plano de ensino$', re.I)).count()]
        if len(ready) > 1:
            raise ValueError('Há mais de uma aba do portal aberta. Deixe apenas uma para continuar.')
        return ready[0] if ready else None

    def run(self):
        from playwright.sync_api import sync_playwright
        from .browser import ManualChrome
        chrome = ManualChrome()
        browser = None
        try:
            self.check()
            chrome.open(PORTAL)
            self.resume.clear()
            self.log('Chrome aberto para login manual. Clique em ACESSAR e entre com gov.br. Quando voltar ao Professor Online, clique em Continuar após login no programa.')
            # No Playwright browser connection or page scripts run during initial login.
            with sync_playwright() as p:
                page = None
                while page is None:
                    while not self.resume.wait(.25):
                        self.check()
                        if not chrome.running():
                            raise ValueError('O Chrome foi fechado. Inicie uma nova sessão.')
                    self.check()
                    self.resume.clear()
                    if browser is None:
                        endpoint = chrome.endpoint(self.stop)
                        self.check()
                        browser = p.chromium.connect_over_cdp(endpoint, timeout=15000)
                    page = self.authenticated_page(browser)
                    if page is None:
                        self.log('Login ainda não concluído. Volte ao Professor Online e clique novamente em Continuar após login.')
                self.log('Sessão do Professor Online conectada. Iniciando o plano de ensino.')
                self.teaching_plan(page)
                while not self.stop.wait(.25) and chrome.running():
                    pass
        except Stopped:
            self.log('Interrompido. Cadastros já enviados permanecem no portal.')
        except Exception as e:
            self.log(str(e) if isinstance(e, ValueError) else 'Não consegui continuar nesta tela. Lote interrompido; confira o último item antes de reiniciar.')
            self.log('O Chrome ficará aberto para conferência. Use Parar e fechar sessão do programa para encerrar.')
            while not self.stop.wait(.25) and chrome.running():
                pass
        finally:
            chrome.close()
