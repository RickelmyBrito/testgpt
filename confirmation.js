globalThis.localizarConfirmacaoAula = function () {
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const visible=el=>el.getClientRects().length && !el.disabled && el.getAttribute('aria-disabled')!=='true';
  const candidates=new Set();
  for(const button of document.querySelectorAll('button,[role="button"],input[type="submit"],input[type="button"]')) {
    if(!visible(button) || norm(button.textContent || button.value)!=='sim')continue;
    let parent=button.parentElement;
    for(let depth=0;parent && depth<8;depth++,parent=parent.parentElement) {
      if(['BODY','HTML'].includes(parent.tagName))break;
      const text=norm(parent.textContent);
      if(!text.includes('atencao') || !text.includes('tem certeza que deseja realizar essa acao?'))continue;
      const buttons=[...parent.querySelectorAll('button,[role="button"],input[type="submit"],input[type="button"]')].filter(visible);
      const yes=buttons.filter(el=>norm(el.textContent || el.value)==='sim');
      const no=buttons.filter(el=>norm(el.textContent || el.value)==='nao');
      if(yes.length===1 && no.length===1)candidates.add(yes[0]);
      break;
    }
  }
  return candidates.size===1 ? [...candidates][0] : null;
};
globalThis.confirmarEnvioAula = async function (check=()=>{}) {
  // Called only immediately after this extension clicks Salvar e Avançar.
  const deadline=Date.now()+10000;
  while(Date.now()<deadline) {
    check();
    const button=globalThis.localizarConfirmacaoAula();
    if(button){button.click();return 'Confirmação “Sim” enviada. O programa tentará avançar pelas etapas e finalizar, sem editar os campos. A gravação ainda não foi comprovada; aguarde o portal.';}
    await new Promise(resolve=>setTimeout(resolve,200));
  }
  return 'Salvar e Avançar acionado, mas a confirmação não foi observada nesta tela. Confira o andamento no portal antes de repetir.';
};
