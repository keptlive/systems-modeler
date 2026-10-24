# Proposed May logistic-model consolidation

Status: proposed; not yet adopted or deployed. These notes describe the planned migration, not a current catalog change.

Three catalog examples use the same one-state logistic generation map with different parameter defaults. The proposal keeps **May logistic generation map**, ID may-chaos-population-eco, and preserves all three defaults as scenarios. It would archive the other two catalog definitions; your saved/private copies would remain unchanged.

| Former model | Former ID | Canonical preset |
| --- | --- | --- |
| May's Logistic Map Model | may-logistic-chaos | r=3.7,Population=0.1 |
| May Ecological Chaos Model | may-ecological-chaos-eco | r=3.8,Population=0.1 |
| May Logistic Map Chaos Model | may-chaos-population-eco (retained) | r=3.9,Population=0.1 |

Use 0..100 whole generations, Euler,dt=discrete_period=1. Each default produces 101 samples. Reducing the integration step or selecting RK4/Radau would change the generation map; the explicit period declaration prevents those changes. These illustrative parameters are not calibrated ecological forecasts.

## Try and compare the presets

Open the canonical model and choose Inspect. Under Equations & initial values select r, then change its Equation in the existing editor to3.7,3.8 or 3.9. Keep Population's initial value 0.1 and the generation settings above, then Run. This intentionally edits your current draft; Save remains a separate action.

To compare, Run one case and choose the existing Save Run control, then repeat for the other r values and choose Compare. Existing desktop/mobile comparison controls remain available. Record the r value for each saved run: generated labels follow your run order, but a comparison trajectory is not a persistent parameter preset or a saved library model.

For agents, the existing compare_scenarios tool accepts:
```json
{
  "model_id": "may-chaos-population-eco",
  "scenarios": [
    {"name":"Legacy r=3.7","parameters":{"r":3.7,"Population":0.1}},
    {"name":"Legacy r=3.8","parameters":{"r":3.8,"Population":0.1}},
    {"name":"Legacy r=3.9","parameters":{"r":3.9,"Population":0.1}}
  ]
}
```
It compares copies and returns summaries without saving. It does not install a browser preset menu or return full trajectories. All three original full default series are retained in the proposal's reference evidence.

## Existing links and output columns

The old IDs map to the canonical ID plus the presets above. Retiring their files does not automatically redirect old links; search for the canonical title or the former title/ID listed in its description. Deployment notes must state when the migration actually takes effect. Original JSON files are preserved byte-for-byte in the reviewed archive, and existing user definitions are not rewritten.

The canonical diagnostic names become Instantaneous Log Slope and Coarse Parameter Range Code. Their old expressions and IDs are retained. An instantaneous slope is not a long-run averaged Lyapunov exponent; code 99 does not prove chaos, and periodic windows occur within that broad parameter range.

The two retired models used Growth_Rate for different quantities: constant r in the 3.7 case, but r*(1-Population) in the 3.8 case. Do not match those columns by name alone. Population/net increments match exactly; the proposal's explicit compatibility map preserves all former diagnostics, including original arithmetic ordering for fixed-point/deviation columns. Name-based chart/report consumers may need that mapping.

Download JSON preserves the generation-period contract. The XMILE exporter currently refuses that unsupported contract explicitly and explains choosing JSON; it must not silently erase the period. Both export choices remain available.

## Release conditions

This proposal requires independent approval of its final canonical hash, public preset/migration notes, a scoped hash-bound two-retirement/one-replacement transaction and staged verification. The separate actionable export-error fix must ship in the same future quality release before this migration. No active changes are performed by publishing this draft proposal.
