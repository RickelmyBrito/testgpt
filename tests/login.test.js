const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function fixture(origin='https://portal.seduc.pi.gov.br',duplicate=false) {
  class Input {
    constructor(){this.disabled=false;this._value='';}
    get value(){return this._value;}
    set value(v){this._value=v;}
    getClientRects(){return [1];}
    dispatchEvent(){}
  }
  const user=new Input(),pass=new Input(),button=new Input();
  button.textContent='ENTRAR'; let clicks=0;button.click=()=>clicks++;
  const context=vm.createContext({sessionStorage:{setItem(){}},location:{origin},HTMLInputElement:Input,Event:class{},document:{querySelectorAll(selector){
    if(selector.includes('placeholder'))return duplicate?[user,new Input()]:[user];
    if(selector==='input[type="password"]')return [pass];
    return [button];
  }}});
  vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../login.js'),'utf8'),context);
  return {context,user,pass,clicks:()=>clicks};
}
test('envia login apenas com campos únicos no domínio oficial',async()=>{
  const f=fixture();await f.context.entrarNoPortal({usuario:'teste',senha:'exemplo-local'});
  assert.equal(f.user.value,'teste');assert.equal(f.pass.value,'exemplo-local');assert.equal(f.clicks(),1);
});
test('recusa outro domínio e campos ambíguos sem enviar login',async()=>{
  for(const f of [fixture('https://outro.example'),fixture(undefined,true)]) {
    await assert.rejects(()=>f.context.entrarNoPortal({usuario:'teste',senha:'exemplo-local'}));
    assert.equal(f.clicks(),0);assert.equal(f.pass.value,'');
  }
});
