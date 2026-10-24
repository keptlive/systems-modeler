# Engine failure reproduction — hardening review 1.9

The shared simulation entrypoint now attaches a `reproduction` object to numerical failures while preserving the original error code, message, root causes, blocked dependencies, state and time. It contains:

- `normalized_model_sha256`: a digest of the supplied model excluding creation/update timestamps;
- `engine_sha256`: content hashes of the numerical engine files;
- `settings`: the effective request settings, with the actual stochastic seed when the engine captured it.

The explicit Euler and RK4 entrypoints use the same boundary. REST, investigation and MCP diagnostics can transport this evidence without embedding the full private model, configuration or filesystem paths. A failure in metadata collection does not replace the actual numerical error: reproduction metadata is marked unavailable.

Seven independent tests check a failure occurring after initialization, its root/blocked chain, exact hashes and solver overrides, timestamp-independent identity, explicit solver entrypoints, report errors and preservation of the original failure when metadata is unavailable. Escaped lone-surrogate report labels are rejected before execution; valid emoji and multilingual labels remain intact. They pass in `tests/test_engine_hardening_v19_root.py`.

This context makes an observed failure reproducible with the same model and engine. It does not establish whether the input equations are scientifically valid. Numerical repairs require separate independent mathematical evidence.

The desktop and mobile failure panel also offers **Download failure report**. The JSON contains the exact failed model snapshot, effective replay settings and causal diagnostics. Later edits do not replace those inputs, and starting a new run or clearing results removes the stale report. A browser-module regression verifies snapshot ownership, seed preservation, escaped labels and actual download payload. Existing inspection, charts, analytics and navigation remain available.

Failure panels use the existing button styling and remain available in analytics and fullscreen views. Fullscreen charts clear an obsolete plot when there is no current result. Changing a variable between numeric and report roles invalidates prior results; semantic edits also clear failed-run exports. The actual browser download was checked against the failed model, effective settings and engine fingerprints.
