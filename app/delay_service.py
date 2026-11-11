"""Read validated, published FRA delay aggregates; no raw XLSX loads per request."""
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
from .service_categories import category_for_operational, CATEGORY_LABELS

DATA = Path(__file__).resolve().parent / 'data/fra_delays.json'
CODE_DICTIONARY = Path(__file__).resolve().parent / 'data/delay_code_definitions.json'


def delay_codes():
    """Read provenance-linked code labels independently from published observations."""
    return json.loads(CODE_DICTIONARY.read_text(encoding='utf-8'))



@lru_cache(maxsize=1)
def _load():
    if not DATA.exists():
        return {'available': False, 'periods': [], 'services': [], 'by_key': {}, 'source': None}
    data = json.loads(DATA.read_text(encoding='utf-8'))
    if data.get('version') != 1:
        raise ValueError('Unsupported FRA delay publication version')
    groups = defaultdict(list)
    for row in data['records']:
        groups[(row['service'], row['sub_service'])].append(row)
    catalog = []
    lookup = {}
    for i, (key, rows) in enumerate(sorted(groups.items()), 1):
        identifier = str(i)  # numeric ID avoids ambiguous names and slug collisions
        total = sum(r['minutes'] for r in rows)
        service, subservice = key
        catalog.append({'id': identifier, 'service': service, 'sub_service': subservice,
                        'label': service if service.casefold() == subservice.casefold() else f'{service} / {subservice}',
                        'category': category_for_operational(service, subservice),
                        'total_minutes': round(total, 1), 'period_count': len({(r['year'],r['quarter']) for r in rows})})
        lookup[identifier] = rows
    return {'available': True, 'periods': data['periods'], 'services': catalog,
            'by_key': lookup, 'source': data['source'], 'rows_processed': data['rows_processed'],
            'source_workbook_count': len(data['source_workbooks'])}


def overview():
    data = _load()
    return {k: data[k] for k in ('available', 'periods', 'services', 'source')}


def detail(identifier):
    data = _load()
    group = identifier.removeprefix('group:') if identifier.startswith('group:') else None
    if group is not None and group not in CATEGORY_LABELS:
        return None
    if group is not None:
        ids = {s['id'] for s in data['services'] if s['category'] == group}
        rows = [r for key in ids for r in data['by_key'][key]]
        if not rows: return None
    else:
        rows = data['by_key'].get(identifier)
        if rows is None: return None
    # Explicit 'all' period is aggregate of the same service/subservice only.
    by_period = defaultdict(float)
    by_responsibility = defaultdict(float)
    by_code = defaultdict(float)
    by_host = defaultdict(float)
    by_resp_period = defaultdict(float)
    for r in rows:
        p = f"FY{r['year']} Q{r['quarter']}"
        m = r['minutes']
        by_period[p] += m
        by_responsibility[r['responsibility']] += m
        by_resp_period[(p, r['responsibility'])] += m
    # Quarter-level cause/host breakdowns let UI change date window without re-requesting raw rows.
    by_period_code = defaultdict(float)
    by_period_host = defaultdict(float)
    for r in rows:
        p = f"FY{r['year']} Q{r['quarter']}"
        by_period_code[(p, r['code'], r['responsibility'])] += r['minutes']
        by_period_host[(p, r['host'], r['responsibility'])] += r['minutes']
    summary = ({'id':identifier,'label':CATEGORY_LABELS[group]+' — all reporting units','category':group, 'total_minutes':sum(r['minutes'] for r in rows),'is_group':True} if group is not None else next(item for item in data['services'] if item['id'] == identifier))
    return {'service': summary, 'periods': data['periods'],
            'trends': [{'period': p, 'minutes': round(by_period[p], 2)} if p in by_period else {'period':p,'minutes':None} for p in data['periods']],
            'responsibilities': [{'period': p, 'responsibility': resp, 'minutes':round(value,2)} for (p,resp),value in sorted(by_resp_period.items())],
            'causes': [{'period':p,'code':code,'responsibility':resp,'minutes':round(m,2)} for (p,code,resp),m in sorted(by_period_code.items())],
            'hosts': [{'period':p,'host':host,'responsibility':resp,'minutes':round(m,2)} for (p,host,resp),m in sorted(by_period_host.items())],
            'delay_code_dictionary': delay_codes(),
            'method': 'Summed FRA delay minutes across selected reporting units by cause and host. This is NOT a normalized rate, and may overlap if operational reporting units represent the same trains. No host-train-mile denominators are summed.'}
