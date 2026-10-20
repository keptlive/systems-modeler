# Analysis studio refinement — 1.7

## Design brief and observed baseline

Audience: people and their agents investigating time-series models. Primary task: read the result of a run, inspect one series, then compare variables without losing numeric meaning. Design thesis: lead with a readable result and measured trace; make comparative detail an explicit next step.

October 20, 2026 baseline: live Anderson–May model, desktop around 1205×884. Analytics put a nine-column table in a roughly300px sidebar with names and scientific notation breaking across lines. Every section was expanded. The chart's Value caption overlapped y ticks. Fullscreen copied HTML, losing analysis event handlers; its19-item legend exceeded the chart height. These were observed in rendered UI and then explained in source.

Preserved paths: chart/analytics/AI tabs; all statistics, rate, variance, behavior, peak and correlation sections; final values; chart types/scales/normalization/animation/comparison/save/export; model/property edits; assistant/agent connection; library; mobile panels. No model formulas are changed by this UI work.

## Final rules

- A compact run strip precedes a single-series explorer. The selected series has an actual recorded trace, final result, eight named metrics and a methods disclosure. No synthetic downsampling or invented values.
- Compare-all tables remain available in named disclosures. A fixed minimum table width, sticky variable column and explicit horizontal-scroll hint preserve numeric tokens and long names. Nothing is deleted to make the screen look simpler.
- Tabular numerals, restrained pale-blue trace, distinct label/value hierarchy,16–24px group spacing. Zero renders as0; readable ordinary magnitudes use locale separators; extremes use scientific notation.
- Analysis sections default collapsed except the summary; expansion choices persist across renders. Expanded analysis has two columns on desktop and one on phones. Chart+Stats has a chart alongside a scrolling analysis column on desktop.
- Chart axis margins and compact SI ticks separate captions from numbers. Long legends scroll with complete, keyboard-operable labels. Focus returns to a toggled legend entry after rendering.
- Fullscreen uses bound module instances, not inert copied HTML. Close/Escape restore focus; Tab remains inside; reopening resets the selected fullscreen tab consistently. Scrolling cannot accidentally dismiss the workspace.
- Existing charts, properties, editor and assistant retain their structure. Final-value rows wrap their names without colliding with the number.

## Verification

Actual Chromium browser: Anderson–May full default366samples; desktop sidebar, expanded Analytics and Chart+Stats; selected Recovered changes result to83,581.94; Peak Analysis opens with recorded values;390×844 and320×740 phone layouts; longest series name; constant-series trace. Node checks exercise actual analytics formatting, escaped names, zero/single/extreme data, selector changes and 12,801/100,001sample support. Editor guards test original fine timestep,100,000interval ceiling,1m retained values and blank input.

These are viewport checks, not physical-device or Firefox/Safari certification. Corpus source findings and engine capacity changes are documented separately. Statistical descriptions do not establish calibration, causation or scientific validity.

Export acceptance: the browser decoded the actual generated PNG at602×1572 with19 selected-series labels below the plot. Export now offers a native preview dialog with Save PNG and Save SVG. Live interactive HTML legend controls are removed from the exported SVG clone; computed styles and complete measured-width wrapped labels are retained. Output saved as chart-export-v170.png in the operator evidence folder. Download-event capture in the in-app browser timed out; image generation/decoding and accessible save links were verified separately.

Production acceptance confirms the 366-sample Anderson–May run, fullscreen Recovered selection at83,581.94, and no captured browser errors. Both live site footers now contain only Stock & Flow navigation, following the explicit request to remove unrelated promotions.
