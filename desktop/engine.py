import json
import re
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from desktop import APP_VERSION
from desktop.planning import lessons

ORIGINS = {'https://portal.seduc.pi.gov.br', 'https://seduc-academico-prod.seduc.pi.gov.br'}
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
SCRIPTS = ('portal.js', 'confirmation.js', 'wizard.js', 'fill.js', 'batch.js')


class AutomationError(Exception):
    pass


def bundle():
    source = '\n'.join((ROOT / name).read_text(encoding='utf-8') for name in SCRIPTS)
    navigation = (ROOT / 'desktop' / 'navigation.js').read_text(encoding='utf-8')
    return """(() => {
      if(!%s.includes(location.origin))return;
      const start=()=>{%s\n%s};
      if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
    })();""" % (json.dumps(sorted(ORIGINS)), source, navigation)


def official(frame):
    parsed = urlsplit(frame.url)
    return parsed.scheme + '://' + parsed.netloc in ORIGINS


def navigation_source():
    # Playwright invokes a function returned by evaluate(). A bare script ending
    # in desktopAction's assignment returns that function and calls it with null.
    # Execute declarations inside an explicit initializer returning a boolean.
    source = (ROOT / 'desktop' / 'navigation.js').read_text(encoding='utf-8')
    return '() => {\n' + source + '\nreturn true;\n}'


