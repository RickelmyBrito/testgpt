const {test}=require('node:test');
const assert=require('node:assert/strict');
require('../schedule.js');
test('gera apenas os dias escolhidos, inclui limites e múltiplos horários',()=>{
  const result=Aulas.generate({inicio:'2026-10-26',fim:'2026-11-02',semana:{1:'07:00 - 07:50; 07:50 - 08:40',3:'09:00 - 09:50'}});
  assert.deepEqual(result.map(a=>a.data),['2026-10-26','2026-10-26','2026-10-28','2026-11-02','2026-11-02']);
});
test('exclui dias sem aula',()=>{
  assert.deepEqual(Aulas.generate({inicio:'2026-10-26',fim:'2026-11-02',semana:{1:'07:00'},excecoes:'02/11/2026'}),[{data:'2026-10-26',horario:'07:00'}]);
});
test('mês completo considera ano bissexto e exclusões por número',()=>{
  const aulas=Aulas.generate({mes:'2028-02',semana:{2:'07:00;07:00'},excecoes:'8, 15;22'});
  assert.deepEqual(aulas,[{data:'2028-02-01',horario:'07:00'},{data:'2028-02-29',horario:'07:00'}]);
});
test('rejeita dia inexistente e exclusão fora do mês',()=>{
  for(const excecoes of ['30','01/03/2028'])assert.throws(()=>Aulas.generate({mes:'2028-02',semana:{2:'07:00'},excecoes}));
  assert.throws(()=>Aulas.generate({mes:'2026-13',semana:{2:'07:00'}}));
});
test('rejeita datas inexistentes, intervalos invertidos e agenda vazia',()=>{
  for(const c of [
    {inicio:'2026-02-30',fim:'2026-03-02',semana:{1:'07:00'}},
    {inicio:'2026-11-02',fim:'2026-10-26',semana:{}},
    {inicio:'2026-10-26',fim:'2026-10-26',semana:{}},
    {inicio:'2026-10-26',fim:'2026-11-02',semana:{1:'07:00'},excecoes:'31/02/2026'}
  ])assert.throws(()=>Aulas.generate(c));
});
