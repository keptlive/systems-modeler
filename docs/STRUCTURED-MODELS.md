# Native structured models

The compiler in `app/core/structured.py` expands a bounded, explicitly supported JSON contract into the existing scalar engine. It uses no Simlin runtime, Python eval, or external execution. Simlin's separation of model structure and compilation informed the architecture; this implementation and examples are original.

`compile_structured_model(raw)` returns an object with `model` (scalar model), `source_map` (expanded ID to original element path and dimension indices), and `diagnostics` (empty on success). Failure raises `StructuredModelError`, a ValueError with `code`, `path`, and structured `diagnostics`. The input is never modified. Persist/export the original project separately: the expanded model is an execution artifact, not a lossless project replacement.

## Arrays

Declare root `dimensions: [{"name":"Region","elements":["North","South"]}]`. Stocks, flows and variables may declare `dimensions:["Region"]`, or multiple ordered dimension names. Structured names and dimension members are ASCII identifiers of at most 128 characters; scalar-only projects retain their existing naming rules.

A stock uses scalar `initial_value` as its default. `initial_values:{"North":100,"South":200}` overrides cells. Every element may use `equations:{"North":"2","South":"3"}` to override its default equation. Multidimensional keys follow declared order, comma-separated without spaces, such as `North,Young`. Partial overrides are permitted; unknown keys fail.

`Population[Region]` maps Region to the current cell index. `Population[North]` selects a literal cell. Bare array references work only when all their declared dimensions are bound by the current element. The selector must name that axis's dimension or one of its members; dimension renaming/mapping is unsupported.

`SUM(Population[Region])` sums the full dimension. For a multidimensional array, `SUM(Population[North,Age])` sums ages within North. Within SUM, dimension-name selectors always reduce their full axis, even inside an array cell. SUM accepts one reference only; arbitrary reduction expressions, slices, wildcard selectors, and other array operators are rejected. Write elementwise auxiliary equations before reducing them.

Flow endpoints use the same reference notation and resolve to the corresponding declared local stock's deterministic ID. Root/local source IDs are also accepted for stock references. Compiled names resemble `Population[North]`; IDs resemble `structured:Population[North]`. All equation references are quoted for the scalar parser.

## Reusable modules

Root `module_definitions` is a map of definition names to bodies. A body contains ordinary stocks/flows/variables and optional nested module instances. Dimensions are declared at the project root. Inputs and outputs are explicit:

```json
{
  "module_definitions": {
    "Tank": {
      "inputs": ["rate"],
      "outputs": {"remaining": "Water"},
      "stocks": [{"name": "Water", "initial_value": 100}],
      "flows": [{"name": "Drain", "from_stock": "Water", "equation": "Water * rate"}]
    }
  },
  "variables": [{"name": "speed", "equation": "0.1"}],
  "modules": [{"name": "left", "definition": "Tank", "inputs": {"rate": "speed"}}]
}
```

An input binding is one scalar reference in the parent scope, including an explicit array cell or another instance's declared output. It is read-only. An output port maps to one explicit scalar reference inside the module, including a nested module output. Consumers reference `left.remaining`. Every declared input must be bound exactly once; bindings and outputs are checked even when unused. Module names, local elements, and inputs must not collide.

Instances receive namespaces such as `left.Water`. Bare or quoted references cannot capture outer names: an undeclared parent variable is an error inside a module. A flow can connect only stocks declared in its own body; crossing a module boundary through inputs or outputs is rejected. Connect independent modules through read-only information bindings; shared stocks, cross-boundary material flow, array-valued ports and module arrays are unsupported.

## Bounds and limitations

Compiler limits are 4,096 expanded elements (the existing execution engine may impose a lower limit, currently 500; compilation does not waive execution budgets), 128 module instances, eight levels of module nesting, 32 dimension declarations, 100,000 source characters per equation and two million total equation characters/expanded-reference work units, and two million expanded identifier metadata bytes. Dimension/instance/module/element declarations reject unsupported extra fields; mappings and module arrays cannot be silently ignored. Recursive module instantiation and cyclic port bindings fail before simulation. Scalar algebraic cycles remain the scalar engine's validation responsibility.

Nonempty connectors are rejected rather than silently dropped; regenerate visual connectors from expanded dependencies where needed. Structured scalar names must be identifiers. Tables and simulation settings pass through unchanged to existing validation. Unknown function calls remain the scalar parser's responsibility. Quoted tokens in structured equations are element references; literal string/report expressions are outside this contract. Rich XMILE/MDL array and module semantics are not claimed by this JSON compiler.

Tests compare complete output series with an independently hand-expanded scalar model, exercise module conservation and nested namespaces, verify source preservation and deterministic expansion, and reject invalid dimensions, overrides, indices, reductions, recursion, missing bindings, name capture and cross-boundary flow.

