from flask import Blueprint, jsonify, render_template, request
from .rail_forecast_engine import counties,forecast,published_calibration,published_nhts_profile
bp=Blueprint('rail_forecast',__name__)

@bp.get('/projects/rail-ridership-estimator')
def page():return render_template('rail_forecast.html')

@bp.get('/api/rail-forecast/counties')
def catalog():
    return jsonify({'counties':counties(),'loaded':bool(counties()),'calibration_status':'route_total_calibrated' if published_calibration() and len(counties())>=3000 else 'uncalibrated', 'data_note':'County census data (after running publisher) or explicitly labeled demonstration observations'})

@bp.get('/api/rail-forecast/calibration')
def calibration_report():
    doc=published_calibration()
    if not doc:return jsonify({'status':'not_published','message':'Publish real county data and run calibrate_rail_forecast.py first.'}),404
    return jsonify(doc)

@bp.get('/api/rail-forecast/nhts')
def nhts_profile():
    d=published_nhts_profile()
    if not d:return jsonify({'status':'not_published','message':'Run scripts/publish_nhts_2022.py on the official 2022 NHTS long-distance CSV.'}),404
    return jsonify(d)

@bp.post('/api/rail-forecast/estimate')
def estimate():
    try:return jsonify(forecast(request.get_json(silent=True) or {}))
    except (ValueError, TypeError,OverflowError) as exc:return jsonify({'error':str(exc)}),400
