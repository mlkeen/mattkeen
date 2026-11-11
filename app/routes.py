from flask import Blueprint, abort, jsonify, render_template, request
from .services import get_all_routes, get_default_route, get_route, get_summary, get_system_trend, get_group_ridership
from .otp_service import get_otp_match, get_otp_overview, get_otp_service

from .compare_service import comparison_catalog, get_comparison

from .delay_service import overview as delay_overview, detail as delay_detail_data, delay_codes as delay_code_dictionary

from .financial_service import overview as financial_overview, detail as financial_detail

from .reliability_service import catalog as reliability_catalog, data as reliability_data

bp = Blueprint("main", __name__)


def with_matched_otp(route):
    """Enrich a ridership route only on a conservative one-to-one match."""
    return {**route, "otp": get_otp_match(route["name"])}


@bp.get("/")
def home():
    from .rail_forecast_engine import counties
    county_count = len(counties())
    return render_template(
        "index.html",
        summary=get_summary(),
        station_preview=station_overview(),
        county_count=county_count,
        county_is_nationwide=county_count >= 3000,
    )


@bp.get("/projects/intercity-rail")
def intercity_rail():
    selected = get_default_route()
    routes = get_all_routes()
    return render_template(
        "intercity_rail.html", summary=get_summary(),
        routes=routes, selected=selected,
        otp=get_otp_overview(),
        selected_otp=get_otp_match(selected["name"]),
        otp_route_match={r["slug"]: get_otp_match(r["name"]) for r in routes},
    )


@bp.get("/projects/intercity-rail/routes/<slug>")
def route_detail(slug):
    route = get_route(slug)
    if route is None:
        abort(404)
    return render_template("route_detail.html", route=route, otp=get_otp_match(route["name"]), otp_available=get_otp_overview()["available"])


@bp.get("/workbench")
def workbench():
    return render_template("workbench.html")


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.get("/api/rail/routes")
def rail_routes_api():
    return jsonify(get_all_routes())


@bp.get("/api/rail/routes/<slug>")
def rail_route_api(slug):
    route = get_group_ridership(slug[6:]) if slug.startswith('group:') else get_route(slug)
    if route is None: abort(404)
    return jsonify({**route, 'otp':None} if route.get('is_group') else with_matched_otp(route))


@bp.get("/api/rail/ridership/system")
def system_ridership_api():
    return jsonify({"summary": get_summary(), "series": get_system_trend()})


@bp.get("/api/rail/otp/routes")
def otp_routes_api():
    return jsonify(get_otp_overview())


@bp.get("/api/rail/otp/routes/<slug>")
def otp_route_api(slug):
    result = get_otp_service(slug)
    if result is None:
        abort(404)
    return jsonify(result)


@bp.get("/projects/intercity-rail/compare")
def comparison_lab():
    catalog = comparison_catalog()
    preferred = ["downeaster", "acela-express", "california-zephyr"]
    available = {r["slug"] for r in catalog}
    defaults = [r for r in preferred if r in available]
    if not defaults:
        defaults = [r["slug"] for r in catalog[:3]]
    return render_template("comparison_lab.html", routes=catalog, defaults=defaults,
                           comparison=get_comparison(defaults))


@bp.get("/api/rail/compare")
def compare_api():
    slugs = request.args.getlist("route")
    try:
        result = get_comparison(slugs)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.get("/projects/intercity-rail/delays")
def delay_explorer():
    return render_template("delay_explorer.html", overview=delay_overview())


@bp.get("/api/rail/delays")
def delay_catalog_api():
    return jsonify(delay_overview())


@bp.get("/api/rail/delays/codes")
def delay_codes_api():
    return jsonify(delay_code_dictionary())


@bp.get("/api/rail/delays/<identifier>")
def delay_detail_api(identifier):
    result = delay_detail_data(identifier)
    if result is None:
        abort(404)
    return jsonify(result)


@bp.get('/projects/intercity-rail/economics')
def rail_economics():
    return render_template('rail_economics.html', overview=financial_overview())

@bp.get('/api/rail/economics')
def rail_economics_catalog():
    return jsonify(financial_overview())

@bp.get('/api/rail/economics/detail')
def rail_economics_detail():
    identifier=request.args.get('service','system')
    result=financial_detail(identifier)
    if result is None:abort(404)
    return jsonify(result)


@bp.get('/projects/intercity-rail/reliability')
def reliability_lab():
    return render_template('reliability_lab.html', catalog=reliability_catalog())

@bp.get('/api/rail/reliability')
def reliability_api():
    try:
        return jsonify(reliability_data(route_slugs=request.args.getlist('route'),period=request.args.get('period','all')))
    except ValueError as exc:
        return jsonify({'error':str(exc)}),400


from .station_service import overview as station_overview, detail as station_detail

@bp.get('/projects/intercity-rail/stations')
def station_map_page():
    return render_template('station_map.html', overview=station_overview())

@bp.get('/api/rail/stations')
def station_catalog_api():
    return jsonify(station_overview())

@bp.get('/api/rail/stations/detail')
def station_detail_api():
    try:
        count=int(request.args.get('min_customers','1'))
        result=station_detail(request.args.get('service',''),request.args.get('period','all'),count)
    except ValueError as exc:
        return jsonify({'error':str(exc)}),400
    if result is None:abort(404)
    return jsonify(result)


from .scorecards_service import overview as scorecards_overview, detail as scorecards_detail

@bp.get('/projects/intercity-rail/scorecards')
def scorecards_page():
    return render_template('rail_scorecards.html', overview=scorecards_overview())

@bp.get('/api/rail/scorecards')
def scorecards_api():
    try:
        min_riders = int(request.args.get('minimum_riders', '0'))
        return jsonify(scorecards_detail(
            period=request.args.get('period'), category=request.args.get('category', 'all'),
            sort=request.args.get('sort', 'ridership'),
            direction=request.args.get('direction', 'desc'), minimum_riders=min_riders))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
