# Simlin comparison and useful model assets

Reviewed October 24, 2026. Source pinned to [bpowers/simlin, commit 3f87e9024a580b86b65e3d0c5c3353660fc5426e](https://github.com/bpowers/simlin/tree/3f87e9024a580b86b65e3d0c5c3353660fc5426e). This is a source review plus executed interoperability tests in Systems Modeler, not a benchmark of Simlin execution or an audit of every upstream model. No Simlin dependency or engine replacement was installed.

## Recommendation

Use Simlin as an independent compatibility reference and a source of carefully attributed test fixtures. Its strongest additions would be dimensional analysis, richer import capabilities and feedback-loop analysis. Do not replace the current engine just to rescue scientifically incomplete definitions: numerical completion cannot supply missing initial conditions, equations or provenance. Preserve the current editor, APIs, diagnostics, solver choices and user data.

| Area | Verified comparison | Recommended use |
| --- | --- | --- |
| Units | Simlin has inference and expression-level checking in `units_infer.rs` and `units_check.rs`. Our model stores unit strings, but `validation.py` primarily warns when units are absent; it does not establish dimensional consistency. | Highest-value capability to add. Begin with explicit stock/flow time-unit consistency, addition and function-argument checks, and unknown-unit diagnostics. Infer cautiously; never invent units or convert an unknown into a pass. This directly targets dollars entering quality scores and dimensionless treatment flows. |
| Arrays and modules | Simlin represents dimensions, mapped subscripts and modules, with dedicated compiler and tests. Our scalar XMILE parser intentionally rejects these. | Useful future coverage, but not a small patch: requires data model, editor, import/export and evaluator changes. Keep explicit unsupported errors until end-to-end support exists. |
| Import and preservation | Simlin has native MDL and XMILE readers, import-loss warnings and semantic save checks. Our import is scalar XMILE. | Adopt explicit loss reporting and round-trip semantic tests first. Never silently flatten modules or drop simulation features. MDL conversion is a separate feature, not permission to replace original definitions. |
| Loop analysis | Simlin implements quantitative Loops That Matter, including dominance changes over time. Our current core investigation offers equation evidence, step refinement, name-based domain leads and topological conservation. | Add as an opt-in analysis aid later. A reinforcing feedback score can explain runaway behavior; it does not validate its equations. |
| Execution architecture | Simlin compiles to bytecode/VM and WebAssembly, with incremental compilation. Our engine is Python-based and bounded by explicit work budgets. | Potential performance gain, unmeasured here. Benchmark representative supported models before considering an adapter; retain current numerical semantics and reproducibility. |
| Integration | Simlin's implemented method enum is Euler, RK2 and RK4. Our settings expose Euler, RK4 and adaptive Radau, with feature restrictions and diagnostics. | Simlin is not an across-the-board solver upgrade. Keep Radau and current stiff-system regression coverage. Compare engines only with matched methods, timesteps, lookup behavior, delay semantics and initial conditions. |

Source entry points: [units checking](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/units_check.rs), [import losses](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/import_losses.rs), [engine architecture](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/CLAUDE.md), [Python binding capabilities](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/pysimlin/README.md), [integration method definitions](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/src/simlin-engine/src/datamodel.rs).

## Concrete improvement implemented

Both upstream scalar Teacup and SIR XMILE files contain an empty `<dimensions/>` container. Our parser rejected it as an array declaration. Removing only that metadata in a scratch probe allowed complete runs; actual nested modules remained unsupported. The parser now accepts empty containers while rejecting nonempty dimension declarations and multiple model elements. No equations or initial values were changed.

Unmodified, MIT-licensed inputs and their independently generated Vensim CSV references are retained in `tests/fixtures/sdxorg/`, with attribution and license. New tests compare every output column over the full horizon: SIR 3,201 rows and Teacup 241 rows. All columns match at rtol=6e-6 and atol=5e-6, allowing the historical reference exports' limited precision and small numerical differences. An existing test incorrectly used an empty container as its array example; it now contains an actual dimension declaration.

Validation: `pytest -q tests/test_xmile_sdxorg_samples.py tests/test_xmile_features.py tests/test_xmile_interoperability_v19_c.py tests/test_xmile_roundtrip.py` completed with **153 passed**, one existing Pydantic settings warning. Full application checks remain the integrating maintainer's responsibility.

## Sample models and licensing

The upstream engine is Apache-2.0; the embedded `test/test-models` collection is separately MIT-licensed, and `test/sdeverywhere` has its own MIT copyright notice. Preserve the applicable notices and individual provenance. Do not assume every third-party sample elsewhere in the repository has identical rights merely because it is in an Apache-licensed repository.

| Candidate | Assessment |
| --- | --- |
| SDXorg Teacup | Good beginner reference for exponential cooling and an import/solver regression. Provenance identifies James Houghton and Vensim DSS 6.3 reference output. Consider a catalog entry only if it improves the retained cooling examples rather than duplicating them. |
| SDXorg SIR | Good conservative three-compartment regression with complete reference data and authorship. Starts with susceptible=1000 plus infectious=5, so the sum is 1005 while its denominator parameter is 1000. Preserve and explain this benchmark assumption; it is not a calibrated epidemic forecast. Likely redundant with existing SIR catalog entries. |
| SDXorg hares and lynxes modules | Good future module interoperability fixture; correctly rejected today. Not eligible for the working-model catalog until module support is complete. |
| SDXorg simple harmonic oscillator, Roessler chaos and Lotka–Volterra | Potential reference/teaching material, but sampled files are MDL and require a reviewed translation or MDL support. Not imported or validated in this review. Avoid adding multiple variants merely to reach 1,000. |
| Simlin array/conveyor/queue fixtures | Valuable feature-conformance cases for future engineering, not ready-made scientifically validated public-library entries. Our parser deliberately rejects these semantics. |

The [SDXorg collection README](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/README.md) distinguishes small feature tests from complete integration/demo samples and describes canonical output provenance. [Collection license](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/LICENSE) and [engine license](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/LICENSE) should travel with any reused material.

## Next useful experiment

Create a small, pinned cross-engine conformance suite rather than importing a large sample dump. Include growth/decay, conservation, delayed adjustment, lookup boundaries, pulse timing, numerical stiffness and explicit unsupported arrays. Compare complete series and invariants against independent references, record model/source hashes and exact settings, and distinguish failed import, unsupported semantics, numerical disagreement and invalid scientific assumptions. A Simlin sidecar via its Python bindings is a plausible optional comparison backend, pending installation/version checks and performance measurement; it is not currently part of this application.
