/* Datas civis em UTC evitam mudanças de dia por fuso e horário de verão. */
globalThis.Aulas = (() => {
  const CONTEUDO = 'Desenvolvimento dos conteúdos previstos no currículo da SEDUC-PI para o componente curricular e a etapa de ensino, conforme o planejamento pedagógico da turma.';
  const METODOLOGIA = 'Aula expositiva dialogada, com apresentação dos conceitos, resolução de exemplos e realização de atividades para consolidação da aprendizagem.';
  function date(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw Error('Informe datas válidas.');
    const d = new Date(value + 'T00:00:00Z');
    if (Number.isNaN(+d) || d.toISOString().slice(0,10) !== value) throw Error('Data inválida: ' + value);
    return d;
  }
  function generate(config) {
    let inicio=config.inicio, fim=config.fim;
    if(config.mes) {
      if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(config.mes)) throw Error('Selecione mês e ano válidos.');
      inicio=config.mes+'-01';
      const last=date(inicio);last.setUTCMonth(last.getUTCMonth()+1);last.setUTCDate(0);
      fim=last.toISOString().slice(0,10);
    }
    const start = date(inicio), end = date(fim);
    if (end < start) throw Error('A data final deve ser igual ou posterior à inicial.');
    if ((end-start)/86400000 > 366) throw Error('Escolha um período de até 367 dias.');
    const excluded = new Set();
    for (const line of (config.excecoes || '').split(/[\n,;]/).map(x=>x.trim()).filter(Boolean)) {
      if(config.mes && /^\d{1,2}$/.test(line)) {
        const iso=config.mes+'-'+line.padStart(2,'0');date(iso);excluded.add(iso);continue;
      }
      const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(line);
      if (!match) throw Error('Informe números dos dias no mês ou datas DD/MM/AAAA.');
      const iso = `${match[3]}-${match[2]}-${match[1]}`;
      if(config.mes && !iso.startsWith(config.mes+'-'))throw Error('O dia sem aula deve pertencer ao mês selecionado: '+line);
      date(iso); excluded.add(iso);
    }
    const result = [];
    for (const d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate()+1)) {
      const iso = d.toISOString().slice(0,10);
      if (excluded.has(iso)) continue;
      for (const horario of new Set((config.semana[d.getUTCDay()] || '').split(';').map(x=>x.trim()).filter(Boolean))) result.push({data:iso,horario});
    }
    if (!result.length) throw Error('Nenhuma aula no período. Marque os dias e informe os horários.');
    return result;
  }
  return {generate, CONTEUDO, METODOLOGIA};
})();
