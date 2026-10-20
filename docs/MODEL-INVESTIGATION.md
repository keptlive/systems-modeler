# Model input investigation — October 20, 2026

The complete 1,078-file GitHub library was run at its original default settings against the repaired engine. 929 runs completed and 149 failed explicitly. Completion establishes neither scientific validity nor reasonable assumptions. No library definitions were edited or deleted during this repair.

The 13 additional production definitions were also checked privately after release: 11 complete and two fail. Across all 1,091 production files, that is 940 completed defaults and 151 explicit failures. No user model definitions were copied into source control. Public SHA-bound badges currently cover the 1,078 checked-in definitions; the 13 additional files retain their separate private audit receipt.

`operations/library-full.json` records each file's SHA256, result, error and the exact core source hashes. `operations/library-investigation.json` investigates the union of initial and final failures (160 models): 11 initially failing models now complete. Diagnostic groups overlap: 65 numerical/domain/cycle failures, 65 unresolved-symbol definitions, seven ambiguous names, seven malformed or unsupported expressions, six workload-limit cases and nine function-coverage cases.

Concrete input leads:

- Simple Global Carbon Cycle references `CO2_Fertilization` while defining `CO2 Fertilization Factor`. Confirm the original source before changing it.
- Beer Distribution Game references absent inventory-adjustment parameters.
- `Population65+` and `Population_65plus` require source reconciliation; they are not silently treated as identical.
- The SIR example starts Susceptible at zero with Infectious five and a Total Population parameter of 1,000. A finite run cannot establish that this scenario is intended. Do not invent an initial population from the title.
- Greenshields traffic is unstable at its coarse default timestep and improves under smaller Euler steps or RK4. Forest-fire and DICE examples still have domain failures at finer steps. World2 may yield a finite negative population. These require scientific review, not success badges alone.

The editor's **Check inputs** displays initial stock values, equations, flow endpoints, settings, units and retained source/reference metadata. It reports structural and short numerical checks separately from scientific validation. The two libraries show **Default run completed**, **Needs investigation**, or **Not yet checked**, bound to the exact model bytes checked.

Next repairs should be source-by-source: verify original equations and units, recover missing definitions, establish conservation/domain expectations, test timestep convergence, document each changed assumption, then rerun the full default and regression audits. Unsupported RANDOM variants need reproducible per-run streams before implementation. Arrays, conveyors, queues, explicit nonnegative constraints and other unsupported XMILE semantics are rejected rather than silently discarded.
