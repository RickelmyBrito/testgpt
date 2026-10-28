const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const code=fs.readFileSync(require('node:path').join(__dirname,'../profile.js'),'utf8');
function run({armed=true,count=1,heading=true,expired=false}={}) {
  let clicks=0,stored=armed?String(Date.now()+(expired?-1000:60000)):null;
  const button={textContent:' Professor(a) ',getClientRects:()=>[1],getAttribute:()=>null,click:()=>clicks++};
  vm.runInNewContext(code,{
    sessionStorage:{getItem:()=>stored,removeItem:()=>{stored=null;}},
    document:{body:{textContent:heading?'Escolha seu perfil de acesso':'Menu'},documentElement:{},querySelectorAll:()=>Array(count).fill(button)},
    MutationObserver:class{observe(){}disconnect(){}},setTimeout(){}
  });
  return {clicks,stored};
}
test('seleciona perfil único após login solicitado e consome a autorização',()=>{
  assert.deepEqual(run(),{clicks:1,stored:null});
});
test('não seleciona sem login solicitado, com expiração, ambiguidade ou fora da tela',()=>{
  for(const options of [{armed:false},{expired:true},{count:2},{heading:false}])assert.equal(run(options).clicks,0);
});
