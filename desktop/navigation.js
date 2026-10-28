/* Find a unique action in the card identified by exact school/class/subject text. */
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
