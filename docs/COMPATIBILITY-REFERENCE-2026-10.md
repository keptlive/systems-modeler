# Function compatibility reference, October 24, 2026

This is a bounded semantic investigation, not a parity or performance claim. The executable reference is installed `pysimlin` 0.8.5; its native-library hash is in [the observations](compatibility-simlin-reference-20261024.json). The separately inspected source commit is `3f87e9024a580b86b65e3d0c5c3353660fc5426e`. The wheel is **not** asserted to have been built from that commit. The original generated scalar inputs and expressions are reproducible through [the probe script](../scripts/compatibility_simlin_reference.py); input hashes, complete five-sample outputs, and bounded failures are retained in the receipt.

The wheel accepts STARTTIME/STOPTIME as bare values and zero-argument calls, returning the actual 5/6 interval bounds. ARCSIN/ARCCOS/ARCTAN work, but ASIN/ACOS/ATAN fail in this wheel. Out-of-domain ARCSIN returns NaN; this product intentionally rejects nonfinite numerical output.

Do not substitute a reference tool's behavior for the source dialect's contract:

| Case | Observed wheel | Inspected source / primary dialect contract |
| --- | --- | --- |
| MDL INTEGER(-3.2) | -4 | Pinned translation uses TRUNC; Vensim requires -3 |
| QUANTUM(-9.9,-3) | -9 | Pinned implementation and Vensim return unchanged -9.9 when step is nonpositive |
| MDL XIDZ(1,1e-9,9) | division, about 1e9 | Vensim selects fallback9 for abs(denominator)<1e-6 |
| XMILE SAFEDIV(1,1e-9,9) | division, about 1e9 | Pinned implementation tests exact zero |
| MDL LOG(100), LOG(8,2) | 2, 3 | Base10 single argument; explicit base for two arguments |

Primary Vensim references: [INTEGER](https://www.vensim.com/documentation/fn_integer.html), [QUANTUM](https://www.vensim.com/documentation/fn_quantum.html), [ZIDZ](https://www.vensim.com/documentation/fn_zidz.html), [XIDZ](https://www.vensim.com/documentation/fn_xidz.html). The threshold is strict: exactly ±1e-6 divides. Negative and zero boundaries are in the receipt. Pinned implementation evidence is `src/simlin-engine/src/{builtins.rs,vm.rs,mdl/xmile_compat.rs}`, each hash-bound by the receipt. Source semantics and wheel observations differ, so unsupported raw names and those divergences are recorded rather than hidden.

Wheel SAFEDIV(1,2,1/0), SAFEDIV(SQRT(-1),0,9), and MDL XIDZ(1,2,1/0) yield finite selected results. This alone establishes neither eager nor lazy evaluation: IEEE arithmetic can evaluate an unused argument to Inf/NaN without throwing. This product's ordinary pure arguments remain eager and its nonfinite/domain checks are stricter; no lazy compatibility claim is made.

Graphical-function witnesses use identical xscale0..1/ypts10,20 geometry. Direct Curve(0.5), TRUNC(0.5), and SAFEDIV(0.5) all fail in the wheel, including the ordinary-name control. LOOKUP(Curve,0.5), LOOKUP(TRUNC,0.5), and LOOKUP(SAFEDIV,0.5) all return15. SAFEDIV(4,2) returns builtin2 even with that named table present. Therefore named table calls must be distinguished before builtin lowering; explicit LOOKUP is the tested interoperable spelling. These cases do not prove general graphical-function interoperability.

Run using an isolated environment containing pysimlin:

```sh
python scripts/compatibility_simlin_reference.py --source /path/to/pinned/simlin --output /tmp/compatibility-reference.json
```

The script does not import this product's evaluator, mutate engine code, or install dependencies. Rejected exploratory probes are observations, not harness failures. No existing models or public/remote files were changed by this investigation.

## Implemented scope and independent comparison

This implementation adds STARTTIME/STOPTIME values and zero-argument calls with
per-run bounds; ARCSIN/ARCCOS/ARCTAN; floor-based INT, toward-zero TRUNC and
QUANTUM; exact-zero SAFEDIV; and distinct Vensim ZIDZ/XIDZ/MODULO semantics.
Existing declared scalar names and graphical-function ownership take precedence
where they did before. The finite/domain checks remain strict. Adaptive Radau
rejects newly introduced uncertified discrete operations and time/state-dependent
safe-division denominators; a constant-denominator smooth quotient remains usable.

Independent comparison against the recorded full series classified 73 direct
probes: 29 agreements, 10 documented dialect differences, 22 cases where the
reference rejected or returned nonfinite values, and 12 local domain rejections
or unsupported cases. These categories are not a compatibility percentage.
Thirteen generated exports roundtripped exactly locally; nine matched the wheel.
The wheel rejected TRUNC and three standalone graphical-function exports.
Explicit LOOKUP is supported by the wheel's aux-with-gf fixture, but that does
not establish support for our standalone-gf export topology. No silent conversion
to additional model variables is performed.

The remaining direct-probe gaps include raw XMILE INTEGER/REM, bare
initial_time/final_time, MDL QUANTUM and one-argument MDL LOG. The MDL importer
does handle INITIAL TIME and FINAL TIME control references explicitly.
Negative MODULO is intentionally C/Vensim remainder rather than the wheel's
observed floor-modulus result. See the [MDL contracts](MDL-FUNCTION-COMPATIBILITY.md)
for admitted spellings, independent stock-chain checks and remaining rejects.
