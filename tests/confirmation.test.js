const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../confirmation.js'),'utf8');
function fixture({text='Atenção Tem certeza que deseja realizar essa ação? Não Sim',duplicates=false,disabled=false}={}){
  let clicks=0;
  const yes={textContent:'Sim',disabled,getClientRects:()=>[1],getAttribute:()=>null,click:()=>clicks++};
  const no={...yes,textContent:'Não'};
  const parent={textContent:text,tagName:'DIV',querySelectorAll:()=>duplicates?[yes,yes,no]:[yes,no]};
  yes.parentElement=parent;
  const context=vm.createContext({document:{querySelectorAll:()=>[yes,no]},setTimeout});
  vm.runInContext(source,context);return {context,yes,clicks:()=>clicks};
}
test('confirma uma vez o diálogo esperado',async()=>{
  const f=fixture();assert.equal(f.context.localizarConfirmacaoAula(),f.yes);
  assert.match(await f.context.confirmarEnvioAula(),/ainda não foi comprovada/);assert.equal(f.clicks(),1);
});
test('não aceita outro diálogo, botões ambíguos ou desabilitados',()=>{
  for(const options of [{text:'Excluir registro? Não Sim'},{duplicates:true},{disabled:true}]){
    const f=fixture(options);assert.equal(f.context.localizarConfirmacaoAula(),null);assert.equal(f.clicks(),0);
  }
});
