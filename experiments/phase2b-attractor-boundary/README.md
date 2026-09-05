# ATCT-PH Phase 2B v0.1

## Attractor Flattening and Operational Boundary Degeneracy

This directory is the **preregistration-only** scaffold for Phase 2B.

The scientific question is deliberately narrower than any phenomenological or metaphysical interpretation:

> When a preregistered restoring organization is weakened by lowering `kappa`, does the **operational causal boundary distinguishability** measured under a fixed access class decrease?

The core model is:

```
x_(t+1) = F(x_t) + kappa R(x_t, K) + eta_t
```

`kappa` is the physical/simulation control parameter. `DeltaT` remains an analysis-window hyperparameter and is never reinterpreted as a physical death variable.

The primary endpoint is `D_boundary(kappa)`, defined from matched internal-vs-external intervention response distributions with a frozen normalized energy-distance estimator. It is an **access-relative operational quantity** only.

Five preregistration corrections are fixed here:

1. `D_boundary` is fully operationalized and does not claim latent-boundary identity.
2. Monotone degeneration and operational extinction are separate claims.
3. Flattening is independently certified by `F_flat` before interpreting `D_boundary`.
4. Fisher information is diagnostic only and its parameterization must be frozen.
5. Window susceptibility is written as `chi_B(DeltaT; kappa)`; `chi_kappa` is a separate control sensitivity.

A registered counterworld is allowed to kill the hypothesis. If certified flattening occurs while `D_boundary` remains preserved within tolerance, the registered H1 is falsified. No estimator or threshold rescue is allowed after such a hit.

## Current status

- protocol: **DRAFT_FOR_PREREGISTRATION_FREEZE**
- Pilot execution: **NOT AUTHORIZED**
- Confirmatory execution: **NOT AUTHORIZED**
- current gate: **P2B-P0_SPECIFICATION_FREEZE**

No result in this directory may be used to claim ego death, consciousness loss, qualia change, soul persistence, soul death, biological validity, or latent boundary identity.

The next valid step is an implementation-qualification PR that exactly instantiates the frozen access class, model contract, primary endpoint, flattening certificate, null, counterworld, and Oracle-Clone firewall. Confirmatory data generation requires a later explicit freeze.
