"""Read the published FRA financial-metrics ridership extract.

We intentionally distinguish named services from APT system/adjustment rows,
and distinguish two names even when FRA has reused an APT code.
"""
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from .service_categories import category_for_apt

PUBLISHED_CSV = Path(__file__).resolve().parent / "data" / "fra_ridership.csv"


def _number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _format_period(period):
    return f"FY{period[0]} Q{period[1]}"


def _yoy(current, previous):
    if current is None or previous is None or current < 0 or previous <= 0:
        return None
    return round(100 * (current / previous - 1), 1)


@lru_cache(maxsize=1)
def _load():
    if not PUBLISHED_CSV.is_file():
        raise FileNotFoundError(
            f"Missing published ridership data at {PUBLISHED_CSV}. "
            "Run scripts/publish_ridership.py after FRA ETL."
        )

    rows = []
    unique_keys = set()
    with PUBLISHED_CSV.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"fiscal_year", "fiscal_quarter", "apt_code", "route", "ridership", "reporting_level"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Ridership CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            year, quarter = int(row["fiscal_year"]), int(row["fiscal_quarter"])
            if not 1 <= quarter <= 4:
                raise ValueError(f"Invalid quarter {quarter} in {row['source_workbook']}")
            key = (year, quarter, row["apt_code"])
            if key in unique_keys:
                raise ValueError(f"Duplicate fiscal quarter + APT code: {key}")
            unique_keys.add(key)
            rows.append({
                "period_key": (year, quarter),
                "apt_code": row["apt_code"],
                "name": row["route"].strip(),
                "level": row["reporting_level"],
                "ridership_raw": _number(row.get("ridership")),
                "passenger_miles": _number(row.get("passenger_miles")),
                "train_miles": _number(row.get("train_miles")),
                "source_workbook": row.get("source_workbook", ""),
                "source_sheet": row.get("source_sheet", ""),
                "source_excel_row": row.get("source_excel_row", ""),
            })

    periods = sorted({row["period_key"] for row in rows})
    systems = {r["period_key"]: r for r in rows if r["apt_code"] == "APT_All_APT" and r["level"] == "aggregate"}
    if set(systems) != set(periods):
        raise ValueError("Missing one or more distinct APT_All_APT system totals")

    # APT codes can be reused/rebranded, so a series is identified by (code, name),
    # not merely by code. Never splice these histories together without a crosswalk.
    named = defaultdict(dict)
    code_names = defaultdict(set)
    for r in rows:
        if r["level"] != "route":
            continue
        series_key = (r["apt_code"], r["name"])
        named[series_key][r["period_key"]] = r
        code_names[r["apt_code"]].add(r["name"])

    latest = periods[-1]
    prior_year = (latest[0] - 1, latest[1])
    route_list, detail_by_slug = [], {}
    for (apt_code, name), observations in named.items():
        slug = _slug(name)
        if slug in detail_by_slug:
            slug = f"{slug}-{_slug(apt_code)}"
        latest_row = observations.get(latest)
        latest_value = latest_row["ridership_raw"] if latest_row else None
        if latest_value is not None and latest_value < 0:
            latest_value = None
        previous_row = observations.get(prior_year)
        previous_value = previous_row["ridership_raw"] if previous_row else None
        valid_periods = [p for p, row in observations.items() if row["ridership_raw"] is not None and row["ridership_raw"] >= 0]
        overview = {
            "slug": slug,
            "name": name,
            "apt_code": apt_code,
            "category": category_for_apt(apt_code, name),
            "latest_ridership": latest_value,
            "latest_period": _format_period(latest),
            "yoy_pct": _yoy(latest_value, previous_value),
            "quarters_reported": len(observations),
            "quarters_valid": len(valid_periods),
            "first_reported": _format_period(min(observations)),
            "last_reported": _format_period(max(observations)),
            "other_names_same_code": sorted(code_names[apt_code] - {name}),
        }
        series = []
        issues = []
        for p in periods:
            r = observations.get(p)
            raw = r["ridership_raw"] if r else None
            passenger_count = raw if raw is not None and raw >= 0 else None
            p_last = (p[0] - 1, p[1])
            prior_r = observations.get(p_last)
            prior = prior_r["ridership_raw"] if prior_r else None
            negative = raw is not None and raw < 0
            if negative:
                issues.append(f"{_format_period(p)}: negative source adjustment ({raw:,.0f}); excluded from the plotted series")
            series.append({
                "period": _format_period(p),
                "fiscal_year": p[0],
                "fiscal_quarter": p[1],
                "ridership": passenger_count,
                "source_value": raw,
                "yoy_pct": _yoy(passenger_count, prior),
                "status": ("not_reported" if r is None else "negative_adjustment" if negative else "reported"),
                "source_workbook": r["source_workbook"] if r else None,
                "source_sheet": r["source_sheet"] if r else None,
                "source_excel_row": r["source_excel_row"] if r else None,
            })
        detail_by_slug[slug] = {**overview, "series": series, "issues": issues}
        route_list.append(overview)

    route_list.sort(key=lambda r: (r["latest_ridership"] is None, -(r["latest_ridership"] or 0), r["name"]))
    system_trend = []
    for p in periods:
        r = systems[p]
        v = r["ridership_raw"]
        prev = systems.get((p[0] - 1, p[1]))
        system_trend.append({"period": _format_period(p), "ridership": v, "yoy_pct": _yoy(v, prev["ridership_raw"] if prev else None)})

    return {
        "periods": [_format_period(p) for p in periods],
        "routes": route_list,
        "details": detail_by_slug,
        "system_trend": system_trend,
        "latest_period": _format_period(latest),
        "latest_ridership": systems[latest]["ridership_raw"],
        "latest_yoy": system_trend[-1]["yoy_pct"],
        "active_services": sum(r["latest_ridership"] is not None and r["latest_ridership"] > 0 for r in route_list),
    }


