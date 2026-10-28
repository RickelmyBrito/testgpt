const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../wizard.js'),'utf8');
test('identifica somente a etapa atual pelo breadcrumb e mantém a ordem',()=>{
  const c=vm.createContext({});vm.runInContext(source,c);
  assert.equal(c.FluxoAula.stageFromBreadcrumb('Registro de Aula / Frequência'),'frequencia');
  assert.equal(c.FluxoAula.stageFromBreadcrumb('Conteúdo Plano de aula Frequência Atividade'),null);
  assert.equal(c.FluxoAula.next('atividade'),'aguardando resultado');
  assert.throws(()=>c.FluxoAula.next('notas'));
});
test('avança sem editar frequência, não repete clique e não declara sucesso ao finalizar',()=>{
  const store=new Map([['assistente-aulas-fluxo',JSON.stringify({stage:'frequencia',expiry:Date.now()+10000})]]);
  let tick,clicks=0,breadcrumb='Registro de Aula / Frequência',label='Salvar e Avançar';
  const button={get textContent(){return label;},getClientRects:()=>[1],getAttribute:()=>null,click:()=>clicks++};
  const c=vm.createContext({sessionStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},
    localizarConfirmacaoAula:()=>null,setInterval:fn=>{tick=fn;},document:{querySelectorAll:selector=>selector==='table'?[]:selector.startsWith('.breadcrumb')?[{textContent:breadcrumb,getClientRects:()=>[1],getAttribute:()=>null}]:[button]}});
  vm.runInContext(source,c);tick();assert.equal(clicks,1);
  breadcrumb='Registro de Aula / Recursos didáticos';tick();tick();assert.equal(clicks,2);
  breadcrumb='Registro de Aula / Atividade';label='Salvar e Finalizar';tick();tick();assert.equal(clicks,3);
  assert.equal(JSON.parse(store.get('assistente-aulas-fluxo')).stage,'aguardando resultado');
  assert.match(store.get('assistente-aulas-status'),/aguardando comprovação/);
});
test('comprova o registro específico com situação pendente, sem confundir com aprovação',()=>{
  const c=vm.createContext({});vm.runInContext(source,c);
  const headers=['Data da Aula','Horário (inicial ~ final)','Turma','Componente','Situação'];
  const row=['05/10/2026','08:00 às 09:00','Turma B','MATEMÁTICA','Aula aguardando confirmação'];
  const aula={data:'2026-10-05',horario:'08:00 - 09:00',turma:'Turma B',disciplina:'Matemática'};
  assert.equal(c.FluxoAula.lessonResult(headers,[row],aula),'aguardando confirmação');
  assert.equal(c.FluxoAula.lessonResult(headers,[row],{...aula,data:'2026-10-06'}),null);
  assert.equal(c.FluxoAula.lessonResult(headers,[row],{...aula,disciplina:'Física'}),null);
  assert.equal(c.FluxoAula.lessonResult(headers,[row,row],aula),'duplicado');
  assert.equal(c.FluxoAula.lessonResult(headers,[[...row.slice(0,4),'Aula confirmada']],aula),'confirmada');
  assert.equal(c.FluxoAula.lessonResult(headers,[[...row.slice(0,4),'Outra situação']],aula),'situação desconhecida');
  const shortRow=['05/10/2026','9:20 às 10:20','Turma B','MATEMÁTICA','Aula aguardando confirmação'];
  assert.equal(c.FluxoAula.lessonResult(headers,[shortRow],{...aula,horario:'09:20 - 10:20'}),'aguardando confirmação');
});
