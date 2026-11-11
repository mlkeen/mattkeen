# FRA Rail Performance Scorecards

## Install

Merge the `app` directory from the small update ZIP into your existing project.
Do not overwrite or delete your `data/raw`, `data/processed`, or other local files.

### Data requirements

- The scorecards use the **existing** `app/data/fra_ridership.csv` (included with the earlier ridership update).
- To enable **revenue per rider** and **revenue per passenger-mile**, run:

  ```powershell
  .\.venv\Scripts\python.exe scripts\publish_financials.py
  ```

  This reads locally processed financial CSVs and writes `app/data/fra_financials.json`.
  The update does **not** require importing the 179 source workbooks again.
- To enable customer OTP rankings if not already active, run:

  ```powershell
  .\.venv\Scripts\python.exe scripts\publish_customer_otp.py
  ```

Restart Flask:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:5000/projects/intercity-rail/scorecards

API: http://127.0.0.1:5000/api/rail/scorecards

## Revenue definitions and safeguards

- **Passenger revenue per rider** = passenger revenue / route quarterly total ridership.
- **Passenger revenue per passenger-mile** = passenger revenue / reported route quarterly passenger-miles.
- Passenger revenue comes from `avoidable_expense` financial records' `passenger_revenue` numerator; **not** total/adjusted operating revenue.
- Same APT code, same reported route name (case and whitespace normalized), same fiscal quarter required. Neither fuzzy route merging nor aggregated system rows used.
- When state-payment variants disagree about passenger revenue, show N/A and flag the conflict.
- Negative passenger revenue, missing passenger revenue, and zero or negative denominators result in N/A, never an invented figure.
- Financial publishing must be complete for revenue metrics; if missing, the page still shows ridership and any available OTP.
- Financial ratio quality flags are handled by the financial publisher. OTP is only shown for exact whole-service matches.
- Revenue yield is not an individual ticket fare, operating profit, or net economic benefit.

## Files changed

- `app/routes.py` (two new endpoints)
- `app/scorecards_service.py` (join and metrics)
- `app/templates/rail_scorecards.html` (new page)
- `app/templates/intercity_rail.html` (page link)
- `app/static/css/site.css` (isolated scorecards CSS)
- `app/static/js/rail_scorecards.js` (filters, ordering, export)
- `tests/test_scorecards.py` (data and endpoint tests)
