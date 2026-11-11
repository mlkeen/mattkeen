"""Publish quarterly FRA financial measures with explicit quality flags.

Inputs: data/processed/{cost_recovery,avoidable_expense,fully_allocated_expense}.csv
Output: app/data/fra_financials.json. No original workbook data is rewritten.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / 'app/data/fra_financials.json'
SOURCES = {
    'cost_recovery': ('cost_recovery.csv', 'cost_recovery', 'operating_revenue', 'allocated_expense'),
    'avoidable_expense': ('avoidable_expense.csv', 'avoidable_expense_coverage', 'passenger_revenue', 'avoidable_expense'),
    'fully_allocated_expense': ('fully_allocated_expense.csv', 'allocated_expense_coverage', 'passenger_revenue', 'allocated_expense'),
}

def num(text):
    if text is None or str(text).strip() == '': return None
    try: value=float(text)
    except (ValueError, TypeError): return None
    return value if math.isfinite(value) else None

def classification(numerator, denominator, reported):
    if numerator is None or denominator is None: return 'missing_components'
    if denominator == 0: return 'zero_expense'
    if denominator < 0: return 'negative_expense'
    if numerator < 0: return 'negative_revenue'
    if reported is None: return 'missing_ratio'
    calculated = numerator / denominator
    if abs(calculated - reported) > max(.02, abs(calculated)*.02): return 'ratio_mismatch'
    return 'valid'

def compile_financials(directory):
    records=[]; quarters=set(); seen=set(); counts={}; workbooks=set()
    for measure,(filename,ratio_col,num_col,den_col) in SOURCES.items():
        path=Path(directory)/filename
        if not path.is_file(): raise FileNotFoundError(f'Missing {path}. Run scripts/fra_etl.py first.')
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader=csv.DictReader(f)
            required={'fiscal_year','fiscal_quarter','apt_code','route','reporting_level',ratio_col,num_col,den_col,'source_workbook','source_sheet','source_excel_row'}
            if measure!='cost_recovery': required.add('state_payments_included')
            missing=required-set(reader.fieldnames or [])
            if missing: raise ValueError(f'{filename}: missing columns {sorted(missing)}')
            for lineno,r in enumerate(reader,2):
                try:
                    y=int(r['fiscal_year']);q=int(r['fiscal_quarter'])
                    if not 2000<=y<=2100 or q not in range(1,5): raise ValueError('Invalid fiscal quarter')
                except (ValueError,TypeError) as e: raise ValueError(f'{filename}:{lineno}: invalid period') from e
                level=r['reporting_level'].strip().lower()
                if level not in ('route','aggregate'):raise ValueError(f'{filename}:{lineno}: invalid reporting level')
                payments = None if measure=='cost_recovery' else r['state_payments_included'].strip().lower()
                if payments not in (None,'true','false','1','0','yes','no'): raise ValueError(f'{filename}:{lineno}: unknown state-payments flag {payments}')
                if payments is not None:payments=payments in ('true','1','yes')
                code=r['apt_code'].strip();name=r['route'].strip()
                if not code or not name:raise ValueError(f'{filename}:{lineno}: empty reporting identity')
                key=(measure,y,q,code,payments)
                if key in seen:raise ValueError(f'{filename}:{lineno}: duplicate measure/period/code/payment: {key}')
                seen.add(key)
                numerator=num(r[num_col]);denominator=num(r[den_col]);reported=num(r[ratio_col]);status=classification(numerator,denominator,reported)
                counts[status]=counts.get(status,0)+1
                workbooks.add(r['source_workbook'].strip());quarters.add((y,q))
                records.append({'measure':measure,'year':y,'quarter':q,'period':f'FY{y} Q{q}',
                    'apt_code':code,'route':name,'level':level,'state_payments_included':payments,
                    'numerator':numerator,'denominator':denominator,'ratio_source':reported,
                    'ratio':reported if status=='valid' else None,'status':status,
                    'source_workbook':r['source_workbook'].strip(), 'source_sheet':r['source_sheet'].strip(),
                    'source_excel_row':r['source_excel_row'].strip()})
    return {'version':1,'source':'FRA quarterly Financial Metrics','periods':[f'FY{y} Q{q}' for y,q in sorted(quarters)],
        'source_workbooks':sorted(workbooks),'status_counts':counts,'records':records,
        'method':'Ratios are stored as fractions (1.0 = 100%). Flagged records retain original values but are excluded from charts. Route histories are identified by both APT code and reported route name.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,default=ROOT/'data/processed')
    p.add_argument('--destination',type=Path,default=DEFAULT_DEST)
    args=p.parse_args()
    d=compile_financials(args.source_dir)
    args.destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.destination.with_suffix(args.destination.suffix+'.tmp')
    try:
        tmp.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
        os.replace(tmp,args.destination)
    finally: tmp.unlink(missing_ok=True)
    print(f"Published {len(d['records']):,} financial observations across {len(d['periods'])} quarters")
    print('Quality status:',d['status_counts'])
    print('Destination:',args.destination)
    print('Restart Flask to reload publication.')

if __name__=='__main__':main()
