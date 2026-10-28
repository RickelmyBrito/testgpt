# Programa de Registro de Aulas — Windows

Programa com janela própria que abre o Google Chrome, faz login no portal da SEDUC-PI e tenta registrar as aulas do mês automaticamente. **Não requer extensão do Chrome.**

A versão atual aparece no título da janela: **3.1.2**. Após atualizar o ZIP, abra `Abrir Programa.cmd` da nova pasta; um executável ou atalho antigo não é atualizado pela extração do código-fonte.

## Abrir no Windows

### Executável

A compilação Windows está configurada em [Actions → Programa Windows](https://github.com/RickelmyBrito/testgpt/actions/workflows/windows-program.yml). Quando uma execução terminar com sucesso, baixe o artefato **RegistroDeAulas-Windows**, extraia e abra **RegistroDeAulas.exe**. O executável inclui Python e Playwright; o Google Chrome deve estar instalado no computador.

O repositório contém a configuração de compilação, não um executável previamente validado neste ambiente Linux. Uma execução verde do workflow comprova a compilação e o teste local do executável no Windows; não comprova o acesso ao diário real.

### Código-fonte (alternativa imediata)

1. Baixe [o ZIP do projeto](https://github.com/RickelmyBrito/testgpt/archive/refs/heads/main.zip) e extraia a pasta.
2. Tenha **Google Chrome** e **Python 3.12 para Windows** instalados. O instalador oficial do Python deve incluir o Python Launcher (`py`).
3. Dê dois cliques em **Abrir Programa.cmd**. Na primeira abertura, ele prepara uma pasta `.venv` e instala Playwright com verificação TLS normal. Nas próximas, abre a interface.

## Como usar

Na janela do programa, informe:

- Usuário e senha do portal (somente no seu computador).
- Nome completo da escola, turma e disciplina, como aparecem no portal.
- Mês e ano no formato `AAAA-MM`.
- Dias da semana e horários de início e fim. Aceita `9:20 - 10:20` e `09:20 - 10:20`. Para várias aulas no mesmo dia, separe os horários por ponto e vírgula: `8:00 - 9:00; 10:00 - 11:00`.
- Dias sem aula no mês, por exemplo `7, 12, 21`.
- Conteúdo e metodologia correspondentes às aulas efetivamente realizadas.

Clique em **Entrar e registrar mês**. O programa abre uma janela separada do Chrome, envia o login, seleciona Professor(a), procura a escola e o cartão da turma/disciplina e inicia o lote. Se aparecer CAPTCHA ou código de verificação, conclua essa etapa no Chrome; o programa não contorna essas verificações.

A procura da turma percorre a página e painéis internos com rolagem, incluindo listas dentro de iframe e cartões carregados durante a rolagem. Ao encontrar um cartão único, traz a ação Registro de aulas para a área visível antes de clicar, mesmo quando ela é um texto dentro de um cartão clicável. Se chegar ao fim sem localizar a combinação exata de turma e disciplina, informa o motivo e interrompe sem abrir outra turma.

O lote consulta a lista existente e a paginação reconhecida, exige totais completos e pula aulas já registradas. Para cada aula restante, tenta selecionar Aula Normal, data e horário, preencher os textos, confirmar o envio, avançar por Plano de aula, Frequência e Recursos didáticos e finalizar em Atividade. Aguarda localizar na lista o registro correspondente antes de iniciar outro.

Não edita competências, habilidades, objetivos ou notas. Na frequência, clica em Salvar e Avançar sem alterar os controles: **isso pode gravar os valores já exibidos**, conforme autorizado pelo usuário. Não adiciona recursos ou atividades. Aguardando confirmação significa enviado, pendente de confirmação da escola.

Use **Parar e fechar Chrome** para interromper. Ações já enviadas não são desfeitas. Não utilize essa janela para outras operações enquanto o lote estiver ativo. Após concluir ou detectar uma falha, a janela fica aberta para conferência até você fechá-la ou clicar em Parar.

## Credenciais e dados

Usuário e senha são usados para preencher o formulário HTTPS oficial e não são gravados pelo programa em arquivos ou configurações. A senha é retirada da interface ao iniciar. O navegador usa um contexto novo, sem reutilizar seu perfil pessoal; a sessão fica em memória durante a execução. O programa não salva cookies, capturas de tela, HAR ou traces. Mensagens de erro não incluem os logs brutos de preenchimento do Playwright. Serviços oficiais podem manter seus próprios registros de acesso.

Os metadados do lote ficam no armazenamento de sessão da página acadêmica durante a execução. O programa não acessa dados de notas nem exporta dados de alunos.

## Limites conhecidos

O preenchimento usa a estrutura real de conteúdo fornecida pelo usuário: React/Radix em um iframe de `seduc-academico-prod.seduc.pi.gov.br`, dentro de `portal.seduc.pi.gov.br`. A navegação procura ações únicas pelos nomes exatos de escola, turma e disciplina. Controles ambíguos, filtros que escondem aulas, paginação não reconhecida ou resultados incertos interrompem o lote sem reenvio automático. Confira os registros antes de reiniciar após uma falha.

**A integração autenticada completa ainda precisa ser validada no portal.** Os testes locais usam a estrutura sanitizada dos campos e eventos simulados para menus, calendário, cartões e salvamento. Não comprovam uma gravação real. O HTML recebido não incluiu o calendário aberto nem os cartões completos; mudanças nesses componentes podem exigir adaptação.

## Desenvolvimento

Use o checkout existente: as tarefas em nuvem são isoladas; não crie worktrees sem solicitação. Python 3.12 e Node.js 24 são usados nos testes. Para executar a interface pelo código-fonte:

```sh
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -r requirements-desktop.txt
.venv\Scripts\python programa.py
```

Testes:

```sh
python -m unittest discover -s tests -p test_desktop.py
node tests/wizard.test.js
node tests/confirmation.test.js
node tests/browser.test.js
.venv/bin/python -m unittest discover -s tests -p test_playwright_navigation.py
```

O teste `tests/browser.test.js` requer Chromium em `/usr/bin/chromium` ou `CHROMIUM_PATH`. Usa CDP por pipe e página sintética em memória, sem navegação externa nem scripts dos anexos. Pode requerer permissão de execução fora do sandbox. A interface gráfica Windows não é validada por esse teste Linux.

O teste `test_playwright_navigation.py` usa Playwright 1.55.0 (instalado pelo `requirements-desktop.txt`) e Chrome no Windows, ou Chromium no Linux. Executa a inicialização JavaScript por `Frame.evaluate`, a seleção do perfil e o caminho escola/turma em páginas locais, incluindo um iframe. Ele cobre a chamada real que falhava antes de identificar o perfil; os testes de DOM isolados não detectavam esse erro. No Windows, use `.venv\\Scripts\\python` no lugar de `.venv/bin/python`.

Para compilar no Windows: instale `pyinstaller==6.11.1` além de `requirements-desktop.txt` e execute `python desktop/build_windows.py`. O workflow também executa `RegistroDeAulas.exe --self-test` para validar Tcl, recursos embarcados e Chrome em uma página local antes de disponibilizar o artefato.
