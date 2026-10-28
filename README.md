# Assistente de Registro de Aulas

Extensão Chrome Manifest V3 para preparar registros no iSEDUC da SEDUC-PI. Não usa servidor próprio nem recebe senhas fora do navegador do usuário.

## Uso no Windows

1. Extraia o pacote para uma pasta permanente.
2. Em `chrome://extensions`, ative **Modo do desenvolvedor** e use **Carregar sem compactação** para selecionar a pasta com `manifest.json`. Após atualizar os arquivos, clique em **Recarregar** na extensão e atualize a aba do portal.
3. Abra `https://portal.seduc.pi.gov.br/`. Na extensão, informe usuário e senha em **Entrar no portal**. As credenciais são preenchidas na página oficial e não são armazenadas pela extensão. CAPTCHA e verificações adicionais são concluídos no navegador.
4. A seleção do perfil Professor(a) é tentada após o login solicitado pela extensão. Abra a escola e **Registro de aulas** da turma/disciplina. Essas escolhas ainda são manuais.
5. Informe turma exatamente como aparece no portal, disciplina, mês/ano, dias da semana, horários e dias sem aula. Para vários horários no mesmo dia, separe com `;`. Os dias sem aula podem ser números, como `7, 12, 21`, ou datas completas do mesmo mês.
6. Clique em **Preparar lista de aulas**, abra **Adicionar aula** no portal e use **Preencher e salvar** na aula desejada.
7. Para executar o mês sem iniciar cada aula, use **Registrar mês automaticamente** na lista da turma com filtros limpos, ou num formulário novo completamente vazio. A rotina consulta as páginas reconhecidas da tabela e compara o total com os contadores; se a lista estiver parcial, interrompe antes de enviar. Pula aulas já registradas e processa as demais sequencialmente, aguardando a comprovação de cada uma.
8. O programa tenta preencher Aula Normal, data, horário, conteúdo e metodologia e confirmar o envio. Em seguida tenta avançar por Plano de aula, Frequência e Recursos didáticos e clicar em Salvar e Finalizar em Atividade. Não adiciona planos, recursos ou atividades.
9. Use **Consultar resultado** para verificar o andamento. O registro só é identificado como salvo quando uma linha da tabela corresponde a data, horário, turma, disciplina e situação. Aguardando confirmação significa enviado, pendente de confirmação da escola.

**Salvar é automático ao iniciar uma aula.** Não use registros reais para ensaios sem intenção de enviá-los. O lote não reenvia automaticamente uma aula com resultado incerto, rejeitado ou duplicado. Na frequência a rotina não altera os controles, mas pode gravar os valores já exibidos, conforme autorizado pelo usuário. Notas não são acessadas. Competências, habilidades e objetivos ficam intactos.

**Parar avanço automático** cancela as próximas ações. Solicitações já enviadas não são desfeitas. Se houver interrupção, confira a lista no portal antes de repetir: um conteúdo pode ter sido gravado antes de o fluxo terminar.

## Compatibilidade e limites

A versão 2.0 usa o HTML de conteúdo fornecido pelo usuário: rótulos sem associação `for`, botões Radix com `role=combobox` e calendário em popover. Ela localiza o quadro em `seduc-academico-prod.seduc.pi.gov.br`, em vez de procurar os campos na página externa do portal. Permissões são limitadas aos dois domínios HTTPS oficiais.

A seleção de listas segue `aria-controls` e opções `role=option`; IDs temporários não são fixados. O calendário suporta cabeçalhos DayPicker em português/inglês, navegação mês a mês e dias habilitados. O HTML recebido não inclui o calendário aberto: sua estrutura interna ainda depende de validação no portal. Valores são conferidos antes de enviar. Se um controle não for reconhecido, a execução para.

A rotina de etapas identifica o breadcrumb e confirma apenas o diálogo conhecido após o próprio clique. Há tempo limite por etapa. Não declara sucesso somente pelo aumento de um contador ou pelo clique final. No envio individual, uma linha oculta por filtros ou em outra página não confirma o resultado. No lote, a rotina consulta a paginação reconhecida; filtros que escondem registros impedem o início.

**A escolha da escola e da turma após o login continua manual.** O lote mensal funciona a partir da lista da turma ou de um formulário novo vazio. A paginação é suportada quando os botões expõem nomes como Próxima página/Página anterior ou Next page/Previous page. Sem comprovação da consulta completa, a rotina interrompe. Mantenha a aba aberta e não a utilize para outras aulas enquanto o lote estiver ativo. A integração autenticada completa não foi testada; testes locais não comprovam gravação no portal.

## Dados locais

A grade e os textos ficam no armazenamento local da extensão. Metadados do fluxo e seu resultado ficam no armazenamento de sessão da aba acadêmica. Nenhum dado é enviado a serviços próprios. Credenciais não são persistidas. Para remover a grade, desinstale a extensão; para encerrar a sessão no portal, use a opção Sair do próprio sistema.

## Desenvolvimento e validação

Use o checkout existente. As tarefas em nuvem já são isoladas: não crie worktrees sem solicitação. Não há instalação de dependências ou build.

Execute os testes com Node.js 24:

```sh
node tests/schedule.test.js
node tests/login.test.js
node tests/profile.test.js
node tests/confirmation.test.js
node tests/wizard.test.js
node tests/browser.test.js
```

O último teste usa Chromium local (`/usr/bin/chromium`, ou a variável `CHROMIUM_PATH`), um perfil temporário e controle CDP por pipe. Não acessa o portal. Usa somente uma fixture sanitizada da estrutura dos campos, com eventos simulados para as listas e calendário; não executa scripts do HTML enviado nem inclui parâmetros de identidade ou dados de alunos. No ambiente restrito, iniciar o Chromium pode precisar da permissão de execução correspondente.
