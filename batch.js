/* Sequential month runner. Every result must be found in the lesson table. */
globalThis.LoteAulas = (()=>{
  const key='assistente-aulas-lote';
  const p=()=>globalThis.PortalAulas;
  let running=false;
  const read=()=>JSON.parse(sessionStorage.getItem(key)||'null');
  const save=state=>sessionStorage.setItem(key,JSON.stringify(state));
  const status=text=>sessionStorage.setItem('assistente-aulas-status',text);
  function check(id){if(read()?.id!==id)throw Error('Lote interrompido.');}
  function button(name) {
    const list=[...document.querySelectorAll('button,a,[role="button"]')].filter(p().visible)
      .filter(el=>p().norm(el.textContent || el.getAttribute('aria-label'))===p().norm(name));
    if(list.length!==1 || list[0].disabled)throw Error('Ação não identificada: '+name);
    return list[0];
  }
  function tableSnapshot() {
    const tables=[...document.querySelectorAll('table')].filter(p().visible).map(table=>({
      table,headers:[...table.querySelectorAll('thead th')].map(el=>el.textContent),
      rows:[...table.querySelectorAll('tbody tr')].map(row=>[...row.querySelectorAll('td')].map(el=>el.textContent.trim()))
    })).filter(data=>data.headers.some(h=>p().norm(h)==='data da aula') && data.headers.some(h=>p().norm(h)==='situacao'));
    if(tables.length!==1)return null;
    const result=tables[0];
    if(!result.rows.length || (result.rows.length===1 && result.rows[0].length===1 && !/nenhum|no results/i.test(result.rows[0][0])))return null;
    if(result.rows[0]?.length===1)result.rows=[];
    return result;
  }
  function pagination(direction) {
    const patterns=direction==='next'? /^(?:ir para (?:a )?)?(?:proxim[ao](?: pagina)?|next(?: page)?|go to next page)$/ : /^(?:ir para (?:a )?)?(?:anterior(?: pagina)?|pagina anterior|previous(?: page)?|go to previous page)$/;
    const matches=[...document.querySelectorAll('button')].filter(p().visible).filter(el=>{
      const names=[el.getAttribute('aria-label'),el.title,el.textContent].map(p().norm);
      return names.some(text=>patterns.test(text));
    });
    if(matches.length>1)throw Error('Paginação ambígua.');
    return matches[0] || null;
  }
  const disabled=el=>!el || el.disabled || el.getAttribute('aria-disabled')==='true';
  async function turn(el,old,id) {
    check(id);p().press(el);
    return p().wait(()=>{const current=tableSnapshot();return current && JSON.stringify(current.rows)!==JSON.stringify(old.rows)?current:null;},()=>check(id));
  }
  async function scan(id) {
    let current=await p().wait(tableSnapshot,()=>check(id));
    let back=pagination('previous');
    for(let count=0;!disabled(back);count++) {
      if(count>=100)throw Error('Muitas páginas na consulta.');
      current=await turn(back,current,id);back=pagination('previous');
    }
    const rows=[],seen=new Set();
    for(let count=0;count<100;count++) {
      check(id);
      const fingerprint=JSON.stringify(current.rows);
      if(seen.has(fingerprint))throw Error('Paginação repetida; consulta interrompida.');
      seen.add(fingerprint);rows.push(...current.rows);
      const next=pagination('next');
      if(disabled(next)) {
        // Unknown pagination cannot establish that all records were inspected.
        const pageText=p().norm(document.body.textContent).match(/pagina\s+(\d+)\s+de\s+(\d+)/);
        if(!next && pageText && Number(pageText[2])>1)throw Error('A paginação da lista não é suportada.');
        const text=p().norm(document.body.innerText);
        const counts=['confirmadas','aguardando confirmacao','rejeitadas'].map(label=>text.match(new RegExp('(?:^|\\s)(\\d+)\\s*aulas '+label)));
        const knownTotal=counts.every(Boolean)?counts.reduce((sum,match)=>sum+Number(match[1]),0):null;
        if(knownTotal!==null && rows.length!==knownTotal)throw Error('A lista está parcial ou filtrada. Limpe os filtros; não é seguro iniciar com registros ocultos.');
        if(knownTotal===null && !next && !(pageText && Number(pageText[2])===1))throw Error('Não foi possível comprovar que a consulta inclui todas as aulas.');
        return {headers:current.headers,rows};
      }
      current=await turn(next,current,id);
    }
    throw Error('Consulta excedeu o limite de páginas.');
  }
  async function reachList(id) {
    if(tableSnapshot())return;
    // Only discard a pristine, empty content form during initial setup.
    p().assertIdentity(read().config);
    if(p().value(p().field('Conteúdo abordado')).trim() || p().value(p().field('Estratégia metodológica')).trim())throw Error('Abra a lista de aulas ou um formulário vazio antes de iniciar o mês.');
    const type=p().norm(p().value(p().field('Tipo de Aula')));
    if(type!=='selecione' || p().norm(p().value(p().field('Data')))!=='escolha uma data')throw Error('Há uma aula em edição. Termine ou cancele manualmente antes de iniciar o mês.');
    check(id);p().press(button('Cancelar'));
    await p().wait(tableSnapshot,()=>check(id));
  }
  async function run() {
    if(running)return;
    let state=read();if(!state)return;
    running=true;
    try {
      check(state.id);
      if(state.expiry<Date.now())throw Error('Tempo limite do lote.');
      if(state.phase==='preflight') {
        await reachList(state.id);
        const snapshot=await scan(state.id);
        state=read();check(state.id);
        for(const aula of state.aulas) {
          const found=FluxoAula.lessonResult(snapshot.headers,snapshot.rows,{...state.config,...aula});
          if(found && !['aguardando confirmação','confirmada'].includes(found))throw Error('Registro '+found+' para '+aula.data+'. Confira a lista.');
          if(found)aula.done='já registrado';
        }
        state.phase='list';save(state);
      }
      state=read();check(state.id);
      if(state.phase==='waiting') {
        const flow=JSON.parse(sessionStorage.getItem('assistente-aulas-fluxo')||'null');
        const result=JSON.parse(sessionStorage.getItem('assistente-aulas-resultado')||'null');
        const aula=state.aulas[state.index];
        if(!result && flow?.stage!=='aguardando resultado')return;
        if(!tableSnapshot())return;
        const snapshot=await scan(state.id);
        const found=FluxoAula.lessonResult(snapshot.headers,snapshot.rows,{...state.config,...aula});
        if(!['aguardando confirmação','confirmada'].includes(found))throw Error('Não foi possível comprovar um único registro salvo para '+aula.data+'. O lote não fará novo envio.');
        state=read();check(state.id);state.aulas[state.index].done=found;state.index++;state.phase='list';save(state);
        sessionStorage.removeItem('assistente-aulas-fluxo');sessionStorage.removeItem('assistente-aulas-resultado');
      }
      state=read();check(state.id);
      if(state.phase==='list') {
        while(state.index<state.aulas.length && state.aulas[state.index].done)state.index++;
        if(state.index>=state.aulas.length) {
          sessionStorage.setItem('assistente-aulas-lote-concluido',JSON.stringify(state.aulas));
          sessionStorage.removeItem(key);status('Mês concluído: '+state.aulas.filter(a=>a.done!=='já registrado').length+' aula(s) enviada(s), '+state.aulas.filter(a=>a.done==='já registrado').length+' já registrada(s). Envios aguardam confirmação da escola.');return;
        }
        state.phase='opening';state.expiry=Date.now()+120000;save(state);
        p().press(button('Adicionar aula'));
        await p().wait(()=>[...document.querySelectorAll('label')].some(el=>p().norm(el.textContent)==='conteudo abordado'),()=>check(state.id));
      }
      state=read();check(state.id);
      if(state.phase==='opening') {
        await p().wait(()=>[...document.querySelectorAll('label')].some(el=>p().norm(el.textContent)==='conteudo abordado'),()=>check(state.id));
        p().assertIdentity(state.config);
        state.phase='waiting';state.expiry=Date.now()+120000;save(state);
        status('Registrando aula '+(state.index+1)+' de '+state.aulas.length+'.');
        const message=await preencherAula({...state.config,...state.aulas[state.index],batchId:state.id});
        if(!sessionStorage.getItem('assistente-aulas-fluxo') && !sessionStorage.getItem('assistente-aulas-resultado'))throw Error(message || 'Envio não iniciado.');
      }
    } catch(error) {
      sessionStorage.removeItem(key);sessionStorage.removeItem('assistente-aulas-fluxo');sessionStorage.removeItem('assistente-aulas-preenchimento');
      status('Lote interrompido: '+error.message+' Confira a lista antes de reiniciar.');
    } finally {running=false;}
  }
  function start(config,aulas) {
    if(read() || sessionStorage.getItem('assistente-aulas-fluxo') || sessionStorage.getItem('assistente-aulas-preenchimento'))throw Error('Já existe uma execução pendente.');
    if(!aulas.length)throw Error('Nenhuma aula no mês.');
    if(aulas.some(aula=>!/^\d{2}:\d{2}-\d{2}:\d{2}$/.test(p().time(aula.horario))))throw Error('Informe os horários completos, por exemplo 08:00 - 09:00.');
    const state={id:crypto.randomUUID(),config,aulas,index:0,phase:'preflight',expiry:Date.now()+120000};
    sessionStorage.removeItem('assistente-aulas-resultado');save(state);status('Conferindo aulas existentes antes de iniciar o mês.');run();
    return 'Lote iniciado. Mantenha a aba aberta; use Consultar resultado para acompanhar.';
  }
  return {start,run,tableSnapshot};
})();
if(typeof location!=='undefined' && location.origin==='https://seduc-academico-prod.seduc.pi.gov.br' && !globalThis.assistenteBatchInstalled) {
  globalThis.assistenteBatchInstalled=true;setInterval(()=>LoteAulas.run(),700);LoteAulas.run();
}
