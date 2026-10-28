globalThis.FluxoAula = (() => {
  const stages=['plano de aula','frequencia','recursos didaticos','atividade'];
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  function stageFromBreadcrumb(text) {
    const clean=norm(text).replace(/\s*\/\s*/g,' ');
    return stages.find(stage=>clean==='registro de aula '+stage) || null;
  }
  function next(stage) {
    const index=stages.indexOf(stage);
    if(index<0)throw Error('Etapa desconhecida.');
    return stages[index+1] || 'aguardando resultado';
  }
  function lessonResult(headers,rows,aula) {
    if(!aula)return null;
    const h=headers.map(norm);
    const columns=['data da aula','horario (inicial ~ final)','turma','componente','situacao'].map(name=>h.indexOf(name));
    if(columns.some(index=>index<0))return null;
    const time=value=>{
      const values=String(value).match(/\b\d{1,2}:\d{2}\b/g)||[];
      if(values.length!==2 || values.some(v=>{const [h,m]=v.split(':').map(Number);return h>23 || m>59;}))return '';
      return values.map(v=>v.padStart(5,'0')).join('-');
    };
    const expectedTime=time(aula.horario);
    if(!/^\d{2}:\d{2}-\d{2}:\d{2}$/.test(expectedTime))return null;
    const expectedDate=aula.data.split('-').reverse().join('/');
    const [d,t,c,s,status]=columns;
    const found=rows.filter(row=>String(row[d]).trim()===expectedDate && time(row[t])===expectedTime && norm(row[c])===norm(aula.turma) && norm(row[s])===norm(aula.disciplina));
    if(found.length>1)return 'duplicado';
    if(found.length!==1)return null;
    const situation=norm(found[0][status]);
    if(situation.includes('aguardando confirmacao'))return 'aguardando confirmação';
    if(situation==='aula confirmada' || situation==='confirmada')return 'confirmada';
    if(situation.includes('rejeitada'))return 'rejeitada';
    return 'situação desconhecida';
  }
  return {stages,norm,stageFromBreadcrumb,next,lessonResult};
})();
if(typeof document!=='undefined' && !globalThis.assistenteWizardInstalled) {
  globalThis.assistenteWizardInstalled=true;
  (()=>{
    const key='assistente-aulas-fluxo';
    let busy=false;
    const visible=el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true';
    const status=message=>sessionStorage.setItem('assistente-aulas-status',message);
    function tick() {
      if(busy)return;
      busy=true;
      try {
        const raw=sessionStorage.getItem(key);if(!raw)return;
        const state=JSON.parse(raw);
        if(!Number.isFinite(state.expiry) || state.expiry<Date.now()) {
          sessionStorage.removeItem(key);status('Fluxo interrompido por tempo limite. Confira a situação no portal antes de reenviar.');return;
        }
        if(state.stage==='aguardando resultado') {
          for(const table of document.querySelectorAll('table')) {
            if(!visible(table))continue;
            const headers=[...table.querySelectorAll('thead th')].map(el=>el.textContent);
            const rows=[...table.querySelectorAll('tbody tr')].map(row=>[...row.querySelectorAll('td')].map(el=>el.textContent));
            const result=FluxoAula.lessonResult(headers,rows,state.aula);
            if(!result)continue;
            sessionStorage.removeItem(key);
            if(!['aguardando confirmação','confirmada'].includes(result)) {
              status('Execução interrompida: registro '+result+'. Confira a lista no portal.');return;
            }
            sessionStorage.setItem('assistente-aulas-resultado',JSON.stringify({...state.aula,situacao:result}));
            status('Registro localizado na lista: '+result+'. Data, horário, turma e disciplina conferidos.');return;
          }
        }
        const stages=[...document.querySelectorAll('.breadcrumb,[aria-label="breadcrumb"],[aria-label="Breadcrumb"]')]
          .filter(visible).map(el=>FluxoAula.stageFromBreadcrumb(el.textContent)).filter(Boolean);
        const stage=stages.length===1?stages[0]:null;
        if(stage===state.stage) {
          sessionStorage.removeItem('assistente-aulas-preenchimento');
          const label=stage==='atividade'?'salvar e finalizar':'salvar e avancar';
          const buttons=[...document.querySelectorAll('button,input[type="submit"]')].filter(visible)
            .filter(el=>FluxoAula.norm(el.textContent || el.value)===label);
          if(buttons.length!==1 || globalThis.localizarConfirmacaoAula())return;
          state.awaiting=stage;state.stage=FluxoAula.next(stage);state.expiry=Date.now()+45000;
          sessionStorage.setItem(key,JSON.stringify(state));
          status(stage==='atividade'?'Finalização enviada; aguardando comprovação no portal.':'Avançando: '+stage+'.');
          buttons[0].click();return;
        }
        if(state.awaiting) {
          const button=globalThis.localizarConfirmacaoAula();
          if(button) {state.awaiting=null;sessionStorage.setItem(key,JSON.stringify(state));button.click();}
        }
      } catch {
        sessionStorage.removeItem(key);status('Fluxo interrompido por erro. Confira o registro no portal antes de repetir.');
      } finally {busy=false;}
    }
    setInterval(tick,350);tick();
  })();
}
