# PH v0.3.1-r2 — Paired-Stress & Representation-Repair Pilot Stop Audit

## Official status

**Decision: `INCONCLUSIVE` — Confirmatory not started.**

This is the preregistered stopping outcome, not a post-hoc downgrade. The R2 protocol requires the intervention-kernel representation to validate in Pilot before any Confirmatory seed is used.

## Parent-detector continuity

Before R2 repair, the parent PH v0.3.1 implementation was reproduced locally at its official Confirmatory values: `K_V(0.8)=0.7807945`, `K_O(0.8)=0.7764041`, `R_lambda_OOD=0.9069090`, `R_CIC=0.4950731`. R2 then changed only the intended measurement/intervention audit layer: raw-margin saturation semantics, paired nuisance RNG, SHA-derived fresh seeds, and the Pilot-frozen RBF kernel representation.

## Official Pilot

- N = 40 seeds/condition
- seed source = SHA256(`version|stage|mode|condition|index`) -> uint32
- overlap with v0.3 / v0.3.1 registered seed ranges = **0**
- paired RNG integrity = **PASS**
- selected RBF bandwidth `h = 0.5`
- selected ridge `alpha = 0.0001`
- Pilot leave-one-lambda-out RMSE = `0.01097619`

### Kernel Pilot Gate

| Endpoint | Result | Preregistered criterion |
|---|---:|---:|
| P_kernel(shared) | 0.483 | >= 0.80 |
| FP_kernel(separate) | 0.000 | <= 0.05 |
| FP_kernel(common-driver) | 0.000 | <= 0.05 |
| FP_kernel(adversarial-clamp-mimic) | 0.393 | <= 0.05 |

**Kernel Pilot Gate: FAIL.** Shared recovery is too low and the adversarial clamp mimic is too often accepted by the kernel representation.

## Core endpoints remained strong before G10

Fresh Pilot shared-boundary values:

- `K_V(0.8) = 0.78434`
- `K_O(0.8) = 0.79149`
- `R_lambda_OOD = 0.87074`; UCB95 `0.91912`
- `R_CIC = 0.50137`; UCB95 `0.65221`
- raw-margin saturation V/O = `0.000 / 0.000`
- parametric representation = `True`
- nonparametric representation = `True`
- kernel representation = `False`

Thus R2 successfully removes the old G2 technical failure and verifies paired RNG, but does **not** repair G10 under the preregistered kernel-validation rule.

## Consequence

Per protocol, no post-Pilot hyperparameter or threshold adjustment is allowed and no `freeze.json` is created. `run_confirmatory.py` therefore refuses to execute. No ROBUST / FRAGILE / FALSIFIED claim is made, and the compound `s=0.50` question remains unconfirmed in R2.

A future revision must define a different representation estimator **before new Pilot seeds are generated**. The present Pilot seeds must not be reused for that revision.
