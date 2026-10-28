const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawn}=require('node:child_process');

test('preenche controles personalizados em Chromium com a estrutura real sanitizada',async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aulas-browser-'));
  const root=path.resolve(__dirname,'..');
  const fixture=fs.readFileSync(path.join(__dirname,'fixtures/registro-conteudo.html'),'utf8');
  const script=name=>'<script>'+fs.readFileSync(path.join(root,name),'utf8')+'</script>';
  const html='<!doctype html><meta charset="utf-8"><body><main>'+fixture+'</main><pre id="report"></pre><script>window.addEventListener("error",e=>{document.getElementById("report").textContent="FAIL "+e.message;});const storage=new Map();Object.defineProperty(window,"sessionStorage",{value:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)}});if(!crypto.randomUUID)crypto.randomUUID=()=>String(Math.random());</script>'+script('portal.js')+script('fill.js')+script('wizard.js')+script('batch.js')+script('desktop/navigation.js')+`<script>
  const outcomes=[];
  const assert=(ok,message)=>{if(!ok)throw Error(message);};
  const p=PortalAulas;
  let saves=0,inputEvents=0,calendarMonth=8;
  const timeButton=p.field('Horário (inicial ~ final)');
  function menu(name,options) {
    const trigger=p.field(name);
    trigger.onclick=()=>{
      const list=document.createElement('div');list.id=trigger.getAttribute('aria-controls');list.role='listbox';
      for(const text of options) {
        const option=document.createElement('div');option.role='option';option.tabIndex=0;option.textContent=text;
        option.onclick=()=>{trigger.textContent=text;list.remove();};list.append(option);
      }
      document.body.append(list);
    };
  }
  menu('Tipo de Aula',['Aula Normal','Reposição']);
  menu('Horário (inicial ~ final)',['9:20 - 10:20','10:20 - 11:20']);
  const dateButton=p.field('Data');
  const monthNames=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
  function renderCalendar() {
    document.getElementById(dateButton.getAttribute('aria-controls'))?.remove();
    const calendar=document.createElement('div');calendar.id=dateButton.getAttribute('aria-controls');calendar.role='dialog';
    const root=document.createElement('div');root.className='rdp';calendar.append(root);
    const caption=document.createElement('div');caption.className='text-sm font-medium';caption.setAttribute('aria-live','polite');caption.textContent=monthNames[calendarMonth]+' 2026';root.append(caption);
    for(const [name,delta] of [['previous-month',-1],['next-month',1]]) {
      const button=document.createElement('button');button.name=name;button.textContent=name;button.onclick=()=>{calendarMonth+=delta;renderCalendar();};root.append(button);
    }
    const outside=document.createElement('button');outside.className='day-outside';outside.textContent='5';root.append(outside);
    for(let i=1;i<=31;i++) {
      const day=document.createElement('button');day.textContent=String(i);
      day.onclick=()=>{
        dateButton.textContent=String(i).padStart(2,'0')+'/'+String(calendarMonth+1).padStart(2,'0')+'/2026';calendar.remove();
        timeButton.disabled=true;setTimeout(()=>{timeButton.disabled=false;},120);
      };root.append(day);
    }
    document.body.append(calendar);
  }
  dateButton.onclick=renderCalendar;
  p.field('Conteúdo abordado').addEventListener('input',()=>inputEvents++);
  const save=document.createElement('button');save.textContent='Salvar e Avançar';save.onclick=()=>saves++;document.body.append(save);
  globalThis.localizarConfirmacaoAula=()=>null;
  globalThis.confirmarEnvioAula=async()=> 'envio simulado';
  (async()=>{
    const aula={data:'2026-10-05',horario:'09:20 às 10:20',turma:'Turma Exemplo',disciplina:'Matemática',conteudo:'Conteúdo de exemplo',metodologia:'Metodologia de exemplo'};
    assert(p.field('Turma').disabled,'lê turma desabilitada');
    const wrong=await preencherAula({...aula,disciplina:'Física'});
    assert(wrong.includes('disciplina') && saves===0,'não envia na disciplina errada');outcomes.push('disciplina');
    const result=await preencherAula(aula);
    assert(result==='envio simulado','preenchimento completou: '+result);
    assert(saves===1,'somente um envio');
    assert(inputEvents===1,'evento de edição disparado');
    assert(p.value(p.field('Data'))==='05/10/2026','navegação entre meses e seleção da data');
    assert(p.value(p.field('Horário (inicial ~ final)'))==='9:20 - 10:20','horário equivalente selecionado mesmo sem zero inicial no portal');
    assert(p.value(p.field('Conteúdo abordado'))===aula.conteudo,'conteúdo preenchido');
    assert(p.field('Competência Específica').textContent.trim()==='Selecione','competências preservadas');
    outcomes.push('data','horário','textos','envio único','currículo preservado');
    const repeat=await preencherAula(aula);assert(repeat.includes('pendente') && saves===1,'impede execução concorrente');outcomes.push('concorrência');
    sessionStorage.removeItem('assistente-aulas-fluxo');
    let cancelled=false;
    try{await p.choose('Tipo de Aula','Outra',()=>{throw Error('parado');});}catch(e){cancelled=e.message==='parado';}
    assert(cancelled,'cancelamento durante espera');outcomes.push('cancelamento');
    // Test month orchestration separately: the real field adapter was exercised above.
    // Saving is simulated here, never sent to a remote service.
    document.querySelectorAll('[role="listbox"]').forEach(el=>el.remove());
    const formFixture=${JSON.stringify(fixture)};
    let adds=0;
    const existing=['05/10/2026','08:00 às 09:00','Turma Exemplo','MATEMÁTICA','Aula confirmada'];
    const created=['12/10/2026','08:00 às 09:00','Turma Exemplo','MATEMÁTICA','Aula aguardando confirmação'];
    function list(rows,total=rows.length) {
      const main=document.querySelector('main');main.replaceChildren();
      const summary=document.createElement('div');summary.textContent='1 Aulas confirmadas '+(total-1)+' Aulas aguardando confirmação 0 Aulas rejeitadas';main.append(summary);
      const table=document.createElement('table'),head=document.createElement('thead'),header=document.createElement('tr');
      for(const text of ['Data da Aula','Horário (inicial ~ final)','Turma','Componente','Situação']){const th=document.createElement('th');th.textContent=text;header.append(th);}head.append(header);table.append(head);
      const body=document.createElement('tbody');for(const row of rows){const tr=document.createElement('tr');for(const text of row){const td=document.createElement('td');td.textContent=text;tr.append(td);}body.append(tr);}table.append(body);main.append(table);
      const add=document.createElement('button');add.textContent='Adicionar aula';add.onclick=()=>{adds++;main.innerHTML=formFixture;};main.append(add);
    }
    globalThis.preencherAula=async item=>{
      list([existing,created]);sessionStorage.setItem('assistente-aulas-resultado',JSON.stringify({...item,situacao:'aguardando confirmação'}));return 'envio simulado';
    };
    list([existing]);
    LoteAulas.start(aula,[{data:'2026-10-05',horario:'08:00 - 09:00'},{data:'2026-10-12',horario:'08:00 - 09:00'}]);
    for(let i=0;i<100 && sessionStorage.getItem('assistente-aulas-lote');i++){await LoteAulas.run();await new Promise(r=>setTimeout(r,20));}
    assert((sessionStorage.getItem('assistente-aulas-status')||'').startsWith('Mês concluído'),'lote concluiu: '+sessionStorage.getItem('assistente-aulas-status'));
    assert(adds===1,'pula aula já existente e abre somente a nova');
    const completed=JSON.parse(sessionStorage.getItem('assistente-aulas-lote-concluido'));
    assert(completed[0].done==='já registrado' && completed[1].done==='aguardando confirmação','situações distintas preservadas');outcomes.push('lote mensal','aulas existentes');
    list([existing,created],3);
    LoteAulas.start(aula,[{data:'2026-10-19',horario:'08:00 - 09:00'}]);
    for(let i=0;i<100 && sessionStorage.getItem('assistente-aulas-lote');i++){await LoteAulas.run();await new Promise(r=>setTimeout(r,20));}
    assert((sessionStorage.getItem('assistente-aulas-status')||'').includes('parcial'),'recusa lista parcial');assert(adds===1,'lista parcial não inicia nova aula');outcomes.push('consulta parcial bloqueada');
    function pages(index) {
      list([index===0?existing:created],2);
      const main=document.querySelector('main');
      const caption=document.createElement('p');caption.textContent='Página '+(index+1)+' de 2';main.append(caption);
      const previous=document.createElement('button');previous.setAttribute('aria-label','Página anterior');previous.disabled=index===0;previous.onclick=()=>pages(0);
      const next=document.createElement('button');next.setAttribute('aria-label','Próxima página');next.disabled=index===1;next.onclick=()=>pages(1);main.append(previous,next);
    }
    pages(1);
    LoteAulas.start(aula,[{data:'2026-10-12',horario:'08:00 - 09:00'}]);
    for(let i=0;i<100 && sessionStorage.getItem('assistente-aulas-lote');i++){await LoteAulas.run();await new Promise(r=>setTimeout(r,20));}
    assert((sessionStorage.getItem('assistente-aulas-status')||'').startsWith('Mês concluído'),'consulta percorreu páginas: '+sessionStorage.getItem('assistente-aulas-status'));
    assert(adds===1,'aula localizada em outra página não é reenviada');outcomes.push('paginação');
    document.querySelector('main').innerHTML='<section><h3>Turma Exemplo</h3><p>Física</p><a>Registro de aulas</a></section><section><h3>Turma Exemplo</h3><p>Matemática</p><a id="math">Registro de aulas</a></section><section><h3>Escola Exemplo</h3><button id="school">Abrir</button></section>';
    assert(desktopAction({title:'Turma Exemplo',action:'Registro de aulas',discipline:'Matemática'})===document.getElementById('math'),'navegação distingue disciplina na mesma turma');
    assert(desktopAction({title:'Escola Exemplo',action:'Abrir'})===document.getElementById('school'),'navegação localiza escola');
    assert(desktopAction({title:'Turma Exemplo',action:'Registro de aulas',discipline:'Biologia'})===null,'não abre disciplina inexistente');
    document.querySelector('main').insertAdjacentHTML('beforeend','<section><h3>Turma Exemplo</h3><p>Matemática</p><a>Registro de aulas</a></section>');
    assert(desktopAction({title:'Turma Exemplo',action:'Registro de aulas',discipline:'Matemática'})===null,'não escolhe cartão ambíguo');outcomes.push('escola e turma por disciplina');
    document.getElementById('report').textContent='PASS '+outcomes.join(', ');
  })().catch(e=>{document.getElementById('report').textContent='FAIL '+e.message;});
  </script>`;
  const file=path.join(dir,'test.html');fs.writeFileSync(file,html);
  const child=spawn(process.env.CHROMIUM_PATH || '/usr/bin/chromium',[
    '--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking',
    '--no-first-run','--no-default-browser-check',
    '--user-data-dir='+path.join(dir,'profile'),'--remote-debugging-pipe'
  ],{stdio:['ignore','ignore','ignore','pipe','pipe']});
  let seq=0,buffer='';const pending=new Map();
  function call(method,params={},sessionId) {
    return new Promise((resolve,reject)=>{
      const id=++seq;
      const timer=setTimeout(()=>{pending.delete(id);reject(Error('Tempo limite CDP: '+method));},10000);
      pending.set(id,{resolve,reject,timer});
      child.stdio[3].write(JSON.stringify({id,method,params,sessionId})+'\0');
    });
  }
  child.on('error',error=>{for(const item of pending.values()){clearTimeout(item.timer);item.reject(error);}pending.clear();});
  child.stdio[4].setEncoding('utf8');
  child.stdio[4].on('data',data=>{
    buffer+=data;let end;
    while((end=buffer.indexOf('\0'))>=0) {
      const message=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);
      const item=pending.get(message.id);if(!item)continue;
      pending.delete(message.id);clearTimeout(item.timer);
      if(message.error)item.reject(Error(message.error.message));else item.resolve(message.result);
    }
  });
  try {
    await call('Browser.getVersion');
    const {targetId}=await call('Target.createTarget',{url:'about:blank'});
    const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
    const {frameTree}=await call('Page.getFrameTree',{},sessionId);
    await call('Page.setDocumentContent',{frameId:frameTree.frame.id,html},sessionId);
    let report='';const deadline=Date.now()+20000;
    while(Date.now()<deadline) {
      const response=await call('Runtime.evaluate',{expression:'document.getElementById("report")?.textContent || ""',returnByValue:true},sessionId);
      report=response.result?.value || '';
      if(report)break;
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    if(!report){const debug=await call('Runtime.evaluate',{expression:'JSON.stringify({url:location.href,ready:document.readyState,body:document.body?.textContent.slice(0,300),scripts:document.scripts.length,adapter:typeof PortalAulas})',returnByValue:true},sessionId);report='FAIL '+debug.result?.value;}
    assert.ok(report.startsWith('PASS '),report);console.log(report);
  } finally {
    await call('Browser.close').catch(()=>{});
    child.kill();
    for(const item of pending.values())clearTimeout(item.timer);
    fs.rmSync(dir,{recursive:true,force:true});
  }
});
