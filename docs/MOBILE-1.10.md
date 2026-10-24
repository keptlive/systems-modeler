# Mobile workspace verification — 1.10

## Design brief and baseline
People exploring or editing a model on a phone need to find a model, inspect inputs, run it and read results without fighting floating controls. The established dark instrument interface, diagram editor and modeling features remain. This pass gives navigation a compact header, groups all existing document actions in a labeled native menu, reserves a separate run/action row, and makes result sheets readable at narrow widths.

Baseline inspected on the live 1.9 editor at 390 × 844: the header scrolled horizontally, settings/add/run and zoom competed for canvas space, mobile chat lost drafts on closing and did not immediately show messages. Mobile results omitted desktop run comparison, animation and export controls. Touch tooltip coordinates were invalid because Touch has no offsetX/offsetY.

## Preserved paths and improvements
- New, Save, Import, Export, Library, My Models, Help, command search and Connect agent retain their original controls/listeners. Mobile navigation moves those controls into a native dialog; desktop restores them in place.
- Stock, flow, variable, link, delete, inspection, settings, pan/zoom and Run remain available. The fixed action row and bottom tabs no longer overlap.
- Results retain Chart, Stats and AI; series filtering, all/stocks/clear, chart modes, normalization and logarithmic scale. Added phone access to saved runs, comparison, animation, chart exports and explicit phase axes.
- Chat preserves drafts and updates both visible and desktop histories immediately. Personal OpenRouter settings are available from the menu and assistant. See [OpenRouter setup](OPENROUTER.md).
- Library focus is contained and restored; a late load cannot focus a closed library. Result sheets support keyboard focus containment/restoration. Charts follow panel size changes and touch tooltips use the correct chart owner.

## Verification record
October 21, 2026. Chromium in-app browser, local build on port 13253. Inspected 320 × 740, 390 × 844, 768 × 1024 and 740 × 390: navigation, full-horizon grid-frequency simulation (1,501 samples), results/analytics, settings, library search, AI settings, key rejection/clearing and chat draft preservation. Desktop transition to 1280 × 800 restored all original controls and preserved the current model and chart. Saved-run comparison, play/pause, explicit phase axes and a 1,501-row CSV download were exercised. Nineteen Node behavioral suites pass. Final production checks are recorded in the release receipt. Visual viewport overrides are responsive layout checks, not physical device testing. iOS Safari, Android Chrome, Firefox, actual virtual keyboards and screen-reader speech remain unverified.

Full Python regression: 1,281 passed, three existing XMILE expected failures and 18 preservation subtests. Fresh complete public corpus audit: 1,050 pass / 28 unchanged failures; no equations or engine changes in this release. Numerical completion does not establish scientific validity. Real MCP HTTP/SSE/stdio checks passed locally. Browser provider rejection was exercised with a synthetic invalid key; the existing configured credential independently returned HTTP 401 from OpenRouter Free. Successful real provider generation remains blocked on a valid credential; mocked generation/modification/analysis/refinement and failure paths are covered.
