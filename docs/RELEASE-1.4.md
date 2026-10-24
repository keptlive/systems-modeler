# Version1.4 — source reconciliation and numerical evidence

This pass reviews the143 failing public definitions and the source identities behind selected additional models. The clean audit of1,078 tracked definitions is **941 completed defaults and137 explicit failures**, six additional completions and no newly failing defaults. A completed trajectory is not scientific validation. The legacy all-model test continues to fail on unresolved definitions; those failures have not been excluded from the audit.

## Model changes

Exactly63 public definitions changed, each with original/replacement SHA256 and a field-level receipt:

- Three original implementations restored: School Closure, Solow and Atmospheric Bathtub. Missing first definitions and misclassified stock-changing auxiliaries had removed actual dynamics. School Closure now completes; the latter two were previously finite but materially incomplete. Full Beer remains unresolved because the author's own source has conflicting placeholder equations. See [source restorations](SOURCE-REPAIRS-1.4.md).
- Four educational reconstructions: Kermack–McKendrick, Anderson–May, SEIR and Solow–Swan. Existing declared parameters replace broken references/initialization. Independent whole-trajectory ODE or analytic checks cover the stated assumptions. The three epidemic examples explicitly use RK4 at their existing grids; the vaccination example's former Euler error reached15.6% of initial population. See [mathematical evidence](MATH-SOURCE-REPAIRS-1.4.md).
- Twenty-nine epidemic definitions receive corrected citations or withdrawn unsupported claims. These are conceptual references unless exact fidelity is demonstrated. See [epidemic reconciliation](EPIDEMIC-SOURCE-RECONCILIATION-1.4.md).
- Eighteen physical, traffic, ecological and economic definitions receive citation corrections and specific limitations. Stiff BZ dynamics, missing Oregonator derivatives and other structural problems remain visible. See [physical reconciliation](PHYSICAL-SOURCE-RECONCILIATION-1.4.md).
- Nine healthcare definitions reviewed; the pharmacokinetic example gains exact stock references, systemic/non-systemic oral mass accounting, a disposition eigenvalue half-life and units. Its constants remain illustrative. Eight other healthcare models remain mathematically unresolved. See [healthcare reconciliation](HEALTHCARE-SOURCE-RECONCILIATION-1.4.md).

The default-run improvements are School Closure, Kermack–McKendrick, Anderson–May, SEIR, Solow–Swan and two-compartment pharmacokinetics. Correction of bibliography alone does not count as a numerical repair.

## Engine and reporting

The evaluator supports the exact spaced Vensim `IF THEN ELSE` spelling, XMILE brace comments and left-associated comparisons with the standard's precedence. Extra function arguments and malformed lookup pairs fail explicitly. [Engine evidence](ENGINE-SOURCES-1.4.md) records source standards, tests and remaining dialect gaps.

Input inspection and MCP validation surface24 reviewed erroneous citation pairs. Matching is exact source/reference, so coverage is bounded; an absent warning does not certify a citation. The full model description is included in the downloadable/MCP report and visible beside source/run settings. Original misleading claims are corrected or explicitly bounded in reconciled definitions. Existing editor, optional AI, import/export, analytics, library and agent-page functions are retained.

The historical DOI audit covers all143 previous public failures and distinguishes the historical numerical hash/error from the source snapshot. The latest triage keeps all143 candidates, including six now completing, with unresolved-symbol, domain, case-collision, workload and dialect findings. Categories overlap and are diagnostic leads, not scientific verdicts.

## Verification and limits

**332 regression tests passed**, plus18 parameterized preservation subtests, frontend parsing/numerical checks and real local HTTP/SSE/stdio MCP exercises. Independent review challenged endpoint-only checks, caught the Euler error, and required reproducible independent RHS fixtures and historical/current evidence separation. See [independent review](INDEPENDENT-TRUST-REVIEW-1.4.md).

Legacy API tests now use disposable storage and assert outcomes; frontend tests invoke a real JavaScript parser. The public audit uses an explicit tracked-only scope so local test/user additions cannot inflate public totals. The full audit and remaining failures are recorded separately from the passing regression suite.

Production-runtime staging passed67 source/numerical tests plus18 preservation subtests. Version1.4 is live: all8 runtime files and1,092 data files were verified, with exactly63 reviewed model edits and all other data unchanged. The complete live library has952 completed defaults and139 explicit failures, down from145 failures. Live HTTP/SSE MCP checks and the repaired vaccination model's browser run passed; source caveats and RK4 settings are visible. Physical devices, Safari/Firefox, empirical calibration and full scientific validation of the library remain unfinished work.

## Public evidence provenance

Some receipts retain the historical source baseline identifier `422af21` (or its full hash). It is an operator-side provenance label, not a revision available in this public repository. Public tests do not resolve that Git object: original/replacement byte hashes, field-level before/after evidence and portable canonical-content hashes provide the recorded comparisons. The private local MCP transport receipt is excluded; the public check script supports reproducible local checks with an explicitly supplied endpoint or stdio.
