"""Extract dated curriculum tables locally, without sending the PDF anywhere."""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta


def normal(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c)).upper().split())

MONTHS = {normal(x): i for i, x in enumerate(('janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'), 1)}

@dataclass(frozen=True)
class Encounter:
    day: date
    content: str
    subcontent: str


def interval(label, year):
    label = normal(label)
    cross = re.fullmatch(r'(\d{1,2}) DE ([A-Z]+) A (\d{1,2}) DE ([A-Z]+)', label)
    same = re.fullmatch(r'([A-Z]+) (\d{1,2}) A (\d{1,2})', label)
    if cross:
        a, m, b, n = cross.groups()
        start, end = date(year, MONTHS[m], int(a)), date(year, MONTHS[n], int(b))
    elif same:
        m, a, b = same.groups()
        start, end = date(year, MONTHS[m], int(a)), date(year, MONTHS[m], int(b))
    else:
        raise ValueError(f'Intervalo de datas não reconhecido: {label}')
    if not 0 <= (end-start).days <= 7:
        raise ValueError('O PDF contém um intervalo semanal inválido.')
    return start, end


def bullets(text):
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if normal(line).startswith('OBS:'):
            break
        if re.match(r'^[•→‾]', line):
            result.append(re.sub(r'^[•→‾]\s*', '', line))
        elif result:
            result[-1] += ' ' + line
        else:
            result.append(line)
    return result


def distribute(start, end, text, excluded=()):
    dates = [start+timedelta(days=i) for i in range((end-start).days+1)
             if (start+timedelta(days=i)).weekday() in (2, 3) and start+timedelta(days=i) not in excluded]
    if not dates:
        return []
    items = bullets(text)
    # Unit names provide context, chapter names describe topics; retain both in details.
    if not items:
        raise ValueError('Semana sem conteúdo legível no PDF.')
    fixed = {}
    remaining = []
    for item in items:
        event = re.search(r'\((\d{2})/(\d{2})\)', item)
        event_day = date(start.year, int(event[2]), int(event[1])) if event else None
        if event_day in dates and 'APLICA' in normal(item):
            fixed[event_day] = [item]
        else:
            remaining.append(item)
    free = [d for d in dates if d not in fixed]
    result = []
    for d in dates:
        if d in fixed:
            chunk = fixed[d]
        else:
            i = free.index(d)
            # Contiguous, balanced slices preserve the source order and all source topics.
            boundaries = [j for j, value in enumerate(remaining) if re.match(r'^\(UNIDADE', value, re.I)]
            if len(boundaries) == len(free) and boundaries[0] == 0:
                chunk = remaining[boundaries[i]:boundaries[i+1] if i+1 < len(boundaries) else len(remaining)]
            else:
                chunk = remaining[len(remaining)*i//len(free):len(remaining)*(i+1)//len(free)]
            if not chunk:
                chunk = remaining or items
        titles = [s for s in chunk if '(CAPÍTULO' in s.upper()]
        title = titles[0] if titles else chunk[0]
        title = re.sub(r'^\((?:Capítulo|UNIDADE)\s*\d+\)\s*', '', title, flags=re.I)
        result.append(Encounter(d, title, d.strftime('%d/%m/%Y') + ' — ' + '; '.join(chunk)))
    return result


def import_pdf(path, year, grade, period, excluded=()):
    import pdfplumber
    rows, headers = [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            headers.append(text)
            for table in page.extract_tables():
                for row in table:
                    if len(row) >= 3 and row[0] and re.search(r'\d+\s+A\s+\d+|\d+ DE', normal(row[0])):
                        rows.append((row[0], row[2] or ''))
    if not rows:
        raise ValueError('Não encontrei a tabela de semanas. Use um PDF com texto e tabela no formato do alinhamento enviado; PDF escaneado precisa de OCR.')
    header = normal('\n'.join(headers)[:1800])
    found_year = re.search(r'BIMESTRE\s*[-–]?\s*(20\d{2})', header)
    if found_year and int(found_year[1]) != year:
        raise ValueError('O ano selecionado difere do ano do alinhamento.')
    found_grade = re.search(r'(\d+)\s*[º°]?\s*ANO', header)
    if found_grade and int(found_grade[1]) != grade:
        raise ValueError('A turma selecionada difere do ano escolar do PDF.')
    found_period = re.search(r'\b(I{1,3}|IV|[1-4])\s*[º°]?\s*BIMESTRE', header)
    if found_period:
        value = {'I':1,'II':2,'III':3,'IV':4}.get(found_period[1], int(found_period[1]) if found_period[1].isdigit() else 0)
        if value != period:
            raise ValueError('O bimestre selecionado difere do alinhamento.')
    encounters, seen = [], set()
    for label, text in rows:
        a, b = interval(label, year)
        for entry in distribute(a, b, text, excluded):
            if entry.day in seen:
                raise ValueError('Há semanas sobrepostas no PDF; confira o arquivo.')
            seen.add(entry.day)
            encounters.append(entry)
    return sorted(encounters, key=lambda x:x.day)
