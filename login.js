globalThis.entrarNoPortal = async function ({usuario, senha}) {
  if (location.origin !== 'https://portal.seduc.pi.gov.br') throw Error('Abra o portal oficial em HTTPS.');
  const visible = el => Boolean(el.getClientRects().length) && !el.disabled;
  function unique(selector, name) {
    const found=[...document.querySelectorAll(selector)].filter(visible);
    if(found.length!==1) throw Error(`Não foi possível identificar ${name}. Nenhum login enviado.`);
    return found[0];
  }
  const user=unique('input[placeholder="Usuário"], input[placeholder="Usuario"]','o campo Usuário');
  const pass=unique('input[type="password"]','o campo Senha');
  const buttons=[...document.querySelectorAll('button,input[type="submit"]')].filter(visible).filter(el=>(el.textContent || el.value || '').trim().toLocaleLowerCase('pt-BR')==='entrar');
  if(buttons.length!==1) throw Error('Botão Entrar não identificado. Nenhum login enviado.');
  if(!usuario || !senha) throw Error('Informe usuário e senha.');
  for(const [el,value] of [[user,usuario],[pass,senha]]) {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,value);
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
  }
  if(user.value!==usuario || pass.value!==senha) throw Error('O portal não aceitou o preenchimento.');
  sessionStorage.setItem('assistente-aulas-perfil',String(Date.now()+120000));
  buttons[0].click();
  return 'Login enviado. Confira se o portal abriu a área interna. Se houver CAPTCHA ou código de verificação, conclua no navegador.';
};
