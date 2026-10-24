# Open model provenance and catalog candidate review

Reviewed 2026-10-24 against Simlin commit `3f87e9024a580b86b65e3d0c5c3353660fc5426e`.

## Decision: zero new catalog entries

The [SDXorg sample collection](https://github.com/bpowers/simlin/tree/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples) supplies useful executable regression assets, but the faithfully supported native scalar examples overlap existing catalog models. Renamed duplicates would inflate the catalog without improving coverage. No existing catalog definitions were changed and no new models or duplicate fixture copies were added.

| Candidate | Provenance and decision |
| --- | --- |
| Teacup | SDXorg MIT collection; XMILE and Vensim DSS 6.3 output by James Houghton, August 27, 2015. Existing `models/classic/teacup-cooling-cla.json` has the same initial temperature 180, room temperature 70, characteristic time 10, horizon 0-30 and timestep 0.125. Retain upstream as a regression fixture. |
| SIR | SDXorg MIT collection; XMILE by Bobby Powers, August 28, 2015; Vensim output by James Houghton, August 27, 2015. Existing catalog already has SIR coverage. Upstream starts susceptible 1000 plus infectious 5 while denominator is 1000; preserve that benchmark assumption rather than claiming calibrated forecasting. |
| Hares and lynxes | Includes reference CSV but requires nested modules, which the importer explicitly rejects. |
| Simple harmonic oscillator, Roessler chaos, Lotka-Volterra, pendulum, Workforce | Sample definitions are MDL; importer has no MDL reader. Existing catalog also covers these subjects. Translation would require separate equation review and numerical validation. |
| Display samples | STMX display/connection feature tests rather than distinctive scientific models. |
| Other third-party Simlin collections | Cannot inherit SDXorg or engine licensing by assumption. Arrays, conveyors, queues and modules also require semantic support before catalog admission. No blanket mass ingestion. |

## Retained regression assets

Unmodified inputs, independent Vensim reference CSVs, license and authorship README are already retained under `tests/fixtures/sdxorg/`, from the pinned subtree above. These are interoperability fixtures, not public catalog additions.

| Asset | SHA-256 |
| --- | --- |
| LICENSE | ac2cacd8360f8d24555d5feb327f46474f0c6e4635498c6ed498dae06fc1a913 |
| teacup/teacup.xmile | fe46dbda3c71bf99db52e6547c51c36a9b6920be35463904090ce1769da99eff |
| teacup/output.csv | c1ee580f660ab45fc740fe0a44944f2ba780edebea4058801b44fb884e7bff6e |
| SIR/SIR.xmile | a263e672f8391e11aef6a3d668d8bfe1ab383b27cad31cedcaed78735e28a92e |
| SIR/output.csv | 5d2b6277cb112b1b6a264b428e3734a1749036e157861f77008c7aa285ec0ccf |

Validation rerun: `.venv/bin/python -m pytest -q tests/test_xmile_sdxorg_samples.py` - **5 passed**. Tests execute full default horizons and compare every output to independently generated upstream Vensim data: Teacup 241 rows, SIR 3201 rows; rtol=6e-6 and atol=5e-6 accommodate historical reference precision. They retain rejection coverage for actual dimensions and nested models. This establishes numerical interoperability, not scientific validity of the whole catalog.

Future additions must be materially distinct and reproducible: explicit license, original source and hash, complete initial data and equations, supported semantics, full finite default run, and independent numerical reference or analytic invariant. A model-count target does not substitute for these requirements.
