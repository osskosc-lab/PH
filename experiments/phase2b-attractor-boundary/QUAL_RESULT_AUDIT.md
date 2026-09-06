# ATCT-PH Phase 2B v0.1 — QUAL Result Audit

## Frozen run

- GitHub Actions run: `34005255989`
- Head SHA: `487119478bcbffbaae9d3b15265b04ecdc1ac78b`
- QUAL seeds: 96
- Bootstrap: B=10,000
- Artifact ID: `9980770717`
- Artifact SHA256: `1460bec1a6d702d2affe8345c685c6d949e00b21e25b38cb32524059e349d6d6`

## Decision

```
QUALIFICATION_DECISION: QUAL_STOP_GATE_FAILURE
CONFIRMATORY_FREEZE: NOT_ELIGIBLE
CONFIRMATORY_EXECUTION: NOT_AUTHORIZED
```

This is a preregistered scientific STOP, not an infrastructure failure.

## Gate results

| Gate | Result |
|---|---|
| G1 Dynamic range | PASS |
| G2 Intervention matching | PASS |
| G3 Flattening certificate | PASS |
| G4 Exact null | PASS |
| G4 Paired label-swap null | PASS |
| G5 Counterworld negative control | FAIL |
| G6 Primary H1 qualification | FAIL |
| G7 Oracle Clone firewall | PASS |

## Primary endpoint

Frozen `D_boundary(kappa)` point estimates:

| kappa | D_boundary |
|---:|---:|
| 1.00 | 0.4849428893 |
| 0.75 | 0.4906486967 |
| 0.50 | 0.4810519602 |
| 0.25 | 0.4619314036 |
| 0.00 | 0.4471015552 |

Bootstrap:

- `U95(V_mon) = 0.0113493439 <= 0.02` — monotonicity tolerance component PASS.
- `L95(Delta_D) = 0.0286860226 < 0.10` — preregistered minimum endpoint-drop component FAIL.
- median `Delta_D = 0.0382302864`.

Therefore the registered H1 gate fails because the effect is too small, even though gross monotonicity tolerance is not violated.

## Counterworld failure

CW1 `D_boundary(kappa)`:

| kappa | D_boundary_CW |
|---:|---:|
| 1.00 | 0.5719945885 |
| 0.75 | 0.5723945072 |
| 0.50 | 0.5576485292 |
| 0.25 | 0.5321199216 |
| 0.00 | 0.4927113430 |

Counterworld bootstrap:

- median `Delta_D_CW = 0.0791451594`
- `L95(Delta_D_CW) = 0.0706377531 > 0.02`

The registered negative-control requirement was `L95(Delta_D_CW) <= 0.02`; therefore CW1 fails. The current access/estimator pipeline cannot cleanly attribute the observed decreasing `D_boundary` to the registered restoring-boundary mechanism rather than a broader kappa-dependent response effect.

## Other diagnostics

- Dynamic-range minimum in-range fraction: `1.0`.
- Exact-null maximum replay difference: `0.0`.
- Paired label-swap null q95(V): `0.0019595351 <= 0.02`.
- Oracle Clone maximum output difference: `0.0`.
- Secondary extinction gate: FAIL; `U95[D_boundary(kappa=0)] = 0.4589496176 >> 0.05`.
- Fisher diagnostic effective rank remains `3` at every kappa; `lambda_min=4.0` throughout. No Fisher-rank degeneration is observed under the frozen diagnostic parameterization.

## Window-surface observation (secondary only)

The kappa effect is strongly analysis-window dependent. At short DeltaT the point estimates are non-monotone or increase as kappa decreases; the clearest modest decrease appears at longer windows. This is exploratory only and cannot rescue H1.

## Anti-rescue rule

No threshold, estimator, intervention family, kappa grid, window, or counterworld may be retuned and rerun under v0.1.

Any follow-up must be a new protocol version with:
1. a new, explicit failure-localization proposition;
2. a fresh seed namespace;
3. a new preregistration freeze before stochastic execution.

No Confirmatory run is authorized from this result.
