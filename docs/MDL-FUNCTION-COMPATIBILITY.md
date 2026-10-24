# Scalar MDL function compatibility

The native MDL importer now maps ten additional source spellings into existing scalar evaluator functions. Original MDL text and record diagnostics remain retained. Added spellings require exact source arity before validation; bounded translation work also charges argument inspection. There is no general spelling-based import of every evaluator function.

| Vensim source | Imported function | Contract |
| --- | --- | --- |
| LOG(x,base) | log(x,base) | Two arguments; explicit logarithm base |
| MODULO(a,b) | MODULO(a,b) | C remainder via math.fmod; result follows dividend sign |
| INTEGER(x) | TRUNC(x) | Integer part toward zero, including negative inputs |
| POWER(base,exponent) | pow(base,exponent) | Two arguments; same power law as source ^ |
| SMOOTH(input,time) | SMOOTH(input,time) | First-order information smooth; initial input |
| SMOOTHI(input,time,initial) | SMOOTH(input,time,initial) | Explicit initial state |
| SMOOTH3(input,time) | SMOOTH3(input,time) | Three information stages, each time/3 |
| SMOOTH3I(input,time,initial) | SMOOTH3(input,time,initial) | Same initial value in all three stages |
| ZIDZ(a,b) | ZIDZ(a,b) | Zero when abs(b)<1e-6; otherwise a/b |
| XIDZ(a,b,fallback) | XIDZ(a,b,fallback) | Fallback when abs(b)<1e-6; otherwise a/b |

Primary contracts: [MODULO](https://vensim.com/documentation/fn_modulo.html), [INTEGER](https://vensim.com/documentation/fn_integer.html), [LOG](https://vensim.com/documentation/fn_log.html), [POWER](https://vensim.com/documentation/fn_power.html), [SMOOTH/SMOOTHI](https://vensim.com/documentation/fn_smooth.html), [SMOOTH3/SMOOTH3I](https://vensim.com/documentation/fn_smooth3.html), [ZIDZ](https://vensim.com/documentation/fn_zidz.html), [XIDZ](https://vensim.com/documentation/fn_xidz.html). Checked October24,2026. Numeric mappings preserve evaluator domain failures. Guarded division uses the separate Vensim threshold functions, retaining their eager argument evaluation; it is not rewritten into lazy IF or exact-zero SAFEDIV. Exact ±1e-6 denominators divide, and adjacent representable floats on both sides are tested.

Smooth tests compare the complete trajectory against independently authored explicit first-/third-order stock chains under Euler and RK4, plus closed-form ramp responses. Imported controls still select Euler. Hidden smooths retain the existing Radau rejection; importing a spelling does not expand solver support.

An isolated pinned pysimlin0.8.5 comparison used41samples, start0/stop2/dt.05, original MDL inputs and both Euler/RK4. LOG matched exactly. Four smooth forms driven by TIME (including explicit initial2) agreed within6.67e-16. STEP-driven smooths agreed under Euler within1.78e-15. Simlin RK4 samples the STEP event boundary differently: maximum discrepancies0.0833333(first order) and0.0676255(third order). Our STEP fixtures match independent explicit stock chains and Vensim's documented [held test inputs during RK stages](https://vensim.com/documentation/rungekutta.html); that discontinuity comparison is not claimed as cross-engine agreement. Simlin0.8.5 rejected POWER as unknown_builtin; POWER is checked against the primary contract and numerical identities instead. Simlin's MDL translation maps ZIDZ/XIDZ into exact-zero SAFEDIV, which disagrees at small nonzero denominators; documented Vensim threshold behavior is intentionally preserved here rather than copied from that translator.

Intentional rejects remain:

- [PULSE](https://vensim.com/documentation/22300.html) takes start/duration and height1; native PULSE takes impulse magnitude/start/repeat and returns magnitude/dt.
- [RAMP](https://vensim.com/documentation/fn_ramp.html) is not admitted until end-before-start and dynamic argument semantics match; a spelling-only mapping is insufficient.
- [SMOOTH N](https://vensim.com/documentation/fn_smooth_n.html) uses input/time/initial/order, discrete behavior and automatic order reduction; native order/initial and solver behavior differ.
- [Material DELAY](https://vensim.com/documentation/fn_delay1.html) conserves material with changing delay time; native material delays reject changing duration. No blanket DELAY alias is added.
- [RANDOM calls](https://vensim.com/documentation/fn_random.html) carry Vensim stream/seed and truncation contracts; distribution names alone do not prove equivalence.

This is bounded scalar compatibility, not universal Vensim support. Unsupported constructs still raise MDLImportError with source diagnostics; no stock law, table, geometry, source text or unsupported operator is silently rewritten. No saved models or production data are changed by this parser work.

[Simulation control parameters](https://vensim.com/documentation/ref_sim_control_params.html) INITIAL TIME and FINAL TIME references now resolve to dynamic STARTTIME/STOPTIME context values; numeric source controls still establish the original run bounds. Changing effective simulation bounds therefore changes these equation values. If an authored declaration owns the corresponding generated bound name, an actually used control reference is explicitly rejected rather than silently bound to that declaration. The declared source name remains supported when no such control reference is present. This bounded rejection is necessary until the native vocabulary can express both identities independently.

INTEGER uses TRUNC, with negative-input regression tests: the installed pysimlin0.8.5 MDL translator's floor mapping is intentionally not copied, because Vensim explicitly specifies truncation toward zero.

MODULO now uses a distinct native math.fmod primitive matching Vensim's documented C remainder, never Python mod. Tests cover integer/fractional dividends with both dividend and divisor signs, exact multiples, zero dividend and explicit zero-divisor failure.
