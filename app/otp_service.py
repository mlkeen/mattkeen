"""FRA *route-level* customer on-time performance (C OTP).

Preserves reporting grain (service + subservice). Never calculates a route
value from unweighted train or subservice percentages. Missing source CSV is
an explicit no-data state, not illustrative data.
"""
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from .service_categories import category_for_operational

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_OTP = ROOT / "app" / "data" / "fra_customer_otp_route.csv"
PROCESSED_OTP = ROOT / "data" / "processed" / "customer_otp_route.csv"


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _exact(s):
    # Case/whitespace only; deliberately not a fuzzy crosswalk.
    return " ".join(s.casefold().split())


def _ratio(s):
    if s is None or str(s).strip() == "":
        return None
    n = float(s)
    if not math.isfinite(n) or not 0 <= n <= 1:
        raise ValueError(f"Invalid route-level customer OTP proportion {s!r}")
    return n


def _period(p):
    return f"FY{p[0]} Q{p[1]}"


def _number_or_none(s):
    return int(s) if s and str(s).strip().isdigit() else s or None


@lru_cache(maxsize=1)
def _load():
    # During local development, use the ETL output if the deployment CSV has
    # not been published. Deployment ships the validated published copy.
    path = PUBLISHED_OTP if PUBLISHED_OTP.is_file() else PROCESSED_OTP
    if not path.is_file():
        return {"available": False, "services": [], "by_slug": {}, "by_name": {}, "periods": [], "source": None}
    observations = defaultdict(dict)
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"fiscal_year", "fiscal_quarter", "service", "sub_service", "customer_otp"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"OTP CSV is missing required columns: {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            try:
                p = (int(row["fiscal_year"]), int(row["fiscal_quarter"]))
                if p[1] not in (1, 2, 3, 4):
                    raise ValueError("invalid quarter")
                service = row["service"].strip()
                subservice = row["sub_service"].strip()
                if not service or not subservice:
                    raise ValueError("blank service/subservice")
                value = _ratio(row["customer_otp"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid OTP data in {path.name} at CSV row {line}: {exc}") from exc
            key = (service, subservice)
            if (p, key) in seen:
                raise ValueError(f"Duplicate OTP observation for {_period(p)} / {key}")
            seen.add((p, key))
            observations[key][p] = {
                "value": value,
                "source_workbook": row.get("source_workbook") or None,
                "source_sheet": row.get("source_sheet") or None,
                "source_excel_row": _number_or_none(row.get("source_excel_row")),
            }
    source_periods = sorted({p for values in observations.values() for p in values})
    # Align reliability charts with ridership's complete quarterly axis. In
    # particular FY2021 Q4 has train-level but no route-level C OTP.
    from .services import get_system_trend
    ridership_periods = set()
    for point in get_system_trend():
        match = re.fullmatch(r"FY(\d{4}) Q([1-4])", point["period"])
        if match:
            ridership_periods.add((int(match.group(1)), int(match.group(2))))
    periods = sorted(set(source_periods) | ridership_periods)
    by_slug = {}
    by_name = defaultdict(list)
    services = []
    for key, observations_by_period in sorted(observations.items()):
        service, subservice = key
        slug = _slug(service + "--" + subservice)
        if slug in by_slug:
            raise ValueError(f"Ambiguous customer OTP URL slug: {slug}")
        latest = source_periods[-1]
        value = observations_by_period.get(latest, {}).get("value")
        prev = observations_by_period.get((latest[0]-1, latest[1]), {}).get("value")
        yoy_pp = round(100 * (value - prev), 1) if value is not None and prev is not None else None
        series = []
        for p in periods:
            observation = observations_by_period.get(p)
            v = observation["value"] if observation else None
            prior = observations_by_period.get((p[0]-1, p[1]), {}).get("value")
            series.append({
                "period": _period(p), "fiscal_year": p[0], "fiscal_quarter": p[1],
                "otp": v, "yoy_pp": round(100 * (v - prior), 1) if v is not None and prior is not None else None,
                "status": "not_reported" if observation is None else "missing_value" if v is None else "reported",
                "source_workbook": observation["source_workbook"] if observation else None,
                "source_sheet": observation["source_sheet"] if observation else None,
                "source_excel_row": observation["source_excel_row"] if observation else None,
            })
        detail = {
            "slug": slug, "service": service, "sub_service": subservice,
            "category": category_for_operational(service, subservice),
            "label": service if _exact(service) == _exact(subservice) else f"{service} / {subservice}",
            "latest_otp": value, "latest_period": _period(latest), "yoy_pp": yoy_pp,
            "quarters_reported": len(observations_by_period),
            "quarters_valid": sum(o["value"] is not None for o in observations_by_period.values()),
            "series": series,
        }
        by_slug[slug] = detail
        services.append({k: detail[k] for k in ("slug", "service", "sub_service", "category", "label", "latest_otp", "latest_period", "yoy_pp", "quarters_reported", "quarters_valid")})
        # Only auto-match to a ridership *named* route if the entire OTP
        # service is the same as its subservice. Otherwise the route-level
        # OTP might represent just one of several subdivisions.
        if _exact(service) == _exact(subservice):
            by_name[_exact(subservice)].append(detail)

    return {"available": True, "services": services, "by_slug": by_slug,
            "by_name": by_name, "periods": periods, "source": path.name}


def get_otp_overview():
    data = _load()
    return {"available": data["available"], "services": data["services"],
            "latest_period": _period(data["periods"][-1]) if data["periods"] else None,
            "period_count": len(data["periods"]), "source_quarters": len({(obs["fiscal_year"], obs["fiscal_quarter"]) for item in data["by_slug"].values() for obs in item["series"] if obs["status"] != "not_reported"}), "source": data["source"]}


def get_otp_service(slug):
    return _load()["by_slug"].get(slug)


def get_otp_match(route_name):
    """Conservative exact match only; no route/subservice aggregation."""
    matches = _load()["by_name"].get(_exact(route_name), [])
    return matches[0] if len(matches) == 1 else None