def get_all_routes():
    return _load()["routes"]


def get_route(slug):
    return _load()["details"].get(slug)


def get_system_trend():
    return _load()["system_trend"]


def get_summary():
    data = _load()
    return {
        "route_count": len(data["routes"]),
        "active_services": data["active_services"],
        "period_count": len(data["periods"]),
        "latest_ridership": data["latest_ridership"],
        "latest_yoy": data["latest_yoy"],
        "period": data["latest_period"],
        "data_status": "FRA financial-metrics workbooks, route-level total ridership (marketing).",
    }


def get_default_route():
    return get_route("downeaster") or _load()["details"][_load()["routes"][0]["slug"]]


def get_group_ridership(category):
    """Aggregate source route records, never system/adjustment rows.

    Treat a quarter with a negative/unreported route value as incomplete; do
    not silently turn a negative source adjustment into a zero-ridership trip.
    """
    from .service_categories import CATEGORY_LABELS
    if category not in CATEGORY_LABELS:
        return None
    d = _load()
    totals = defaultdict(float)
    participants = defaultdict(set)
    blocked = defaultdict(set)
    with PUBLISHED_CSV.open(encoding='utf-8-sig', newline='') as source:
        for r in csv.DictReader(source):
            if r['reporting_level'] != 'route' or category_for_apt(r['apt_code'], r['route']) != category:
                continue
            p = (int(r['fiscal_year']), int(r['fiscal_quarter']))
            code = r['apt_code']
            value = _number(r.get('ridership'))
            if code in participants[p]:
                raise ValueError(f'Duplicate APT code in group {category}: {p} {code}')
            participants[p].add(code)
            if value is None or value < 0:
                blocked[p].add(code)
            else:
                totals[p] += value
    periods = sorted({(int(p['period'][2:6]), int(p['period'][-1])) for p in d['system_trend']})
    series = []
    for p in periods:
        valid = bool(participants[p]) and not blocked[p]
        value = totals[p] if valid else None
        previous_p = (p[0]-1, p[1])
        prev = totals[previous_p] if participants[previous_p] and not blocked[previous_p] else None
        series.append({'period':_format_period(p),'fiscal_year':p[0],'fiscal_quarter':p[1],
                       'ridership':value,'source_value':value,'yoy_pct':_yoy(value, prev),
                       'status':'reported' if valid else 'incomplete' if participants[p] else 'not_reported',
                       'route_count':len(participants[p]),'excluded_codes':sorted(blocked[p])})
    latest=series[-1]
    return {'slug':'group:'+category,'apt_code':'GROUP','name':CATEGORY_LABELS[category],
            'category':category,'is_group':True,'latest_period':latest['period'],
            'latest_ridership':latest['ridership'],'yoy_pct':latest['yoy_pct'],
            'quarters_reported':sum(bool(participants[p]) for p in periods),
            'quarters_valid':sum(x['ridership'] is not None for x in series),
            'other_names_same_code':[],'issues':['Group sums use all FRA route rows in this category; incomplete quarters are gaps. Group definition is fixed by the APT code crosswalk.'],
            'series':series}
