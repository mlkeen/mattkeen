# FRA Passenger Rail Economics – Site Update

## Install (Windows PowerShell)

1. Back up `C:\Users\Matt\Documents\mattkeen`.
2. Extract the **site-update** ZIP over your existing project, merging directories and replacing matching files. Do not delete `data/processed`, `data/raw/fra`, or the existing ETL scripts.
3. Publish your existing imported data from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\publish_financials.py
```

4. Restart Flask with `.\.venv\Scripts\python.exe run.py`.
5. Visit `http://127.0.0.1:5000/projects/intercity-rail/economics`.

The publisher reads three processed financial CSVs, produces `app/data/fra_financials.json`, and does not modify existing datasets. The full-project archive contains no actual financial data: publish it locally.

## Integrity protections

- Only one FRA reporting code *and* name constitute a route series. System total (`APT_All_APT`) is not combined with route rows.
- Financial ratios remain fractions in storage; the chart multiplies by 100 for percentage display.
- State-payment included/excluded series stay separate. Cost recovery has no state-payment toggle.
- Missing, negative, zero-denominator, or materially inconsistent rows are retained for inspection but excluded from charts.
- Above-100% ratios are allowed when source arithmetic and sign checks pass.
- A flag does **not** assert the published accounting observation is wrong.
- Original source workbook/sheet/Excel-row fields are preserved.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_financials.py
```

The cost-recovery and expense-coverage definitions refer to distinct FRA measures. Do not treat expense coverage as a benefit–cost ratio or claim the plots establish causal relationships.
