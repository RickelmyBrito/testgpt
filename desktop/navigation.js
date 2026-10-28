/* Find a unique action in the card identified by exact school/class/subject text. */
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
    if(visible(select) && [...select.options].filter(option=>!option.disabled && desktopProfileLabel(option.textContent)).length===1)result.add(select);
  }
  for(const label of document.querySelectorAll('a,button,span,div,p,li,label')) {
    if(!visible(label) || !desktopProfileLabel(label.textContent))continue;
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
globalThis.desktopAction = function ({title, action, discipline}) {
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const visible=el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true';
  const nodes=[...document.querySelectorAll('h1,h2,h3,h4,h5,p,span,div,a,button')].filter(visible);
  const result=new Set();
  for(const heading of nodes.filter(el=>norm(el.textContent)===norm(title))) {
    let parent=heading;
    for(let depth=0;parent && depth<10;depth++,parent=parent.parentElement) {
      if(['BODY','HTML'].includes(parent.tagName))break;
      if(discipline && ![...parent.querySelectorAll('p,span,div,h1,h2,h3,h4,h5')].some(el=>norm(el.textContent)===norm(discipline)))continue;
      const actions=[...parent.querySelectorAll('a,button,[role="button"]')].filter(visible).filter(el=>norm(el.textContent)===norm(action));
      if(actions.length===1){result.add(actions[0]);break;}
      if(actions.length>1)break;
    }
  }
  return result.size===1?[...result][0]:null;
};
