# Route and service groups — installation

Use `mattkeen-fra-service-groups-site-update.zip` to update an existing site. Extract and merge its `app/` and `tests/` directories into `C:\Users\Matt\Documents\mattkeen` (back up the folder first). Retain all original Excel files, processed CSVs, and previously published JSON data. Restart Flask:

```powershell
.\.venv\Scripts\python.exe run.py
```

No data import or publishing commands are needed.

## Filters

A **Service group** dropdown appears in the main Rail Explorer's ridership and OTP selectors, its route table, the Comparison Lab, Delay Explorer, Economics Lab, and Reliability Lab. These filters change which reporting services are selectable; they never aggregate or recompute source metrics. A group selection in a checklist hides other choices without removing existing selections. Use **Compare first four visible services** in the Comparison Lab or **Select visible** in the Reliability Lab to quickly change the selected services to the current visible group.

Five categories are offered: **Acela**, **State Supported Service**, **Long Distance**, **Other Northeast Corridor**, and **Special / Unclassified**. The latter two avoid misclassifying Northeast Regional or special trains, which do not belong to the requested three groups. See `app/service_categories.py` for the auditable code crosswalk. Historical reporting names are classified by original APT route code. Operational OTP and delay service labels use exact matching against the ridership catalog where possible; unknown names remain Unclassified, not guessed.

## Important distinction

FRA describes the actual operating service lines as NEC, State Supported, and Long Distance. Some physical NEC trains carry financially State Supported segments, especially Springfield and Virginia services. This crosswalk follows the financial reporting-route records used by the site; it does not assert a separately operated or subsidized train for each entry. The categories are not additive financial or operational system totals; use verified denominator and reporting definitions before calculating category-level statistics.

External reference: [FRA Methodology Report, FY2025 Q2](https://railroads.fra.dot.gov/sites/fra.dot.gov/files/2025-07/FY25%20Q2%20Methodology%20Report.pdf).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_service_categories
```

The updated category fields are returned in the ridership, comparison, delay, financial, OTP and reliability route catalogs and details. Changing the category crosswalk doesn't modify the FRA extracts.
