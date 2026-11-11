"""Prepare 2022 NHTS V2.1 *long-distance person* data, offline.

Input: official NHTS CSV V2.1 distribution zip or its Long Distance CSV.
Run: python scripts/publish_nhts_2022.py --source data/raw/nhts/2022_nhts_csv.zip --check-only
     python scripts/publish_nhts_2022.py --source data/raw/nhts/2022_nhts_csv.zip

A long-distance record represents a person (NOT a trip). Use person weights.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, math, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'app/data/nhts_2022_profile.json'
REQUIRED={'WTPERFIN','LONGDIST','LD_AMT','MAINMODE'}


def input_stream(path):
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as z:
            candidates=[]
            for item in z.infolist():
                if item.is_dir() or not item.filename.lower().endswith('.csv'): continue
                with z.open(item) as f:
                    first=f.readline().decode('utf-8-sig',errors='replace').upper()
                if REQUIRED.issubset(set(next(csv.reader([first])))):
                    candidates.append(item)
            if len(candidates)!=1: raise ValueError(f'Expected one long-distance person CSV with {sorted(REQUIRED)}; found {len(candidates)}. Inspect 2022 NHTS V2.1 ZIP.')
            with z.open(candidates[0]) as raw:
                with io.TextIOWrapper(raw,encoding='utf-8-sig',newline='') as f:
                    yield f, candidates[0].filename
    else:
        with path.open(encoding='utf-8-sig',newline='') as f:
            yield f, path.name


def valid_number(v,hi=None):
    try:x=float(v)
    except (TypeError,ValueError):return None
    if not math.isfinite(x) or x<0 or hi is not None and x>hi:return None
    return x


def prepare(source, min_rows=1000):
    source=Path(source)
    if not source.exists():raise FileNotFoundError(source)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    counts={'rows':0,'weight_valid':0,'longdistance_valid':0,'amtrak_valid':0,'mode_valid':0}
    total_weight=ld_weight=amtrak_weight=mode_weight=0.0
    ld_sum=amt_sum=amtrak_users=amtrak_last=0.0
    member=None
    for f,member in input_stream(source):
        reader=csv.DictReader(f)
        reader.fieldnames=[n.strip().upper() for n in reader.fieldnames]
        if not REQUIRED.issubset(set(reader.fieldnames)):
            raise ValueError('NHTS long-distance fields missing. Use official 2022 V2.1 CSV ZIP, not travel-day TRIP file.')
        for row in reader:
            counts['rows']+=1
            weight=valid_number(row['WTPERFIN'])
            if not weight: continue
            counts['weight_valid']+=1;total_weight+=weight
            ld=valid_number(row['LONGDIST'],207)
            if ld is not None:
                counts['longdistance_valid']+=1;ld_weight+=weight;ld_sum+=weight*ld
            amt=valid_number(row['LD_AMT'],35)
            if amt is not None:
                counts['amtrak_valid']+=1;amtrak_weight+=weight;amt_sum+=weight*amt
                amtrak_users+=weight*(amt>0)
            mode=row['MAINMODE'].strip()
            if mode not in ('','-1','-9'):
                counts['mode_valid']+=1;mode_weight+=weight
                if mode in ('13','13.0'):amtrak_last+=weight
    if counts['weight_valid']<min_rows or not ld_weight or not amtrak_weight:
        raise ValueError(f'Insufficient eligible NHTS person records: {counts}. No output written.')
    per_month=ld_sum/ld_weight
    output={'schema_version':1,'status':'nhts_2022_person_weighted',
        'dataset':'2022 NextGen NHTS V2.1, long-distance person file',
        'source_file_member':member,'input_sha256':digest,'counts':counts,
        'weight_variable':'WTPERFIN',
        'long_distance_trips_per_person_30_days':round(per_month,6),
        'annualized_long_distance_trips_per_person':round(per_month*12,6),
        'amtrak_uses_per_person_past_year':round(amt_sum/amtrak_weight,6),
        'fraction_persons_using_amtrak_past_year':round(amtrak_users/amtrak_weight,6),
        'amtrak_share_of_most_recent_long_distance_trip':round(amtrak_last/mode_weight,6) if mode_weight else None,
        'qualifications':[
            'LONGDIST is reported trips of 50+ miles in the past 30 days; multiply by 12 only as a rough annualized benchmark, not a full-year trip census.',
            'LD_AMT is number of times person used Amtrak in past year; this is distinct from rail trips in an OD matrix.',
            'MAINMODE describes only the most recent long-distance trip, not all annual trips; its share is descriptive only, not a mode-choice coefficient.',
            'WTPERFIN is person survey weight; these are weighted point estimates without replicate-weight confidence intervals.',
            'The survey cannot establish origin-destination county rail demand, distance-decay or generalized-cost elasticities.'
        ]}
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data/raw/nhts/2022_nhts_csv.zip')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    d=prepare(args.source)
    print(json.dumps({k:v for k,v in d.items() if k not in ('qualifications',)},indent=2))
    if args.check_only:
        print('Check only: output not written.');return
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT)
    print('Published:',OUT)

if __name__=='__main__':main()
