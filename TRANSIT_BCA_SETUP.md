# Transit Benefit–Cost Lab — initial screening tool

Open `/projects/transit-bca` after installing. No dataset import is needed.

## Incremental evaluation

The tool models costs and benefits of **build compared with no-build**, in a user-defined common real-dollar base year. Construction cost is allocated evenly through the construction period; first construction year is at t=0. Operations begin after construction. Annual flows are discounted by `(1+r)^t`, with all future flows in constant dollars.

**PV benefits**: existing-rider time savings + half-rule time benefits for new diverted/generated riders + avoided automobile resource costs + separately supplied annual safety, air quality, other and terminal residual benefits.

**PV costs**: construction capital + incremental operation and maintenance. `NPV=PV(B)-PV(C)` and `BCR=PV(B)/PV(C)` (when PV(C)>0).

The avoided-auto calculation assumes each diverted transit boarding replaces one driver-occupied automobile trip. Change auto miles to account for actual vehicle occupancy, park-and-ride, and access trips. Do not equate fare receipts with net social benefit. The simplified half-rule for new transit trips is an approximation, not a full choice-model consumer surplus calculation. Do not double count categories.

All example values (including 3.1% discount rate) are **illustrative placeholders**. The currently applicable USDOT guidance, monetization schedules, carbon discounting and program-specific requirements must be reviewed for any real application: https://www.transportation.gov/mission/office-secretary/office-policy/transportation-policy/benefit-cost-analysis-guidance

## Install

Copy included files into the existing Flask project (back up first), merging directories. Restart `python run.py`. The site homepage's old 'Benefit-Cost Sandbox' placeholder is updated to a live link. Inputs recalculate when changed; the calculate button is also available. Export the annual accounting CSV and assumptions JSON from the results column.

## Scope limits / future work

This is **not grant-ready**. It lacks: annual editable build/no-build input series; mode-specific trip/occupancy, explicit reliability valuation, social cost of carbon with guidance-specific discounting, emissions and safety physical-unit calculators, induced-demand checks, construction timing controls, net salvage accounting, local price-year conversion, validation against USDOT templates, and print/PDF technical memo export. A documented value/source registry and comparison alternatives should be next.
