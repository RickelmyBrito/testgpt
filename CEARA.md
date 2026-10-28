# Plano de Ensino SEDUC-CE — 1.0.0

Programa independente do registro de aulas do Piauí. No Windows, instale Python 3.12 e Google Chrome, extraia o ZIP e abra **Abrir Programa Ceara.cmd**. A primeira abertura instala as dependências na pasta local `.venv-ce`.

Selecione ano, turma, disciplina e bimestre, escolha o PDF e informe eventuais dias sem aula. **Ler PDF** monta um conteúdo e subconteúdo por encontro de quarta e quinta. **Exportar CSV** permite ler os textos completos em uma planilha. **Iniciar** abre o Chrome. O login gov.br é realizado por você no navegador, inclusive senha, CAPTCHA ou código; ao retornar ao Professor Online, clique em **Continuar após login**.

O programa abre Diário Online → Plano de ensino, busca a turma/disciplina, adiciona os itens sequencialmente e verifica cada par de textos na lista do período. Uma data no subconteúdo identifica cada encontro e permite pular itens já enviados pelo programa. Itens antigos sem essa identificação não são considerados equivalentes. O programa não exclui itens nem mexe em frequência, notas ou registro de aulas.

O importador lê tabelas com intervalo semanal na primeira coluna e objetos do conhecimento na terceira, como o alinhamento enviado. Distribui os tópicos na ordem do PDF, em blocos por encontro; não usa IA externa nem inventa tópicos. Respeita avaliações com data explícita. Não presume feriados fora do arquivo; use dias sem aula. PDFs escaneados ou outros formatos são recusados com mensagem. Os textos podem precisar de ajustes pedagógicos; a planilha mostra a divisão feita.

Validado localmente com o PDF fornecido (21 encontros) e páginas simuladas. Ainda não validado numa sessão autenticada da SEDUC-CE: as imagens não revelam todos os seletores HTML. Caso um campo não seja reconhecido, o programa interrompe e informa a tela. Um salvamento sem confirmação também interrompe o lote, sem reenviar. Nesse caso confira o portal antes de reiniciar. O Chrome permanece aberto até **Parar e fechar Chrome**.

As credenciais não são solicitadas pelo programa nem salvas por ele. O PDF é processado localmente. Não compartilhe HTML contendo tokens ou dados de sessão.

Testes: `.venv/bin/python -m unittest tests.test_ceara -v` (ou `python -m unittest discover -s tests -p 'test_ceara.py' -v`).
