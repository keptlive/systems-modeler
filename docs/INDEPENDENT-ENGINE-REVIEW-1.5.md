# Independent advanced-engine review 1.5

Reviewed the frozen advanced scalar-function diff, 209-case matrix and ADVANCED-FUNCTION-REVIEW-1.5.md on 2026-10-20. No engine/UI edits made by this reviewer. Independent focused run: **209 passed in 2.23s**. Passing this matrix does not cover all finite floating-point inputs or establish scientific validity.

## Concrete findings

**P2: remote pulse interval changes the first pulse.** `pulse_function(7, .2, 1e20, 1, 1)` returns 0, whereas the first event occupies [.2,1.2) and should return 7 at accepted time 1; the same call with repeat interval 0 correctly returns 7. The tolerance includes ulp(repeat_interval), so an unrelated huge repetition interval dominates and forces the DT/4 cap. This falsely classifies phase .8 as the exclusive end of a unit pulse. Avoid applying repetition-interval uncertainty before a modulo cycle has occurred; derive tolerances from the actual relevant subtraction/modulo operations. Add a regression comparing first-event output/area for zero, ordinary and huge repetition intervals at an off-grid start.

**Representable extrapolation still fails through an overflowing intermediate.** `lookup_interp(5, [(0,-1e308),(1,-5e307)])` raises a nonfinite-result error although the linear result is 1.5e308. `weight*difference` overflows before the negative y1 cancels part of it. This defect predates the patch, but the new documentation's suggestion that failures are truly nonrepresentable is too broad. Use stable sign-aware/scaled extrapolation or disclose the remaining limitation and narrow the claim. Include this case and the mirrored sign case in the independent extreme-value matrix.

## Reviewed strengths and compatibility

The accepted-state snapshot correctly holds complete STEP/PULSE/RAMP arguments for RK4 while ordinary TIME and hidden-state derivative stages remain stage-valued. Reviewed nested-state identity tests provide meaningful coverage. The [official Vensim integration documentation](https://www.vensim.com/documentation/rungekutta.html) directly supports the held-test-input convention; the documentation appropriately identifies this as an adopted method contract rather than claiming XMILE mandates it or conflating Vensim and XMILE PULSE signatures.

Independent complete-trajectory Erlang, logistic, invariant and exact integral references are materially stronger than merely requiring finite corpus runs. Random-family tests compare separate Python Random instances, accumulation and convolution for the stated runtime behavior, without claiming cross-vendor random-bit compatibility. Registry equality establishes an explicit review row for each advertised function name; it cannot establish exhaustive combination, parameter-domain or floating-point coverage. Unsupported dialects remain explicit failures. No additional concrete snapshot/integration regression was reproduced in this bounded review.

Disposition: address the pulse counterexample before releasing that numerical change. Resolve or explicitly disclose the extrapolation limitation. Existing 209 passing tests do not close either independently reproduced case.

## Verified corrections and final disposition

Reviewed final equations SHA256 `c6e396749ff0b149624673fcee5e08863fe20ac5b9564e98875abd8114e6e925`. Both findings above are closed in this bounded review. The pulse tolerance now excludes the unrelated repetition interval ULP. Independently probed first event returns 7 for intervals 0, 100, 1e20 and 1e300. Repeated off-grid start .2 and interval 10 activates accepted samples 1,11,21, with no early 10/20 activation or trailing 2/12/22 activation. Decimal DT=.01/repeat=.1 activates exactly grid indices 0,10,20,30 in the checked interval.

Nonfinite interpolation/extrapolation intermediates now use an exact affine Fraction calculation over the input floats, followed by checked float conversion. This recovers the reported +1.5e308, mirrored -1.5e308 and a subnormal-X-spacing identity example that should return 1. The fallback operates on bounded-size representations of finite binary floats and does not weaken rejection of truly nonrepresentable results. Ordinary finite fast-path arithmetic remains unchanged.

Independent final focused rerun: **218 passed in 3.38s**. No additional concrete snapshot/integration regression found. Scoped acceptance covers the documented scalar contract and tested cases; full language conformance, arbitrary floating-point accuracy, physical calibration and all-program correctness remain outside this evidence.
