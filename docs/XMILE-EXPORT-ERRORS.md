# Actionable XMILE export errors

2026-10-24. Small additive UI change, separate from sensitivity and May model proposals.

Before modification, the existing export dialog exposed Download XMILE, Download JSON and Cancel. XMILE posted the current unsaved model to its export endpoint; JSON serialized the current model locally. Successful exports downloaded a file and closed the dialog. An XMILE API rejection discarded its explanation and always said to check inputs. In particular, the generator's discrete-period rejection and instruction to use JSON never reached the user. Independent review then found the actual HTTP wrapper also propagated that expected ValueError as500; the initial mocked UI test did not detect this integration defect.

The shared GET/POST xmile_response wrapper now catches only generator ValueError and converts it to HTTP422 with a bounded string detail. It retains at most1024input characters before normalization, removes control characters/collapses whitespace, and returns at most500detail characters or an actionable JSON fallback. It does not catch RuntimeError, TypeError or broad Exception; unexpected failures remain500. Existing Model admission422arrays and missing-model404responses retain their behavior.

The same dialog, three controls, request payload, successful XMILE behavior and local JSON path remain. On an XMILE HTTP failure the UI now extracts only a string detail or typed failure.message from JSON/problem+json, or literal text/plain. It displays the explanation through the existing native alert, followed by an instruction to choose the existing Download JSON button to preserve settings. No response text enters innerHTML, no source/model content is evaluated, and neither export format is hidden or silently substituted. Failed export leaves the dialog open and restores the button, so JSON remains available. No model/draft/save state is mutated.

Error detail is untrusted. The helper retains at most8192bytes, reads at most32chunks (including empty chunks), limits body-detail reading to2seconds, removes control characters/collapses whitespace and displays at most500message characters plus fixed guidance. HTML/unknown-content-type pages, malformed/unusable JSON, missing/locked/failed/stalled streams and empty details receive a generic actionable fallback. Reader cancellation/release is attempted without allowing a stuck cancellation promise to block the UI. This bounds error-detail processing; it does not add a general timeout to the preexisting network fetch or alter backend export admission.

`tests/test_xmile_download_errors_ui.py` runs the actual JavaScript module in a dependency-free Node DOM harness. It verifies actionable discrete-period detail, typed failures, inert markup/control-text display, malformed/HTML/oversized/empty-chunk/locked/failed/stalled body defenses, byte/chunk/deadline caps, both format controls, failed-export recovery, unchanged current model/JSON content and successful XMILE/Cancel behavior. The combined targeted run with all May research tests passed **22tests in0.98s**. This does not certify browser appearance or assistive-technology behavior; independent review remains separate.

May proposals are still isolated in operations/discrete-map-research and are not adopted by this UI change. JSON already preserves their discrete-period declaration; this change merely surfaces the backend's existing explicit refusal of lossy XMILE export. It does not claim new XMILE support.

Real GET/POST route tests reproduce the discrete-model rejection against TestClient with server exceptions disabled; both now return422with the exact JSON guidance, without storage writes or model changes. They also verify successful XML,404, bounded untrusted details, empty-detail fallback, unmodified Pydantic admission errors, and unexpected RuntimeError/TypeError500responses. Final focused export/roundtrip/discrete regression run: **48passed in1.48s**, with one preexisting Pydantic settings warning. Independent review must assess this actual transport correction as well as the UI.

| File | SHA-256 at freeze |
|---|---|
| app/api/models.py | `d71c6c79c4fa0793c5150e928e05621eefd71f8bc955e211088ca66283831b56` |
| static/js/xmile-download.js | `eac24403acc40d778f427e5e93302a1a34fb1e0fe73dd45884ac6e267cd94461` |
| tests/test_xmile_export_errors_http.py | `906fec4c9e211601b16ebefd0d62a3574cae015352b0a6dc933f7d45641dd4ec` |
| tests/test_xmile_download_errors_ui.py | `ee29dfd4ae29c4109ad8a68d990e933a97a5b872264242ff772bfd184a43e9a4` |

Public-package preparation normalized one stray EOF CRLF to LF in each export test file. This is format-only; test logic and runtime bytes did not change. The two test hashes above now bind the normalized files. The API hash records the original export freeze; the separately reviewed May-link/API addition is bound in QUALITY-FOLLOWUP-REVIEW.md. Focused tests were rerun after normalization.
