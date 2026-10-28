import calendar
import datetime as dt
import re

CONTENT = 'Desenvolvimento dos conteúdos previstos no currículo da SEDUC-PI para o componente curricular e a etapa de ensino, conforme o planejamento pedagógico da turma.'
METHOD = 'Aula expositiva dialogada, com apresentação dos conceitos, resolução de exemplos e realização de atividades para consolidação da aprendizagem.'


def lessons(config):
    """Build civil dates; never infer holidays or create attendance data."""
    for name in ('escola', 'turma', 'disciplina', 'conteudo', 'metodologia'):
        if not str(config.get(name, '')).strip():
            raise ValueError('Preencha o campo: ' + name)
    try:
        year, month = map(int, config['mes'].split('-'))
        days = calendar.monthrange(year, month)[1]
        if not 2000 <= year <= 2100:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError('Informe mês e ano válidos.') from None
    excluded = set()
    for text in re.split(r'[,;\n]', config.get('excecoes', '')):
        text = text.strip()
        if not text:
            continue
        try:
            value = dt.date(year, month, int(text)) if re.fullmatch(r'\d{1,2}', text) else dt.datetime.strptime(text, '%d/%m/%Y').date()
            if (value.year, value.month) != (year, month):
                raise ValueError()
        except ValueError:
            raise ValueError('Dia sem aula inválido ou fora do mês: ' + text) from None
        excluded.add(value)
    week = {}
    for weekday, raw in config.get('semana', {}).items():
        if int(weekday) not in range(7):
            raise ValueError('Dia da semana inválido.')
        values = []
        for text in str(raw).split(';'):
            text = text.strip()
            if not text:
                continue
            times = re.findall(r'\b\d{2}:\d{2}\b', text)
            if len(times) != 2:
                raise ValueError('Use horários completos: 08:00 - 09:00.')
            try:
                start, end = (dt.datetime.strptime(t, '%H:%M').time() for t in times)
            except ValueError:
                raise ValueError('Horário inválido: ' + text) from None
            if end <= start:
                raise ValueError('O horário final deve ser posterior ao inicial.')
            value = ' - '.join(times)
            if value not in values:
                values.append(value)
        week[int(weekday)] = values
    result = []
    for day in range(1, days + 1):
        date = dt.date(year, month, day)
        if date in excluded:
            continue
        # JS and portal configuration use Sunday=0.
        for time in week.get((date.weekday() + 1) % 7, []):
            result.append({'data': date.isoformat(), 'horario': time})
    if not result:
        raise ValueError('Nenhuma aula no mês. Informe os dias e horários.')
    return result
