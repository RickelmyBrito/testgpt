(() => {
  const key='assistente-aulas-perfil';
  const normalize=s=>String(s||'').replace(/\s+/g,' ').trim().toLocaleLowerCase('pt-BR');
  function attempt() {
    const raw=sessionStorage.getItem(key);
    if(!raw)return;
    const expiry=Number(raw);
    if(!Number.isFinite(expiry) || expiry<=Date.now()){sessionStorage.removeItem(key);return;}
    const text=normalize(document.body?.textContent);
    if(!text.includes('escolha seu perfil de acesso'))return;
    const candidates=[...document.querySelectorAll('a,button,[role="button"],input[type="button"],input[type="submit"]')]
      .filter(el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true')
      .filter(el=>normalize(el.textContent || el.value)==='professor(a)');
    if(candidates.length!==1)return;
    sessionStorage.removeItem(key);
    candidates[0].click();
  }
  attempt();
  // Also supports login/profile transitions without a full page reload.
  const observer=new MutationObserver(attempt);
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(()=>observer.disconnect(),120000);
})();
