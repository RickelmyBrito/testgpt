/* Find a unique action in the card identified by exact school/class/subject text. */
globalThis.desktopText = function (element) {
  const copy=element.cloneNode(true);
  copy.querySelectorAll('svg,i,[hidden],[aria-hidden="true"],.material-icons,.material-icons-outlined,.material-symbols-outlined').forEach(icon=>icon.remove());
  return copy.textContent.replace(/\s+/g,' ').trim();
};
globalThis.desktopProfileLabel = function (text) {
  return /^professor(?:a|\s*\(\s*a\s*\)|\/a)?$/i.test(String(text||'').replace(/\s+/g,' ').trim());
};
globalThis.desktopProfileScreen = function () {
  return String(document.body?.innerText||'').replace(/\s+/g,' ').trim().toLocaleLowerCase('pt-BR').includes('escolha seu perfil de acesso');
};
globalThis.desktopProfileCandidates = function () {
  if(!desktopProfileScreen())return [];
  const visible=el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true';
  const result=new Set();
  for(const select of document.querySelectorAll('select')) {
    if(visible(select) && [...select.options].filter(option=>!option.disabled && desktopProfileLabel(desktopText(option))).length===1)result.add(select);
  }
  for(const label of document.querySelectorAll('a,button,span,div,p,li,label')) {
    if(!visible(label) || !desktopProfileLabel(desktopText(label)))continue;
    const ancestor=label.closest('a,button,[role="button"],[ng-click],[data-ng-click],[onclick]');
    if(ancestor && visible(ancestor)){result.add(ancestor);continue;}
    let parent=label.parentElement;
    for(let depth=0;parent && depth<3;depth++,parent=parent.parentElement) {
      if(['BODY','HTML'].includes(parent.tagName))break;
      const actions=[...parent.querySelectorAll('a,button,[role="button"],[ng-click],[data-ng-click],[onclick]')].filter(visible);
      if(actions.length===1){result.add(actions[0]);break;}
      if(actions.length>1)break;
    }
  }
  // Nested wrappers can describe the same action; prefer its outer click target.
  return [...result].filter(el=>![...result].some(other=>other!==el && other.contains(el)));
};
globalThis.desktopProfileAction = function () {
  const candidates=desktopProfileCandidates();
  return candidates.length===1?candidates[0]:null;
};
globalThis.desktopActionCandidates = function ({title, action, discipline}) {
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const visible=el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true';
  const nodes=[...document.querySelectorAll('h1,h2,h3,h4,h5,p,span,div,a,button')].filter(visible);
  const result=new Set();
  for(const heading of nodes.filter(el=>norm(desktopText(el))===norm(title))) {
    let parent=heading;
    for(let depth=0;parent && depth<10;depth++,parent=parent.parentElement) {
      if(['BODY','HTML'].includes(parent.tagName))break;
      if(discipline && ![...parent.querySelectorAll('p,span,div,h1,h2,h3,h4,h5')].some(el=>norm(desktopText(el))===norm(discipline)))continue;
      const labels=[...parent.querySelectorAll('a,button,[role="button"],[role="link"],span,div,p,li')].filter(visible).filter(el=>norm(desktopText(el))===norm(action));
      const leaves=labels.filter(el=>!labels.some(other=>other!==el && el.contains(other)));
      const actions=[...new Set(leaves.map(el=>{
        const target=el.closest('a,button,[role="button"],[role="link"],[ng-click],[data-ng-click],[onclick]');
        return target && parent.contains(target)?target:el;
      }))];
      if(actions.length===1){result.add(actions[0]);break;}
      if(actions.length>1)break;
    }
  }
  return [...result];
};
globalThis.desktopAction = function (config) {
  const result=desktopActionCandidates(config);
  return result.length===1?result[0]:null;
};
globalThis.desktopScrollClasses = function () {
  const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
  if(!norm(document.body?.innerText).includes('lista de turmas'))return {screen:false};
  const root=document.scrollingElement;
  const candidates=[...new Set([root,...document.querySelectorAll('main,section,div,ul')])].filter(el=>{
    if(!el || !el.getClientRects().length || el.clientHeight<=0 || el.scrollHeight<=el.clientHeight+2)return false;
    if(el!==root && !/auto|scroll|overlay/.test(getComputedStyle(el).overflowY))return false;
    return el===root || norm(el.innerText).includes('registro de aulas') || norm(el.innerText).includes('lista de turmas');
  }).sort((a,b)=>a.contains(b)?1:b.contains(a)?-1:0);
  for(const el of candidates) {
    if(el.scrollTop+el.clientHeight>=el.scrollHeight-2)continue;
    const before=el.scrollTop;
    el.scrollBy({top:Math.max(180,Math.floor(el.clientHeight*0.75)),behavior:'instant'});
    if(el.scrollTop>before)return {screen:true,moved:true,extent:el.scrollHeight};
  }
  return {screen:true,moved:false,extent:candidates.map(el=>el.scrollHeight).join(',')};
};
