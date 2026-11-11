# Repair: missing rail forecasting engine

The homepage update imported `app.rail_forecast_engine` but did not include the corresponding forecasting feature files. This ZIP supplies the missing module, its route blueprint, template, JavaScript, and CSS. **It does not overwrite `app/routes.py`, `app/__init__.py`, or any county data or publisher scripts.**

## Install

1. Stop your Flask server (Ctrl+C).
2. Extract this ZIP to `C:\Users\Matt\Documents\mattkeen`, merging folders.
3. Make sure `app/__init__.py` registers the forecasting blueprint (it probably already does):

```python
from .rail_forecast import bp as rail_forecast_bp
app.register_blueprint(rail_forecast_bp)
```

These lines must be inside `create_app`, after `app = Flask(...)` and before `return app`. Do not add them a second time if already present.

4. Verify the module exists:

```powershell
.\.venv\Scripts\python.exe -c "from app.rail_forecast_engine import counties; print('County records:', len(counties()))"
```

5. Restart:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open `/` and `/projects/rail-ridership-estimator`.

**County data:** If the check prints `0`, the package does not include a demonstration catalog so that real published data cannot be overwritten. Run `scripts/publish_counties.py` with your downloaded files, if not already done.

**Important:** The forecasting model is an uncalibrated sketch model. The county population data are inputs, not validation of predictions.
