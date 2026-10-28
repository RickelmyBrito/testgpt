const $ = id => document.getElementById(id);
async function academicTarget(){
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  const allowed=['https://portal.seduc.pi.gov.br','https://seduc-academico-prod.seduc.pi.gov.br'];
  if(!tab?.url || !allowed.includes(new URL(tab.url).origin))throw Error('Abra a tela de registro de aulas no portal.');
  const frames=await chrome.scripting.executeScript({target:{tabId:tab.id,allFrames:true},func:()=>location.origin==='https://seduc-academico-prod.seduc.pi.gov.br' && location.pathname.startsWith('/registro-aulas/')});
  const matches=frames.filter(frame=>frame.result===true);
  if(matches.length!==1)throw Error('Abra o Registro de aulas de uma única turma. O quadro acadêmico não foi identificado de forma única.');
  return {tabId:tab.id,frameIds:[matches[0].frameId]};
}
$('consultar').onclick=async()=>{
  try{
    const target=await academicTarget();
    const [result]=await chrome.scripting.executeScript({target,func:()=>sessionStorage.getItem('assistente-aulas-status')});
    $('status').textContent=result.result || 'Nenhum andamento disponível nesta aba.';
  }catch(e){$('status').textContent=e.message;}
};
$('parar').onclick=async()=>{
  try{
    const target=await academicTarget();
    await chrome.scripting.executeScript({target,func:()=>{sessionStorage.removeItem('assistente-aulas-lote');sessionStorage.removeItem('assistente-aulas-fluxo');sessionStorage.removeItem('assistente-aulas-preenchimento');}});
    $('status').textContent='Avanço interrompido. Ações já enviadas não foram desfeitas.';
  }catch(e){$('status').textContent=e.message;}
};
$('iniciar-mes').onclick=async()=>{
  if(!$('form').reportValidity())return;
  $('iniciar-mes').disabled=true;
  try {
    await ready;
    const current=read();const aulas=Aulas.generate(current);
    const target=await academicTarget();
    await chrome.storage.local.set({config:current});
    await chrome.scripting.executeScript({target,files:['portal.js','confirmation.js','wizard.js','fill.js','batch.js']});
    const [result]=await chrome.scripting.executeScript({target,func:(c,items)=>LoteAulas.start(c,items),args:[current,aulas]});
    $('status').textContent=result.result;
  }catch(e){$('status').textContent=e.message;}
  finally{$('iniciar-mes').disabled=false;}
};
$('login-form').onsubmit=async e=>{
  e.preventDefault(); $('entrar').disabled=true;
  try {
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!tab?.url || new URL(tab.url).origin!=='https://portal.seduc.pi.gov.br') throw Error('Abra a página de login em https://portal.seduc.pi.gov.br/.');
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['login.js']});
    const payload={usuario:$('usuario').value.trim(),senha:$('senha').value};
    const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:credentials=>globalThis.entrarNoPortal(credentials),args:[payload]});
    $('status').textContent=result.result;
  } catch(e) { $('status').textContent=e.message; }
  finally { $('senha').value=''; $('usuario').value=''; $('entrar').disabled=false; }
};
const names = ['Domingo','Segunda','Terça','Quarta','Quinta','Sexta','Sábado'];
for (const i of [1,2,3,4,5,6,0]) {
  const row = document.createElement('div'); row.className='dia';
  const label=document.createElement('label'), check=document.createElement('input');
  check.type='checkbox'; check.id='dia'+i; label.append(check, names[i]);
  const input=document.createElement('input'); input.id='hora'+i; input.type='text'; input.placeholder='07:00 - 07:50'; input.setAttribute('aria-label','Horários de '+names[i]);
  row.append(label,input); $('semana').append(row);
}
const fields=['turma','disciplina','mes','excecoes','conteudo','metodologia'];
let config;
function read(){const c={semana:{}}; for(const f of fields)c[f]=$(f).value.trim();for(let i=0;i<7;i++)if($('dia'+i).checked)c.semana[i]=$('hora'+i).value.trim();return c;}
function render(c){
  $('aulas').replaceChildren();
  const aulas=Aulas.generate(c); $('status').textContent=`${aulas.length} aula(s) preparada(s). Cada botão tenta preencher e salvar o conteúdo da aula aberta. Se faltar um campo, o envio é interrompido.`;
  for(const aula of aulas){
    const row=document.createElement('div');row.className='aula';
    const text=document.createElement('span');text.textContent=aula.data.split('-').reverse().join('/')+' · '+aula.horario;
    const button=document.createElement('button');button.type='button';button.textContent='Preencher e salvar';
    button.onclick=async()=>{
      button.disabled=true;
      try{
        const target=await academicTarget();
        await chrome.scripting.executeScript({target,files:['portal.js','confirmation.js','wizard.js','fill.js']});
        const [result]=await chrome.scripting.executeScript({target,func:(payload)=>globalThis.preencherAula(payload),args:[{...aula,turma:c.turma,disciplina:c.disciplina,conteudo:c.conteudo,metodologia:c.metodologia}]});
        $('status').textContent=result.result || 'Abra Adicionar aula antes de preencher.';
      }catch(e){$('status').textContent=e.message;}finally{button.disabled=false;}
    };
    row.append(text,button);$('aulas').append(row);
  }
}
const ready=(async()=>{
  const saved=(await chrome.storage.local.get('config')).config;
  config=saved || {conteudo:Aulas.CONTEUDO,metodologia:Aulas.METODOLOGIA,semana:{}};
  if(!config.mes && config.inicio)config.mes=config.inicio.slice(0,7);
  for(const f of fields)$(f).value=config[f]||'';
  for(let i=0;i<7;i++){ $('dia'+i).checked=Boolean(config.semana?.[i]);$('hora'+i).value=config.semana?.[i]||''; }
  if(saved)try{render(saved);}catch(e){$('status').textContent=e.message;}
})().catch(e=>{$('status').textContent='Não foi possível carregar os dados: '+e.message;});
$('form').onsubmit=async e=>{
  e.preventDefault(); await ready;
  try{config=read();render(config);await chrome.storage.local.set({config});}
  catch(e){$('status').textContent=e.message;}
};
