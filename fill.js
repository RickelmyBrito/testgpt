globalThis.preencherAula = async function (aula) {
  if(!globalThis.PortalAulas)return 'Adaptador do portal não carregado.';
  const p=PortalAulas;
  if(![...document.querySelectorAll('label')].some(el=>p.norm(el.textContent)==='conteudo abordado'))return null;
  const batch=JSON.parse(sessionStorage.getItem('assistente-aulas-lote') || 'null');
  if(batch && batch.id!==aula.batchId)return 'Há um lote em execução. Aguarde ou interrompa antes de iniciar uma aula separada.';
  try {
    const previous=JSON.parse(sessionStorage.getItem('assistente-aulas-resultado') || 'null');
    if(previous && previous.data===aula.data && p.time(previous.horario)===p.time(aula.horario) && p.norm(previous.turma)===p.norm(aula.turma) && p.norm(previous.disciplina)===p.norm(aula.disciplina))return 'Esta aula já foi localizada como enviada nesta sessão. Confira a lista do portal antes de tentar outro registro.';
  }catch{return 'Não foi possível ler o resultado anterior. Confira a lista antes de reenviar.';}
  const busyKey='assistente-aulas-preenchimento';
  if(sessionStorage.getItem(busyKey) || sessionStorage.getItem('assistente-aulas-fluxo'))return 'Já existe uma execução pendente. Consulte o resultado ou interrompa antes de iniciar outra aula.';
  const token=crypto.randomUUID();
  sessionStorage.setItem(busyKey,token);
  const check=()=>{if(sessionStorage.getItem(busyKey)!==token)throw Error('Preenchimento interrompido.');};
  try {
    p.assertIdentity(aula);
    if(!aula.conteudo?.trim() || !aula.metodologia?.trim())throw Error('Informe conteúdo e metodologia.');
    await p.choose('Tipo de Aula','Aula Normal',check);
    await p.chooseDate(aula.data,check);
    await p.choose('Horário (inicial ~ final)',aula.horario,check);
    for(const [name,text] of [['Conteúdo abordado',aula.conteudo],['Estratégia metodológica',aula.metodologia]]) {
      const el=p.field(name);if(el.disabled || el.readOnly)throw Error('Campo indisponível: '+name);
      p.setText(el,text);
      await p.wait(()=>p.value(p.field(name))===text,check);
    }
    check();p.assertIdentity(aula);
    const date=p.value(p.field('Data')).trim();
    if(date!==aula.data && date!==aula.data.split('-').reverse().join('/'))throw Error('Data não confirmada no formulário.');
    if(p.time(p.value(p.field('Horário (inicial ~ final)')))!==p.time(aula.horario))throw Error('Horário não confirmado.');
    const save=await p.seek(()=>p.findButton('Salvar e Avançar'),check);
    if(typeof globalThis.confirmarEnvioAula!=='function')throw Error('Módulo de salvamento não identificado.');
    if(globalThis.localizarConfirmacaoAula())throw Error('Já existe uma confirmação aberta. Não será feito outro envio.');
    sessionStorage.removeItem('assistente-aulas-resultado');
    sessionStorage.setItem('assistente-aulas-fluxo',JSON.stringify({stage:'plano de aula',awaiting:null,expiry:Date.now()+45000,aula:{data:aula.data,horario:aula.horario,turma:aula.turma,disciplina:aula.disciplina}}));
    p.press(save);return await globalThis.confirmarEnvioAula(check);
  } catch(error) {
    return 'Execução interrompida: '+error.message+' Confira os campos antes de repetir.';
  } finally {if(sessionStorage.getItem(busyKey)===token)sessionStorage.removeItem(busyKey);}
};
