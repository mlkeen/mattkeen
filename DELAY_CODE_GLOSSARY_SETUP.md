# FRA Delay Code Descriptions — Update

The Delay Explorer now labels the top 12 delay causes using FRA terminology, adds detailed tooltips, and displays a searchable glossary of every cause found for the selected service and quarter.

## Install
1. Back up your `mattkeen` project.
2. Extract the *site-update* ZIP into the project root, merging `app/` and `tests/`.
3. Restart Flask (`.\.venv\Scripts\python.exe run.py`) and hard-refresh (`Ctrl+Shift+R`).
4. Open `/projects/intercity-rail/delays`.

**No republishing of the 179 Excel workbooks or delay JSON is necessary.** The dictionary ships as a local JSON file at `app/data/delay_code_definitions.json`; the existing detail API attaches it to chart results.

## Source and interpretation
Official source: [FRA FY2024 Q4 quarterly report, Appendix D, Table 5, pp. 70–71](https://railroads.fra.dot.gov/sites/fra.dot.gov/files/2024-12/FY24%20Q4%20Performance%20and%20Service%20Quality%20Report_PDFa.pdf). These are concise paraphrases of FRA's explanations, not a claim about the underlying incident. Unknown codes display as unverified instead of being assigned a meaning.

Some categories are counterintuitive: `NOD` (unused recovery time) appears under *third-party* according to the report, and `TCD` (contractor delays) under *host-responsible*. These are preserved as source classifications.

This update does not alter reported delay minutes, financial/ridership tables, or the distinction between delay totals and delay rates.
