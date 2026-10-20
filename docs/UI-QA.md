# Interface preservation and QA

The baseline feature inventory is in OPERATIONS.md. The existing dark workbench, AI chat, editor tools, saved models, import/export, model library, chart types, analytics, scenarios and mobile panels remain available. Additive styling improves spacing, contrast, keyboard focus and touch targets. D3 is pinned and served locally.

Repaired defects: inactive Steps control; clipped imported diagrams; hidden-container chart dimensions; clipped axis labels; dense tick labels; unlabeled icon buttons and property fields; apostrophes in variable controls; mobile import/export hidden; closed mobile panel covering navigation; mobile variable controls limited to stocks. Raw values are shown by default and normalization is labeled. Derivatives no longer include a fictitious initial zero, constant series are labeled constant, and raw variance comparison is no longer presented as causal sensitivity. Tail stability is presented as a heuristic, not proof of equilibrium.

Browser acceptance uses the available Chromium in-app browser at desktop, tablet and phone viewport sizes. Responsive emulation does not establish behavior on physical iOS/Android devices or Safari/Firefox engines. Record exact verified journeys and remaining platform gaps in the release receipt. Physical-device and alternate-engine acceptance remain required before claiming all-platform coverage.

Automated checks: `node scripts/check_frontend.cjs` parses all source scripts and checks linear/partial-interval derivatives and constant-series classification. API/engine tests and real MCP client checks are documented in TESTING.md.

Final browser acceptance also covered a manually drawn unsaved model (initial stock100 retained as100), explicit equations/units editing, and a successful run followed by an invalid initial equation. The failure state removes old chart values and presents the actual unresolved-symbol diagnostic on mobile. The agent/page loop was tested locally and over public HTTPS, including actual view acknowledgement, preserved source/units and an explicit concurrent-draft choice.
