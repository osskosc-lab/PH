# ATCT-PH Phase 2B v0.1

## Attractor Flattening and Operational Boundary Degeneracy

Phase 2B is now at **P2B-P1_IMPLEMENTATION_QUALIFICATION**.

The P0 specification freeze is complete. The scientific question remains deliberately narrow:

> In the single frozen synthetic base DGP, when the registered restoring organization is weakened by lowering `kappa`, does the access-relative operational causal boundary distinguishability `D_boundary(kappa)` decrease?

The exact implementation contract is:

- `implementation_contract.json` — F/R/K, observation model, theta, intervention cells, time indexing, estimator, controls, seed/RNG namespace, and bootstrap.
- `preregistration.json` — claim scope, primary/secondary endpoints, decision gates, and firewall.
- `P0_FREEZE_AUDIT.md` — zero-degree-of-freedom audit for the frozen scientific specification.
- `CLAIM_FIREWALL.md` — prohibited claim upgrades.

## Frozen core

```
x_(t+1) = A_kappa x_t + b_j u_t + eta_t
A_kappa = I + 0.25(-Q_0 + Omega - kappa Q_K)
K = {x : c1 = 0, c2 = 0}
F_flat(kappa) = 0.20 + 0.80*kappa
```

`DeltaT` remains an analysis-window hyperparameter only.

The primary endpoint is a frozen normalized energy-distance statistic over exactly 16 matched inside/outside intervention cells. The primary inferential gate uses a paired seed bootstrap with B=10,000 and frozen nearest-rank quantiles.

## Current authorization

```
P2B-P0_SPECIFICATION_FREEZE: PASS
CURRENT_GATE: P2B-P1_IMPLEMENTATION_QUALIFICATION

IMPLEMENTATION_SCAFFOLD: AUTHORIZED
STOCHASTIC_QUALIFICATION_RUN: NOT AUTHORIZED
CONFIRMATORY_RUN: NOT AUTHORIZED
```

P1 may translate the contract into simulator/estimator code, deterministic unit tests, and replay/hash checks only. It may not tune any scientific parameter and may not run the stochastic QUAL or CONF stages yet.

No result from this branch may be used to claim ego death, consciousness loss, selfhood identity, qualia change, soul persistence/death/transfer, biological validity, or unique latent boundary identity.
