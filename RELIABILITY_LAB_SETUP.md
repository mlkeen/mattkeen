# Reliability vs. Ridership — Installation

## Existing website
1. Back up your project folder. Extract `mattkeen-fra-reliability-site-update.zip` into `C:\Users\Matt\Documents\mattkeen` (merge/replace matching files).
2. Check `app/data/fra_customer_otp_route.csv` exists. If missing, run `.\.venv\Scripts\python.exe scripts\publish_customer_otp.py` with your `data/processed/customer_otp_route.csv` in place.
3. Restart: `.\.venv\Scripts\python.exe run.py`.
4. Open `http://127.0.0.1:5000/projects/intercity-rail/reliability`.

The shipped package does not contain private/unuploaded OTP observations. It reads your locally published OTP data. Ridership is included in the project from the previously validated CSV.

## Methodology
- Join route ridership to route-level OTP **only** where OTP `service` equals `sub_service` and exactly equals the ridership service name (case/whitespace normalization only), with no ambiguous matches.
- X: change in customer OTP from the same fiscal quarter one year earlier **in percentage points**. Y: ridership year-on-year percentage growth. Missing and invalid observations are excluded.
- The fit is pooled, unweighted OLS. Pearson r and R² are descriptive; not a causal estimate, adjusted regression, or statistical significance test. Repeated route quarters are not independent.
- Download filtered values using the button on the page, with workbook references for audit.
- Data is not cached by the new service: restart Flask after publishing source CSVs because older loaders use cache.
