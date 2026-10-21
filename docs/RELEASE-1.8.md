# Stock & Flow 1.8

## Outcome and limits

The full public audit covers1,078 definitions:1,031 complete and47 fail explicitly. All86 previous failures have a causal diagnosis and source review.39 now complete; no previously completing model now fails.43 definitions changed, including two formerly inert models whose actual dynamics are now restored. Partial repairs and unsupported physical interpretations remain explicit. No model is declared scientifically valid merely because a trajectory is finite.

The [failure register](FAILURE-REGISTER-1.8.md) links every remaining case to a specific cause and evidence requirement. Source partitions [B](CORPUS-REPAIRS-1.8-B.md) and [C](CORPUS-REPAIRS-1.8-C.md) contain portable before/after hashes, full-horizon probes and independent checks. [Morris–Lecar/Oregonator](INERT-MODEL-REPAIRS-1.8.md) have literal-equation reference solutions, positivity/convergence evidence and disclosed adaptation boundaries. Oregonator's default demonstration ends at30 scaled time units rather than300 so actual dynamics fit the work budget; its longer independent reference is recorded separately.

## Engine and interface

Radau is an explicit choice for stiff continuous differential equations. Its tolerances, exact retained output grid and charged work are exposed. Random, stateful history and time-driven discontinuous/lookup forcing are rejected. Independent review reproduced six silent pulse misses and the new rejection guard covers named, LOOKUP and inline WITH_LOOKUP tables and transitive TIME aliases. Stock-driven table feedback remains supported. Output-grid comparisons are not labeled adaptive-solver convergence.

RANDOM_BINOMIAL provides exact finite Bernoulli sums with seeded replay, callsite/time caching and trial-work accounting. The restored Wright–Fisher example stays on its allele-count lattice and retains absorbing boundaries.

Errors show the original failing equation separately from dependent values. API errors retain their original detail string and add structured evidence. Settings expose relative/absolute tolerance and keep actions visible while the body scrolls on small screens. Existing product functions and footer cleanup are preserved.

## Verification

The full audit is bound to engine and model hashes. Canonical and clean public checkout regressions each pass868 tests plus18 preservation subtests. All11 Node suites pass. Real local HTTP/SSE/stdio and live HTTPS HTTP/SSE checks pass with17 tools, including Radau tolerance transport and binomial replay. The production-dependency run passes865 tests; three audit-harness fixture failures were corrected and the complete13-test audit contract then passed, covering all868 tests. No runtime change was needed for those fixture corrections. Existing strict-XMILE identifier expected failures remain documented; Radau XMILE export fails explicitly with a JSON preservation instruction.

Local Chromium completed the repaired Oregonator with3,001samples and rendered the new phone-width settings and structured labor-model errors. Later direct browser input automation timed out; that interruption is not a passing interaction check. MCP then drove the oscillator on both local and live pages, each acknowledging revision3, analytics view and3,001 samples without a browser error. The live screenshot records the result. Physical devices, Firefox and Safari remain unverified. No empirical validation is asserted.

The deployed release matches all17 runtime paths. Exactly43 reviewed definitions changed; every other model and the database remained byte-for-byte unchanged across1,092 datafiles. Both hosted services are active. Production-only examples are audited separately:11 complete and2 remain undefined because required initial data/reporting conventions are missing. They were not overwritten.
