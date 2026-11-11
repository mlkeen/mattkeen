# FRA workbook setup and historical import

The project's FIA/FRA Excel import workflow is now documented in
[`FRA_IMPORT_V2.md`](FRA_IMPORT_V2.md), based on the user's inventory of
179 workbooks over FY2021 Q4–FY2026 Q3.

The input files should be saved unchanged under `data/raw/fra/`, either
flat or in subfolders. The current Flask website still displays clearly
labelled illustrative data and **will not** switch automatically to the
imported datasets.

Run the importer with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-data.txt
.\.venv\Scripts\python.exe scripts\fra_etl.py
```

Review the generated `data/reports/fra_etl_report.json` for any errors or
unexpected missing sheets, and submit the report for further validation.

The structural inventory is a sample of Excel headers and cells. Only the
actual original workbooks can prove that every row is parsed correctly.
