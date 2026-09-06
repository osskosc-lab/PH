# ATCT-PH Phase 2B v0.1 — P1 Static Code-to-Contract Review

## Decision

```
P0_SPECIFICATION_FREEZE: PASS
P1_IMPLEMENTATION_PRESENT: PASS
P1_STATIC_CODE_TO_CONTRACT_MAPPING: PASS

P1_COMPILE_CHECK: NOT_RUN
P1_DETERMINISTIC_TESTS: NOT_RUN
P1_REPLAY_HASH_VALIDATOR: NOT_RUN

STOCHASTIC_QUAL: NOT_AUTHORIZED
CONFIRMATORY: NOT_AUTHORIZED
```

This review is source-level only. No simulator was executed.

## Mapping audit

| Frozen contract item | Source mapping | Static result |
|---|---|---|
| binary64 | `as_f64`, float64 arrays | PASS |
| `A_kappa=I+h(-Q0+Omega-kappa QK)` | `p2b_contract.a_kappa` | PASS |
| state order c1,c2,e1,e2 | contract loader + simulator 4-vector order | PASS |
| K distance | `p2b_simulator.d_k` | PASS |
| four intervention profiles | `profile_value` | PASS |
| 16 exact cells | frozen contract + `FROZEN_CELL_IDS` | PASS |
| process/observation matched streams | side-free PROCESS/OBS stream keys | PASS |
| SHA-256 uniform stream | `uniform64` | PASS |
| Box-Muller order | `gaussian_stream` | PASS |
| exact-uniform bootstrap index | `exact_uniform_integer` | PASS |
| y0..y384 indexing | `simulate_with_noise` | PASS |
| baseline y192..y255 | `trajectory_signature` | PASS |
| post y257..y384 | `trajectory_signature` | PASS |
| 256D signature | time-major flatten / sqrt(256) | PASS |
| normalized energy distance V-statistic | `normalized_energy_distance` | PASS |
| even median rule | `frozen_even_median` | PASS |
| H1 trend statistics | `trend_statistics` | PASS |
| paired seed bootstrap | `bootstrap_primary` | PASS |
| nearest-rank intervals | `nearest_rank` | PASS |
| H1 gate | `primary_h1_gate` | PASS |
| extinction gate | `extinction_gate` | PASS |
| dynamic-range gate | `dynamic_range_gate` | PASS |
| 512 label-swap gate | `null_calibration_gate` + swap function | PASS |
| analytic flattening gate | `flattening_certificate_gate` | PASS |
| CW1 equations | `simulate_counterworld_with_noise` | PASS |
| CW1 negative-control gate | `counterworld_qualification_gate` | PASS |
| 8D Oracle Clone | `simulate_oracle_clone_with_noise` | PASS |
| Fisher theta diagnostic | `fisher_information_conditional_gaussian` | PASS |
| susceptibility finite differences | `finite_difference_susceptibility` | PASS |
| stochastic execution barrier | authorization file required before RNG-backed runner | PASS |
| P0 Git-blob integrity | `p0_lock.json` + validator | PASS by construction; execution pending |
| P1 source integrity | `p1_source_lock.json` + validator | PASS by construction; execution pending |

## Important scope note

The P1 static PASS means only that the written source maps to the frozen textual/numeric contract without an identified source-level scientific-parameter choice.

It does **not** establish that:

- Python compilation succeeds;
- deterministic replay succeeds;
- the numerical implementation reproduces expected values at runtime;
- the estimator is calibrated;
- H1 is supported;
- stochastic QUAL may begin.

Those require the next narrow audit step. Until then the branch intentionally contains no execution authorization file and no QUAL/CONF entrypoint.
