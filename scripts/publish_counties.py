"""Publish county inputs using ONLY locally downloaded U.S. Census files.

Required downloads (save both in data/raw/census/):
  census_data_all_county.csv: county GEO_ID, pop_total_est, income_median_household_income_est
  (alternatively acs_counties.json: legacy 2024 ACS Census API array)
  2025_Gaz_counties_national.zip: 2025 Census national county Gazetteer

Usage from the project root:
  python scripts/publish_counties.py
  python scripts/publish_counties.py --county-csv PATH --gazetteer-zip PATH
  python scripts/publish_counties.py --check-only

No network requests are performed. A bad/missing source never overwrites the current catalog.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / 'data' / 'raw' / 'census'
OUT = ROOT / 'app' / 'data' / 'county_rail_inputs.csv'
COLUMNS = ('fips','name','state','population','median_income','latitude','longitude','source')
SOURCE = 'County ACS-derived CSV (third-party distributor) + 2025 Census Gazetteer'


def load_gazetteer(zip_path: Path):
    with zipfile.ZipFile(zip_path) as archive:
        candidates = [n for n in archive.namelist() if n.lower().endswith(('.txt','.csv')) and not n.startswith('__MACOSX/')]
        if not candidates:
            raise ValueError('Gazetteer ZIP has no .txt or .csv file')
        text = archive.read(candidates[0]).decode('utf-8-sig')
    # Census files sometimes use tab delimiters, other editions use pipes.
    first = text.splitlines()[0]
    delimiter = '\t' if '\t' in first else ('|' if '|' in first else ',')
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError('Gazetteer has no header')
    reader.fieldnames = [h.strip().upper() for h in reader.fieldnames]
    missing = set(('GEOID','NAME','INTPTLAT','INTPTLONG'))-set(reader.fieldnames)
    if missing:
        raise ValueError('Missing Gazetteer fields: '+', '.join(sorted(missing)))
    geo = {}
    for row in reader:
        code = (row.get('GEOID') or '').strip().zfill(5)
        if len(code)==5 and code.isdigit():
            geo[code] = {k: (v or '').strip() for k,v in row.items()}
    return geo


def build(acs, geo):
    if not isinstance(acs,list) or not acs or not isinstance(acs[0],list):
        raise ValueError('ACS file must contain a JSON array of arrays as downloaded from Census')
    header = acs[0]
    required = {'state','county','B01003_001E','B19013_001E'}
    missing = required-set(header)
    if missing:
        raise ValueError('Missing ACS columns: '+', '.join(sorted(missing)))
    positions={name:header.index(name) for name in required}
    out=[]; missing_geo=[]; bad=[]
    for row in acs[1:]:
        try:
            fips=(str(row[positions['state']])+str(row[positions['county']])).zfill(5)
            g=geo.get(fips)
            if not g:
                missing_geo.append(fips);continue
            population=int(row[positions['B01003_001E']])
            if population<=0:
                bad.append(fips);continue
            lat=float(g['INTPTLAT']);lon=float(g['INTPTLONG'])
            if not (-90<=lat<=90 and -180<=lon<=180):
                bad.append(fips);continue
            try:
                income=int(row[positions['B19013_001E']])
                if income<0:income=0  # Census suppression sentinels: unknown, not negative income
            except (ValueError,TypeError):income=0
        except (ValueError,TypeError,KeyError,IndexError):
            bad.append(str(row[-2:]));continue
        out.append({'fips':fips,'name':g['NAME'],'state':g.get('USPS',''),
                    'population':population,'median_income':income,'latitude':lat,
                    'longitude':lon,'source':SOURCE})
    out.sort(key=lambda r:r['fips'])
    return out, sorted(set(missing_geo)), sorted(set(bad))


def build_county_csv(county_csv: Path, geo):
    """Match a downloaded county CSV to official Gazetteer geometry by 5-digit FIPS.

    No guessed centroids or route-specific geographic matching. Reject malformed
    duplicate GEO_IDs rather than accepting a silently overwritten row.
    """
    out = []
    missing_geo = []
    invalid = []
    seen = set()
    with county_csv.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        required = {'GEO_ID', 'pop_total_est', 'income_median_household_income_est'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('County CSV missing columns: ' + ', '.join(sorted(required-set(reader.fieldnames or []))))
        for line, row in enumerate(reader, 2):
            geoid = (row.get('GEO_ID') or '').strip()
            if not geoid.startswith('0500000US') or len(geoid) != 14 or not geoid[-5:].isdigit():
                invalid.append('line ' + str(line) + ': GEO_ID')
                continue
            fips = geoid[-5:]
            if fips in seen:
                raise ValueError(f'Duplicate county GEO_ID: {geoid} on line {line}')
            seen.add(fips)
            g = geo.get(fips)
            if not g:
                missing_geo.append(fips)
                continue
            try:
                population = int(float((row.get('pop_total_est') or '').replace(',', '').strip()))
                latitude = float(g['INTPTLAT'])
                longitude = float(g['INTPTLONG'])
                if population <= 0 or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError('invalid population or coordinate')
            except (ValueError, TypeError, KeyError):
                invalid.append(fips)
                continue
            income_text = (row.get('income_median_household_income_est') or '').replace(',', '').strip()
            try:
                income = int(float(income_text))
                if income < 0:
                    income = 0
            except (ValueError, TypeError):
                income = 0
            out.append({
                'fips': fips,
                'name': g['NAME'],
                'state': g.get('USPS', ''),
                'population': population,
                'median_income': income,
                'latitude': latitude,
                'longitude': longitude,
                'source': SOURCE,
            })
    out.sort(key=lambda r: r['fips'])
    return out, sorted(set(missing_geo)), sorted(set(invalid))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--county-csv',type=Path,default=DEFAULT_RAW/'census_data_all_county.csv',help='Downloaded county table; default input')
    parser.add_argument('--acs-json',type=Path,default=None,help='Optional legacy ACS API JSON instead of CSV')
    parser.add_argument('--gazetteer-zip',type=Path,default=DEFAULT_RAW/'2025_Gaz_counties_national.zip')
    parser.add_argument('--check-only',action='store_true',help='Inspect inputs and report coverage; do not publish')
    args=parser.parse_args(argv)
    input_label, input_path = ('ACS JSON',args.acs_json) if args.acs_json else ('County CSV',args.county_csv)
    for label,path in [(input_label,input_path),('Gazetteer ZIP',args.gazetteer_zip)]:
        if not path.is_file():
            raise FileNotFoundError(f'{label} not found: {path}\nDownload it using the links in RAIL_RIDERSHIP_OFFLINE_DATA.md and save to data/raw/census/.')
    geo=load_gazetteer(args.gazetteer_zip)
    if args.acs_json:
        acs=json.loads(args.acs_json.read_text(encoding='utf-8-sig'))
        rows,unmatched,invalid=build(acs,geo)
        print(f'ACS rows: {len(acs)-1:,}; Gazetteer codes: {len(geo):,}; matched valid counties: {len(rows):,}')
    else:
        rows,unmatched,invalid=build_county_csv(args.county_csv,geo)
        print(f'County CSV rows: {len(rows)+len(unmatched)+len(invalid):,}; Gazetteer codes: {len(geo):,}; matched valid counties: {len(rows):,}')
    print(f'Unmatched geography: {len(unmatched):,} ({", ".join(unmatched[:12]) or "none"})')
    print(f'Invalid/zero-population: {len(invalid):,} ({", ".join(invalid[:12]) or "none"})')
    if len(rows)<3000:
        raise ValueError(f'Only {len(rows):,} valid counties: refusing to overwrite existing catalog (minimum 3,000).')
    if args.check_only:
        print('Validation passed; no files changed.')
        return
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix('.csv.tmp')
    try:
        with tmp.open('w',newline='',encoding='utf-8') as fh:
            writer=csv.DictWriter(fh,fieldnames=COLUMNS)
            writer.writeheader();writer.writerows(rows)
        tmp.replace(OUT)
    finally:
        tmp.unlink(missing_ok=True)
    print(f'Published {len(rows):,} county records to {OUT.relative_to(ROOT)}')
    print('Restart Flask to reload the catalog.')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,json.JSONDecodeError,zipfile.BadZipFile) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
