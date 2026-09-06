# ATCT-PH Phase 2B v0.1 — P0 Specification Freeze Audit

## Decision

```
P2B-P0_SPECIFICATION_FREEZE: PASS
IMPLEMENTER_DEGREES_OF_FREEDOM_FOR_REQUESTED_CORE: ZERO
CURRENT_GATE: P2B-P1_IMPLEMENTATION_QUALIFICATION

IMPLEMENTATION_SCAFFOLD: AUTHORIZED
STOCHASTIC_QUALIFICATION_RUN: NOT_AUTHORIZED
CONFIRMATORY_RUN: NOT_AUTHORIZED
```

No simulation, Pilot, qualification dataset, or Confirmatory dataset was generated in this step.

## What was frozen

The following items are now fully explicit and may not be selected by the implementer:

1. **F / R / K**
   - 4D state order: `[c1,c2,e1,e2]`.
   - `F(x)=A_0 x`.
   - `R(x,K)=-h Q_K x`.
   - `A_kappa=I+h(-Q_0+Omega-kappa Q_K)`.
   - `h=0.25`, and every matrix entry is fixed in `implementation_contract.json`.
   - `K={x:c1=c2=0}`.
   - analytic flattening certificate: `F_flat(kappa)=0.20+0.80*kappa`.

2. **Observation model / theta**
   - `y=C(theta)x+xi`.
   - nominal `C=[[1,0,0.25,0],[0,1,0,0.25]]`.
   - `sigma_obs=0.03`.
   - Fisher diagnostic parameter vector is exactly `theta=(c13,c24,log sigma_obs)`.
   - Fisher is diagnostic only.

3. **Intervention cells**
   - two frozen target pairs: `c1/e1`, `c2/e2`.
   - four exact profiles: impulse, pulse8, sine16x4, biphasic16.
   - two amplitudes: 0.25 and 0.50.
   - exactly 16 matched cells per kappa.
   - onset, duration, baseline, post window, and target vectors are fixed.

4. **Seed namespace / stochastic stream**
   - master namespace: `ATCT-PH-P2B-v0.1`.
   - QUAL: 96 seeds.
   - CONF: 384 reserved seeds; generation prohibited.
   - SHA-256 counter-mode stochastic stream and Box-Muller transform are frozen; library RNG substitution is prohibited.

5. **Bootstrap / decision uncertainty**
   - independent unit: seed.
   - paired resampling across all kappa/cells/sides.
   - B=10,000.
   - nearest-rank percentile quantiles.
   - primary decision: `U95(V_mon)<=0.02 AND L95(Delta_D)>=0.10`.
   - extinction is a separate secondary gate: `U95(D(kappa=0))<=0.05`.

## Additional ambiguity closed

- The 256D trajectory signature and its exact indexing are frozen.
- The normalized energy-distance estimator and even-median convention are frozen.
- Dynamic-range thresholds are frozen.
- Exact-actuation null plus 512 paired label-swap nulls are frozen.
- An 8D duplicated-latent Oracle Clone is frozen.
- `B_eff(DeltaT,kappa)`, `chi_B`, and `chi_kappa` are frozen as secondary analyses.
- CW1 semantics are corrected: it is a negative-control/generalization falsifier. A deliberately decoupled counterworld cannot logically be allowed to automatically decide the base-DGP H1; doing so would make H1 self-falsifying by construction.

## Zero-freedom audit table

| Item | Status | Implementer choice remaining |
|---|---|---|
| State dimension/order | FROZEN | none |
| F matrix/decomposition | FROZEN | none |
| R and K | FROZEN | none |
| kappa grid | FROZEN | none |
| process noise | FROZEN | none |
| observation C / sigma | FROZEN | none |
| Fisher theta | FROZEN | none |
| intervention targets | FROZEN | none |
| profiles/amplitudes | FROZEN | none |
| time indexing | FROZEN | none |
| trajectory signature | FROZEN | none |
| distance estimator | FROZEN | none |
| cell aggregation | FROZEN | none |
| seed derivation | FROZEN | none |
| RNG transform | FROZEN | none |
| bootstrap | FROZEN | none |
| H1 thresholds | FROZEN | none |
| extinction threshold | FROZEN | none |
| null controls | FROZEN | none |
| Oracle Clone | FROZEN | none |
| window susceptibility | FROZEN | none |

## What P1 may do

P1 may only translate the contract into code, deterministic unit tests, replay checks, and a code-to-contract audit.

P1 may **not**:

- tune any matrix, threshold, amplitude, profile, window, seed, or estimator;
- execute the stochastic QUAL run before code audit approval;
- generate any CONF seed or data;
- change the protocol after observing Phase 2B outcomes;
- make claims about ego death, consciousness, selfhood, qualia, soul, biology, or a unique latent boundary.

Any scientific-parameter change requires a new protocol version and a new master seed namespace.
