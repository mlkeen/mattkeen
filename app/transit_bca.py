from flask import Blueprint, jsonify, render_template, request
from .bca_engine import DEFAULTS, analyze, scenarios

bp=Blueprint('transit_bca',__name__)

@bp.get('/projects/transit-bca')
def calculator():
    return render_template('transit_bca.html',defaults=DEFAULTS)

@bp.post('/api/transit-bca/analyze')
def api():
    if not request.is_json:
        return jsonify({'error':'JSON body required'}),400
    try:
        body=request.get_json()
        if not isinstance(body,dict): raise ValueError('Expected a JSON object')
        result=analyze(body)
        result['scenarios']=scenarios(body)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({'error':str(exc)}),400
