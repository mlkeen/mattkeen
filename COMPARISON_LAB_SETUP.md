# Route Comparison Lab

Adds `/projects/intercity-rail/compare` and `/api/rail/compare?route=downeaster&route=california-zephyr`.

## Installation in an existing mattkeen folder

1. Back up the site.
2. Extract the **site-update ZIP** and merge its `app/` and `tests/` directories into your working project. Do not remove any existing files, `data/processed/`, or original workbooks.
3. Restart Flask: `\.venv\Scripts\python.exe run.py`.
4. Open `http://127.0.0.1:5000/projects/intercity-rail/compare`, or follow the new link from the Rail Explorer.
5. Run tests (optional): `\.venv\Scripts\python.exe -m pytest tests/test_comparison_lab.py -q`.

Works with the published `app/data/fra_ridership.csv` shipped with the earlier ridership update. To enable customer OTP comparison, publish it first: `\.venv\Scripts\python.exe scripts\publish_customer_otp.py`. The comparison page will otherwise display ridership and explicitly label OTP as unavailable.

## Methodology

- Select 1–4 route histories. Year-over-year change is **percent**, and compares the corresponding fiscal quarter a year earlier.
- Indexed ridership uses the **first shared fiscal quarter with positive ridership for every selected service**, with that baseline set to 100. If no common base exists, index is unavailable.
- Missing quarters and negative source adjustments remain gaps. No automatic joining of alternate service names or reused APT codes.
- OTP plotted only when there is an unambiguous exact whole-service (service and subservice) match to the ridership route name. No averaging across train-level percentages, and no inferred overall rate for split services.
- For audit and granularity, inspect each service's linked route detail page.
