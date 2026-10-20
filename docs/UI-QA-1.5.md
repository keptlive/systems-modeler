# Workbench verification 1.5

The existing workbench was inspected before the additive design pass. All existing tools, model/library workflows, chart modes, analytics, AI panels, agent connection and mobile panels remain present. The preservation inventory and visual decisions are in `UI-DIRECTION-1.5.md`.

## Actual browser checks

Performed in the desktop app's Chromium browser on October 20, 2026 against the local release candidate. Desktop viewport was 1205×884; responsive checks used 390×844, 768×1024 and 320×740. These are browser viewport checks, not physical-device or Safari/Firefox certification.

| Path | Observed outcome |
| --- | --- |
| Anderson-May deep link and Run | Correct model title, 4 stocks / 4 flows / 11 variables, RK4 / DT 1 / horizon 0–365, running then 366 completed samples |
| Ctrl K, search, Down, Enter | Command dialog opens, filters and invokes the existing action; property field receives focus |
| Exact element name | Searching Beta prioritizes Beta over equations mentioning Beta; mobile Properties opens and receives focus |
| Desktop series controls | Stocks selects four series; filtering `vacc` shows five matching controls while retaining four plotted trajectories |
| Mobile series controls | Stocks / All / Clear, search and selected chip states work; Clear shows “No variables selected”; filtering leaves numerical results and selection unchanged |
| Mobile results | Fullscreen chart and Stats remain usable; time averages, recorded-sample statistics and caveats appear |
| Small numerical labels | Vaccination Rate 0.01 displays as 0.01, rather than the former misleading 0.0 |
| Failure after draft edit | Changing Beta to 1/0 clears prior results and produces a division-by-zero message and “Run failed · inspect inputs”; no library save was performed |
| Tablet input inspection | Source caveats, settings and equations visible; filtering `vaccine` reports 3 of 19 inputs |
| Numerical investigation | Pending feedback followed by full runs at DT 1, 0.5 and 0.25: 366, 731 and 1,461 samples; bounded comparison reports small differences |
| 320-pixel inspection | Title wraps, Close remains accessible and content scrolls within the dialog |
| Library via command palette | Existing search/category/sort/import paths retained; `herd immunity` returns 5 of 1,078 with numerical-completion labels |

Browser findings repaired during this pass: the existing flex display overrode hidden series rows; the mobile context strip overlapped floating controls; exact-name search ranked an equation hit first; small positive/negative numeric values rounded to zero. Asset versions were advanced so existing browsers receive the changed scripts and styles.

## Automated evidence and limits

`check_frontend.cjs`, `check_simulation_state.cjs`, `check_workbench_v15.cjs` and `check_series_controls.cjs` pass. They cover parsing, frontend numerical operations, stale asynchronous results, command delegation, state precedence, ranked search, selection/color/result preservation and nonzero numerical formatting. Browser tests above complement these focused checks.

Physical iOS/Android, Safari, Firefox, screen-reader operation, slow/offline networks and high zoom remain unverified. No claim of universal platform or accessibility certification is made. Existing paths outside the listed interactions were preserved by source review and regression coverage; they were not all manually re-exercised in this release.

The released HTTPS workbench was subsequently checked with the same Anderson-May deep link and a full numerical run. Versioned assets exposed the command finder and new context/series controls; final desktop proof was retained with the private QA artifacts.
