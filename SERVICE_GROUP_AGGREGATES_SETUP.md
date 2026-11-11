# Service-group aggregates (site update)

Install over the current site, preserving app/data/ and data/processed/. Restart Flask.

- On Ridership, Delay Explorer, Economics, and Station Map, pick a **Service group** and leave the **Service** dropdown on **All routes/reporting units in selected group**. Selecting a route switches back to its data.
- Ridership sums eligible route-level passenger counts, never the system aggregate. A negative adjustment makes its group-quarter unavailable instead of silently suppressing the value.
- Delay totals sum reporting-unit delay minutes, not miles-normalized rates. Operational units may overlap.
- Financial cost recovery and expense coverage are **sum(revenues) / sum(expenses)**, *never average of ratios*. A flagged financial component makes the group-quarter/measure unavailable.
- Station percentages are **sum(late detraining passengers) / sum(detraining passengers)**; this may double count if operational source reporting units overlap.
- Customer OTP deliberately does not provide a group total: available percentages are not safely aggregatable without matched customer-level or passenger-weighted numerators/denominators. The reliability regression remains route-level.
- Scorecards already filter group members and rank individual services; an unranked group total is not a comparable competitor in a route leaderboard.

To inspect group JSON directly: `/api/rail/routes/group:long_distance`, `/api/rail/delays/group:long_distance`, `/api/rail/economics/detail?service=group:long_distance`, `/api/rail/stations/detail?service=group:long_distance&period=all&min_customers=1`.