def register_month(config, username, password, stop: threading.Event, log):
    """Own one ephemeral Chrome session. No credentials, cookies, traces or HAR saved."""
    planned = lessons(config)
    if stop.is_set():
        raise AutomationError('Execução interrompida.')
    from playwright.sync_api import sync_playwright, Error as BrowserError

    stage = 'abrir Chrome'
    browser = None
    page = None
    def inspect_window():
        if page and not stop.is_set() and not page.is_closed():
            log('A janela ficará aberta para conferência. Feche o Chrome do programa ou clique em Parar e fechar Chrome para encerrar.')
            while not stop.is_set() and not page.is_closed():
                try:
                    page.wait_for_timeout(250)
                except Exception:
                    break
    with sync_playwright() as playwright:
        try:
            log('Versão do programa: ' + APP_VERSION)
            log('Abrindo o Chrome do programa…')
            browser = playwright.chromium.launch(channel='chrome', headless=False)
            context = browser.new_context(no_viewport=True)
            source = bundle()
            context.add_init_script(script=source)
            page = context.new_page()
            page.set_default_timeout(15000)
            stage = 'login'
            page.goto('https://portal.seduc.pi.gov.br/', wait_until='domcontentloaded', timeout=60000)
            login_user = page.locator('input[placeholder="Usuário"],input[placeholder="Usuario"],input[name="usuario"],input#usuario,input#username').filter(visible=True)
            if login_user.count() == 0:
                login_user = page.locator('input[type="text"]').filter(visible=True)
            login_password = page.locator('input[type="password"]').filter(visible=True)
            login_password.first.wait_for(state='visible')
            if login_user.count() == 0:
                login_user = page.locator('input[type="text"]').filter(visible=True)
            if login_user.count() != 1 or login_password.count() != 1:
                raise AutomationError('Não foi possível identificar os campos de login. Nenhuma senha foi enviada.')
            if stop.is_set():
                raise AutomationError('Execução interrompida.')
            login_user.fill(username)
            login_password.fill(password)
            # Only the official HTTPS page receives the credentials.
            page.get_by_role('button', name=re.compile(r'^entrar$', re.I)).click()
            username = password = None
            log('Login enviado. Se aparecer CAPTCHA ou código, conclua na janela do Chrome.')
            stage = 'perfil, escola e turma'
            deadline = time.monotonic() + 180
            clicked = set()
            profile_attempts = 0
            profile_seen = None
            seen_hosts = set()
            registration = None
            while time.monotonic() < deadline:
                if stop.is_set():
                    raise AutomationError('Execução interrompida.')
                # School links can open a new tab; follow only official HTTPS pages.
                official_pages = [item for item in context.pages if not item.is_closed() and official(item.main_frame)]
                if official_pages:
                    page = official_pages[-1]
                host = urlsplit(page.url).hostname
                if host and host not in seen_hosts:
                    seen_hosts.add(host)
                    log('Página de acesso no domínio: ' + host)
                for frame in page.frames:
                    try:
                        if frame.is_detached() or not official(frame):
                            continue
                        parsed = urlsplit(frame.url)
                        if parsed.hostname == 'seduc-academico-prod.seduc.pi.gov.br' and parsed.path.startswith('/registro-aulas/'):
                            ready = frame.evaluate('''() => Boolean(globalThis.LoteAulas && (LoteAulas.tableSnapshot() || [...document.querySelectorAll('label')].some(el=>PortalAulas.norm(el.textContent)==='conteudo abordado')))''')
                            if ready and {'escola', 'turma'}.issubset(clicked):
                                registration = frame
                                break
                        frame.evaluate(navigation_source())
                        if frame.evaluate('() => desktopProfileScreen()'):
                            if profile_seen is None:
                                profile_seen = time.monotonic()
                                log('Tela de perfis identificada. Selecionando Professor(a)…')
                            candidates = frame.evaluate('() => desktopProfileCandidates().length')
                            if candidates > 1:
                                raise AutomationError('Há mais de uma opção Professor(a). Nenhum perfil foi escolhido para evitar abrir o acesso errado.')
                            if candidates == 0 and time.monotonic() - profile_seen < 1:
                                log('Aguardando o controle de seleção do perfil carregar…')
                            handle = frame.evaluate_handle('() => desktopProfileAction()')
                            element = handle.as_element()
                            if not element:
                                handle.dispose()
                                if time.monotonic() - profile_seen > 20:
                                    raise AutomationError('A tela de perfis foi encontrada, mas o botão Professor(a) não foi reconhecido. Nenhuma aula foi criada.')
                                continue
                            if profile_attempts >= 3:
                                raise AutomationError('O portal não avançou após selecionar Professor(a). Nenhuma aula foi criada.')
                            profile_attempts += 1
                            try:
                                if element.evaluate('(el) => el.tagName') == 'SELECT':
                                    value = element.evaluate('(el) => [...el.options].find(option => !option.disabled && desktopProfileLabel(desktopText(option))).value')
                                    element.select_option(value=value)
                                else:
                                    element.click(timeout=5000)
                                frame.wait_for_function('() => typeof desktopProfileScreen === "function" && !desktopProfileScreen()', timeout=6000)
                                clicked.add('perfil')
                                log('Perfil Professor(a) selecionado. Procurando a escola…')
                            finally:
                                handle.dispose()
                            break
                        for name, title, action, subject in (
                            ('escola', config['escola'], 'Abrir', None),
                            ('turma', config['turma'], 'Registro de aulas', config['disciplina']),
                        ):
                            if name in clicked:
                                continue
                            if name == 'turma' and 'escola' not in clicked:
                                continue
                            handle = frame.evaluate_handle('(c)=>desktopAction(c)', {'title': title, 'action': action, 'discipline': subject})
                            element = handle.as_element()
                            if element:
                                element.click(); clicked.add(name); log('Escola aberta.' if name == 'escola' else 'Turma e disciplina selecionadas.'); break
                            handle.dispose()
                    except BrowserError as error:
                        if page.is_closed():
                            raise AutomationError('A janela do Chrome foi fechada antes de abrir a turma.') from None
                        transient = ('execution context was destroyed', 'cannot find context', 'frame was detached', 'frame has been detached', 'most likely because of a navigation')
                        if type(error).__name__ != 'TimeoutError' and not any(marker in str(error).lower() for marker in transient):
                            raise AutomationError('Não foi possível executar a leitura da tela de acesso. Atualize o programa e informe a última mensagem exibida. Tipo: ' + type(error).__name__) from None
                        # Retry only transient navigation/loading failures, not hidden script errors.
                        continue
                if registration:
                    break
                page.wait_for_timeout(400)
            if not registration:
                raise AutomationError('O caminho até a turma não foi reconhecido. Confira os nomes de escola, turma e disciplina. O programa não criou aulas.')
            if stop.is_set():
                raise AutomationError('Execução interrompida.')
            stage = 'registro mensal'
            registration.evaluate('(data)=>LoteAulas.start(data.config,data.aulas)', {'config': config, 'aulas': planned})
            log('Registro mensal iniciado; não use esta janela para outras operações.')
            last = None
            while not page.is_closed():
                if stop.is_set():
                    for frame in page.frames:
                        if official(frame):
                            try:
                                frame.evaluate("() => ['assistente-aulas-lote','assistente-aulas-fluxo','assistente-aulas-preenchimento'].forEach(k=>sessionStorage.removeItem(k))")
                            except Exception:
                                pass
                    raise AutomationError('Execução interrompida. Envios já realizados não foram desfeitos.')
                frames = [frame for frame in page.frames if official(frame) and urlsplit(frame.url).path.startswith('/registro-aulas/')]
                if len(frames) == 1:
                    state = frames[0].evaluate("() => ({status:sessionStorage.getItem('assistente-aulas-status'),active:!!sessionStorage.getItem('assistente-aulas-lote')})")
                    if state['status'] and state['status'] != last:
                        last = state['status']; log(last)
                    if not state['active']:
                        if last and last.startswith('Mês concluído'):
                            log('Concluído. Confira o resultado no portal antes de iniciar outro mês.')
                            inspect_window()
                            return
                        raise AutomationError('O lote foi interrompido. Confira os registros já enviados antes de tentar novamente.')
                page.wait_for_timeout(500)
            raise AutomationError('A janela do Chrome foi fechada. Confira os registros antes de reiniciar.')
        except AutomationError as error:
            log(str(error))
            inspect_window()
            raise
        except Exception as error:
            # Playwright's raw call logs can contain filled values: never show them.
            message = 'Não foi possível concluir a etapa: ' + stage + '. Confira a janela do Chrome e tente novamente após verificar os registros. Tipo: ' + type(error).__name__
            log(message)
            inspect_window()
            raise AutomationError(message) from None
        finally:
            username = password = None
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
