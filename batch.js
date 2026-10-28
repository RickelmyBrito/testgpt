/* Sequential month runner. Every result must be found in the lesson table. */
globalThis.LoteAulas = (()=>{
  const key='assistente-aulas-lote';
  const p=()=>globalThis.PortalAulas;
  let running=false;
  const read=()=>JSON.parse(sessionStorage.getItem(key)||'null');
  const save=state=>sessionStorage.setItem(key,JSON.stringify(state));
  const status=text=>sessionStorage.setItem('assistente-aulas-status',text);
  function check(id){if(read()?.id!==id)throw Error('Lote interrompido.');}
  async function pressButton(name,id) {
    const el=await p().seek(()=>p().findButton(name),()=>check(id));
    check(id);p().press(el);
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
    const next=direction==='next';
    const patterns=next? /^(?:ir para (?:a )?)?(?:proxim[ao](?: pagina)?|pagina seguinte|seguinte|next(?: page)?|go to (?:the )?next page|pagination-next|next-page)$/ : /^(?:ir para (?:a )?)?(?:anterior(?: pagina)?|pagina anterior|previous(?: page)?|go to (?:the )?previous page|pagination-previous|previous-page)$/;
    const controls=[...document.querySelectorAll('button,a,[role="button"]')].filter(p().visible);
    const matches=controls.filter(el=>{
      const names=[el.getAttribute('aria-label'),el.title,p().text(el),el.getAttribute('data-testid')].map(label=>p().norm(label).replace(/^[‹›«»<>←→\s]+|[‹›«»<>←→\s]+$/g,''));
      return names.some(text=>patterns.test(text));
    });
    if(matches.length>1)throw Error('Paginação ambígua.');
    if(matches.length===1)return matches[0];
    const table=tableSnapshot()?.table;
    if(!table)return null;
    const afterTable=el=>!table.contains(el) && Boolean(el.compareDocumentPosition(table)&Node.DOCUMENT_POSITION_PRECEDING);
    function arrow(el,forward) {
      const glyph=p().norm(el.textContent);
      const names=forward?['›','>','→','chevron_right','navigate_next','keyboard_arrow_right','arrow_forward_ios']:['‹','<','←','chevron_left','navigate_before','keyboard_arrow_left','arrow_back_ios'];
      return names.includes(glyph) || Boolean(el.querySelector(forward?'svg.lucide-chevron-right,svg.lucide-arrow-right,[data-lucide="chevron-right"]':'svg.lucide-chevron-left,svg.lucide-arrow-left,[data-lucide="chevron-left"]'));
    }
    const iconMatches=new Set();
    for(const el of controls.filter(el=>afterTable(el) && arrow(el,next))) {
      let parent=el.parentElement;
      for(let depth=0;parent && depth<4;depth++,parent=parent.parentElement) {
        if(['BODY','HTML'].includes(parent.tagName))break;
        const group=controls.filter(item=>parent.contains(item) && afterTable(item));
        if(group.length>16)break;
        if(!group.some(item=>arrow(item,!next)))continue;
        let common=parent;let near=false;
        for(let i=0;common && i<4;i++,common=common.parentElement)if(common.contains(table)){near=true;break;}
        if(near || /pagina|page|registros|itens/.test(p().norm(parent.textContent))){iconMatches.add(el);break;}
      }
    }
    if(iconMatches.size>1)throw Error('Mais de uma seta de paginação foi encontrada.');
    if(iconMatches.size===1)return [...iconMatches][0];
    const active=[...document.querySelectorAll('[aria-current="page"],.pagination .active,[data-state="active"],[aria-selected="true"]')]
      .filter(p().visible).filter(el=>afterTable(el) && /^\d+$/.test(p().text(el)));
    const numeric=new Set();
    for(const current of active) {
      const number=Number(p().text(current))+(next?1:-1);
      if(number<1)continue;
      let parent=current.parentElement;
      for(let depth=0;parent && depth<4;depth++,parent=parent.parentElement) {
        if(['BODY','HTML'].includes(parent.tagName))break;
        const group=controls.filter(el=>parent.contains(el) && afterTable(el) && /^\d+$/.test(p().text(el)));
        if(group.length<2)continue;
        for(const candidate of group.filter(el=>Number(p().text(el))===number))numeric.add(candidate);
        break;
      }
    }
    if(numeric.size>1)throw Error('Página numérica ambígua.');
    return numeric.size===1?[...numeric][0]:null;
  }
  const disabled=el=>!el || el.disabled || el.getAttribute('aria-disabled')==='true';
  async function turn(el,old,id) {
    check(id);p().press(el);
    return p().wait(()=>{const current=tableSnapshot();return current && JSON.stringify(current.rows)!==JSON.stringify(old.rows)?current:null;},()=>check(id));
  }
  async function scan(id) {
    let current=await p().seek(tableSnapshot,()=>check(id));
    let back=pagination('previous');
    for(let count=0;!disabled(back);count++) {
      if(count>=100)throw Error('Muitas páginas na consulta.');
      current=await turn(back,current,id);back=pagination('previous');
    }
    const rows=[],seen=new Set();
    let footerTotal=null;
    for(let count=0;count<100;count++) {
      check(id);
      const fingerprint=JSON.stringify(current.rows);
      if(seen.has(fingerprint))throw Error('Paginação repetida; consulta interrompida.');
      seen.add(fingerprint);
      const range=p().norm(document.body.innerText).match(/mostrando\s*(\d+)\s*a\s*(\d+)\s*de\s*(\d+)\s*registros?/);
      if(range) {
        const start=Number(range[1]),end=Number(range[2]),total=Number(range[3]);
        if(footerTotal!==null && footerTotal!==total)throw Error('O total da lista mudou durante a consulta. Confira os registros antes de reiniciar.');
        footerTotal=total;
        if(total===0) {
          if(start!==0 || end!==0 || current.rows.length!==0)throw Error('A contagem da lista vazia não corresponde ao rodapé.');
        } else if(start!==rows.length+1 || end-start+1!==current.rows.length)throw Error('A paginação não percorreu os registros em sequência. Nenhuma aula será enviada.');
      } else if(footerTotal!==null)throw Error('O rodapé da lista não foi encontrado durante a paginação.');
      rows.push(...current.rows);
      const next=pagination('next');
      if(disabled(next)) {
        // Unknown pagination cannot establish that all records were inspected.
        const pageText=p().norm(document.body.textContent).match(/pagina\s+(\d+)\s+de\s+(\d+)/);
        const text=p().norm(document.body.innerText);
        const counts=['confirmadas','aguardando confirmacao','rejeitadas'].map(label=>text.match(new RegExp('(?:^|\\s)(\\d+)\\s*aulas '+label)));
        const knownTotal=counts.every(Boolean)?counts.reduce((sum,match)=>sum+Number(match[1]),0):null;
        const expectedTotal=footerTotal??knownTotal;
        if(footerTotal!==null && knownTotal!==null && footerTotal<knownTotal)throw Error('A lista pode estar filtrada: o rodapé contém menos aulas que os totais da turma. Nenhuma nova aula será enviada.');
        if(expectedTotal!==null && rows.length!==expectedTotal)throw Error('Consulta incompleta: '+rows.length+' de '+expectedTotal+' aulas lidas. A paginação pode não ter sido reconhecida ou há filtros ativos. Nenhuma nova aula será enviada.');
        if(expectedTotal===null && !next && !(pageText && Number(pageText[2])===1))throw Error('Não foi possível comprovar que a consulta inclui todas as aulas.');
        return {headers:current.headers,rows};
      }
      current=await turn(next,current,id);
    }
    throw Error('Consulta excedeu o limite de páginas.');
  }
  async function reachList(id) {
    const table=tableSnapshot();
    if(table){p().reveal(table.table);return;}
    const content=[...document.querySelectorAll('label')].some(el=>p().norm(el.textContent)==='conteudo abordado');
    if(!content){await p().seek(tableSnapshot,()=>check(id));return;}
    // Only discard a pristine, empty content form during initial setup.
    p().assertIdentity(read().config);
    if(p().value(p().field('Conteúdo abordado')).trim() || p().value(p().field('Estratégia metodológica')).trim())throw Error('Abra a lista de aulas ou um formulário vazio antes de iniciar o mês.');
    const type=p().norm(p().value(p().field('Tipo de Aula')));
    if(type!=='selecione' || p().norm(p().value(p().field('Data')))!=='escolha uma data')throw Error('Há uma aula em edição. Termine ou cancele manualmente antes de iniciar o mês.');
    check(id);await pressButton('Cancelar',id);
    await p().seek(tableSnapshot,()=>check(id));
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
        if(!tableSnapshot())await p().seek(tableSnapshot,()=>check(state.id));
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
        await pressButton('Adicionar aula',state.id);
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
