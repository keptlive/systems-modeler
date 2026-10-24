# Two distinct systems candidates, isolated pending independent review

No active model, public repository, runtime, catalog count or remote system was
changed. Baseline remains996 public definitions. These original illustrative
models are candidates, not adopted releases or empirically calibrated systems.
Do not admit models just to reach a count target.

## Shared-predator ecology

The Holt1977 model has two prey with separate logistic resource bases and a
shared food-limited predator, using the original paper's equations8-9 on printed
page204 ([author-hosted paper](https://people.clas.ufl.edu/rdholt/files/001.pdf),
[DOI](https://doi.org/10.1016/0040-5809(77)90042-9)). The source PDF was rendered
and visually checked. It has no direct interspecific resource competition.
It demonstrates why adding a second prey can depress the first through a shared
enemy. Defaults and density normalization are new choices, not a paper dataset.

Densities are dimensionless normalized quantities; time is days. Capacities
must be positive; rates, food values, conversion, maintenance and initial
densities nonnegative. No saturation/adaptive diet/spatial structure or
stochastic extinction is included. The continuous nonnegative orthant is
invariant because every density derivative has that density as a factor;
a coarse numerical step need not preserve this property. Conversion zero is
supported and freezes predator density. No state clipping is applied.

## Open-flow adsorption breakthrough

Three well-mixed liquid/solid cells in series add transport of an adsorption
front through separate finite-capacity sorbents. This differs from the current
closed competitive Langmuir model with two solutes and one shared surface.
The model uses the q*-based LDF variant documented by CADET v5.1.1, not native
kinetic Langmuir or the liquid-phase-driving-force variant. Mathematical
references are [LDF](https://cadet.github.io/v5.1.1/modelling/binding/index.html),
[Langmuir equilibrium](https://cadet.github.io/v5.1.1/modelling/binding/multi_component_langmuir_ldf.html)
and [CSTR balance](https://cadet.github.io/v5.1.1/modelling/unit_operations/cstr.html).
No CADET runtime/code/example is used. The three-cell lumped network is original;
it does not claim plug-flow/PDE or industrial-column fidelity.

Solute masses are milligrams, liquid volume liters, solid mass grams, time
seconds. Volume must be positive; flow, feed, solid mass, capacity, affinity and
kinetic coefficient nonnegative. Initially liquid masses are nonnegative and
sorbed masses lie in0..solid mass*capacity. Zero flow, binding, solid mass and
kinetic coefficient limits are supported. Negative reversible-uptake flow
means desorption into the liquid; it is not clipped or replaced with zero.
Liquid+solid+effluent mass equals initial total plus integrated feed. Uniform
cell parameters and constant feed are explicit simplifications. No explicit axial
dispersion term, thermal feedback, pore diffusion or multicomponent competition.

## Evidence and boundaries

Run from the repository root:
`PYTHONPATH=. .venv/bin/python -m pytest -q operations/library-candidates-fifth-systems/test_candidates.py`.
**23 passed in7.86s**: six Euler/RK4/Radau default runs and domain checks,
both symbolic unit checks, predator-free and constant-predator logistic curves,
empty-prey exponential decay, exact coexistence/single-prey equilibria,
species symmetry, weighted food conservation in the no-regeneration limit,
three-tank tracer step responses, zero-binding limits, closed nonlinear
adsorption implicit transient/equilibrium, desorption equilibrium, global mass
budget,120 actual one-step Euler random-state comparisons and complete graph
references. No scalar parser or work limits changed. An exploratory80s/.01
reference exceeded existing work limits; the long equilibrium check uses60s/.02.

RK4 defaults conserve the transfer budget to roundoff. Default Radau's adaptive
interpolation produced a maximum mass residual1.84e-8mg in this test, checked
against3e-8mg; its existing solver tolerances were not relaxed or hidden. These
bounds are numerical evidence, not positivity guarantees for arbitrary edits.

`DEDUPE-BASELINE.json` hashes all996 tracked definitions and admission/curation
indexes. The existing bounded expanded-RHS screen compared1,081 source records
(active plus prior candidate fixtures), expanded1,079 and found neither exact
nor constant-abstracted matches for either candidate. Two unsupported forms are
listed and manually assessed. This screen preserves stock order; it is not a
permutation/isomorphism or transcendental-equivalence proof. Closest existing
predator-prey, closed sorption and distillation equations were also inspected.

`NUMERICAL-EVIDENCE.json` binds model/default output/current engine hashes and
unit status. `SOURCE-EVIDENCE.json` records URLs, source hashes, exact source
scope and rights limits. All JSON, tests and defaults are newly authored;
no paper text, diagrams, datasets, upstream code or fixtures are redistributed.
Source access does not grant blanket rights to redistribute source documents.
Independent peer review and separately authorized admission/release checks are
still required. Editable parameter variables, stock endpoints and dependency
connectors remain explicit in both candidate JSON documents.
