/* Adapter for the academic iframe's React/Radix controls. No private API calls. */
globalThis.PortalAulas = (() => {
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\(\s*\*\s*\)/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const visible=el=>Boolean(el?.isConnected && el.getClientRects().length);
  const time=s=>{
    const values=String(s).match(/\b\d{1,2}:\d{2}\b/g)||[];
    if(values.length!==2 || values.some(v=>{const [h,m]=v.split(':').map(Number);return h>23 || m>59;}))return '';
    return values.map(v=>v.padStart(5,'0')).join('-');
  };
  function field(name) {
    const found=new Set();
    for(const label of document.querySelectorAll('label')) {
      if(norm(label.textContent)!==norm(name) || !visible(label))continue;
      if(label.control && visible(label.control)){found.add(label.control);continue;}
      let parent=label.parentElement;
      for(let depth=0;parent && depth<3;depth++,parent=parent.parentElement) {
        if(parent.querySelectorAll('label').length!==1)break;
        const controls=[...parent.querySelectorAll('input:not([type="hidden"]),textarea,select,button')].filter(visible);
        if(controls.length===1){found.add(controls[0]);break;}
      }
    }
    if(found.size!==1)throw Error('Campo não identificado de forma única: '+name);
    return [...found][0];
  }
  const value=el=>el.tagName==='SELECT'?el.selectedOptions[0]?.textContent : el.tagName==='BUTTON'?el.textContent:el.value;
  function assertIdentity(aula) {
    if(norm(value(field('Turma')))!==norm(aula.turma))throw Error('A turma aberta não corresponde à informada.');
    if(norm(value(field('Componente')))!==norm(aula.disciplina))throw Error('A disciplina aberta não corresponde à informada.');
  }
  async function wait(get,check=()=>{},timeout=6000) {
    const end=Date.now()+timeout;
    do{check();const result=get();if(result)return result;await new Promise(r=>setTimeout(r,60));}while(Date.now()<end);
    throw Error('O portal não disponibilizou o controle esperado.');
  }
  function press(el) {
    if(!visible(el) || el.disabled || el.getAttribute('aria-disabled')==='true')throw Error('Controle indisponível.');
    el.focus();
    el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,button:0,pointerType:'mouse',isPrimary:true}));
    el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,button:0,pointerType:'mouse',isPrimary:true}));
    el.click();
  }
  function setText(el,text) {
    const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto,'value').set.call(el,text);
    el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
  }
  async function choose(name,text,check) {
    const el=await wait(()=>{const candidate=field(name);return !candidate.disabled && candidate.getAttribute('aria-disabled')!=='true'?candidate:null;},check);
    const matches=(a,b)=>name.startsWith('Horário')?time(a)===time(b)&&time(b).length===11:norm(a)===norm(b);
    if(matches(value(el),text))return;
    if(el.tagName==='SELECT') {
      const options=[...el.options].filter(o=>!o.disabled && matches(o.textContent,text));
      if(options.length!==1)throw Error('Opção não encontrada: '+name+' — '+text);
      setText(el,options[0].value);
    } else {
      if(el.getAttribute('role')!=='combobox')throw Error('Lista não suportada: '+name);
      press(el);
      const option=await wait(()=>{
        const id=el.getAttribute('aria-controls');
        const list=id?document.getElementById(id):null;
        if(!list || !visible(list))return null;
        const options=[...list.querySelectorAll('[role="option"]')].filter(visible)
          .filter(o=>o.getAttribute('aria-disabled')!=='true' && !o.hasAttribute('data-disabled') && matches(o.textContent,text));
        if(options.length>1)throw Error('Opção ambígua: '+name);
        return options[0];
      },check);
      press(option);
    }
    await wait(()=>matches(value(field(name)),text),check);
  }
  const months=['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
  const english=['january','february','march','april','may','june','july','august','september','october','november','december'];
  function monthIndex(text) {
    const words=norm(text).split(/\s+/), year=words.find(x=>/^\d{4}$/.test(x));
    let month=months.indexOf(words[0]);if(month<0)month=english.indexOf(words[0]);
    if(!year || month<0)throw Error('Cabeçalho do calendário não reconhecido.');
    return Number(year)*12+month;
  }
  function caption(root) {
    const candidates=[...root.querySelectorAll('.rdp-caption_label,.rdp-caption-label,.rdp-month_caption,[aria-live="polite"]')].filter(visible).filter(el=>{
      try{monthIndex(el.textContent);return true;}catch{return false;}
    });
    if(candidates.length!==1)throw Error('Mês do calendário não identificado.');
    return candidates[0];
  }
  async function chooseDate(iso,check) {
    const target=iso.split('-').reverse().join('/');
    if(value(field('Data')).trim()===target)return;
    const el=field('Data');
    if(el.tagName==='INPUT' && el.type==='date') {setText(el,iso);return;}
    if(el.tagName!=='BUTTON')throw Error('Calendário não suportado.');
    press(el);
    const calendar=()=>{
      const root=document.getElementById(el.getAttribute('aria-controls'));
      if(!root || !visible(root))return null;
      return root.querySelector('.rdp, .rdp-root') || root;
    };
    await wait(calendar,check);
    const desired=Number(iso.slice(0,4))*12+Number(iso.slice(5,7))-1;
    for(let attempts=0;attempts<120;attempts++) {
      check();const root=calendar();if(!root)throw Error('O calendário foi fechado antes da seleção.');
      const current=monthIndex(caption(root).textContent);
      if(current===desired) {
        const day=String(Number(iso.slice(8,10)));
        const buttons=[...root.querySelectorAll('button')].filter(visible).filter(b=>!b.disabled && b.getAttribute('aria-disabled')!=='true')
          .filter(b=>!b.matches('.rdp-day_outside,.rdp-outside,.day-outside,[data-outside="true"]') && !b.closest('.rdp-day_outside,.rdp-outside,.day-outside,[data-outside="true"]'))
          .filter(b=>b.textContent.trim()===day);
        if(buttons.length!==1)throw Error('Dia indisponível ou ambíguo: '+target);
        press(buttons[0]);await wait(()=>value(field('Data')).trim()===target,check);return;
      }
      const back=current>desired;
      const nav=[...root.querySelectorAll('button')].filter(visible).filter(b=>!b.disabled)
        .filter(b=>back? /previous|anterior|prev/i.test((b.name||'')+' '+(b.getAttribute('aria-label')||'')):/next|proximo|próximo/i.test((b.name||'')+' '+(b.getAttribute('aria-label')||'')));
      if(nav.length!==1)throw Error('Navegação do calendário não identificada.');
      press(nav[0]);await wait(()=>{
        const currentCalendar=calendar();
        const cap=currentCalendar && caption(currentCalendar);
        return cap && monthIndex(cap.textContent)!==current;
      },check);
    }
    throw Error('Data fora do limite de navegação do calendário.');
  }
  return {norm,visible,time,field,value,assertIdentity,wait,press,setText,choose,chooseDate,monthIndex};
})();
